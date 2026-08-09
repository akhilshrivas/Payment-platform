"""
Webhook service — processes verified Razorpay webhook events.

Critical rules:
1. Every handler must be idempotent (same event = same result).
2. Wallet balance changes must happen inside atomic transactions.
3. select_for_update() prevents race conditions.
4. The wallet is NEVER credited based solely on frontend callback.
"""

import logging
from datetime import datetime, timezone

from django.db import transaction

from apps.common.utils import generate_reference
from apps.payments.models import Payment, RazorpayWebhookEvent

logger = logging.getLogger(__name__)


class WebhookService:
    """Handles Razorpay webhook event processing."""

    # Supported event types
    SUPPORTED_EVENTS = {
        "payment.captured",
        "payment.failed",
        "order.paid",
        "refund.processed",
        "refund.failed",
    }

    @classmethod
    def process_event(cls, event_id: str, event_type: str, payload: dict) -> None:
        """
        Main entry point.

        1. Check for duplicate event (idempotency).
        2. Store the event.
        3. Route to the appropriate handler.
        4. Mark as processed.
        """
        # Idempotency check: skip if already processed
        event, created = RazorpayWebhookEvent.objects.get_or_create(
            razorpay_event_id=event_id,
            defaults={
                "event_type": event_type,
                "payload": payload,
                "processed": False,
            },
        )

        if not created and event.processed:
            logger.info(
                "Duplicate webhook event skipped | event_id=%s | type=%s",
                event_id,
                event_type,
            )
            return

        if event_type not in cls.SUPPORTED_EVENTS:
            logger.info("Unsupported webhook event ignored: %s", event_type)
            event.processed = True
            event.processed_at = datetime.now(tz=timezone.utc)
            event.save(update_fields=["processed", "processed_at"])
            return

        try:
            if event_type == "payment.captured":
                cls._handle_payment_captured(payload)
            elif event_type == "payment.failed":
                cls._handle_payment_failed(payload)
            elif event_type == "order.paid":
                cls._handle_order_paid(payload)
            elif event_type in ("refund.processed", "refund.failed"):
                cls._handle_refund(event_type, payload)

            event.processed = True
            event.processed_at = datetime.now(tz=timezone.utc)
            event.save(update_fields=["processed", "processed_at"])
            logger.info(
                "Webhook event processed | event_id=%s | type=%s",
                event_id,
                event_type,
            )
        except Exception as e:
            event.error_message = str(e)
            event.save(update_fields=["error_message"])
            logger.exception(
                "Webhook event processing failed | event_id=%s | type=%s | error=%s",
                event_id,
                event_type,
                e,
            )
            raise

    @classmethod
    @transaction.atomic
    def _handle_payment_captured(cls, payload: dict) -> None:
        """
        payment.captured — Razorpay has captured the payment.

        Atomic steps:
        1. Lock the Payment record.
        2. If already SUCCEEDED → return (idempotent).
        3. Mark Payment as SUCCEEDED.
        4. Lock user's Wallet.
        5. Credit wallet balance.
        6. Create completed Transaction.
        7. Send notification.
        """
        from apps.transactions.models import Transaction
        from apps.wallets.models import Wallet
        from apps.notifications.services.notification_service import NotificationService

        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        razorpay_order_id = payment_entity.get("order_id")
        razorpay_payment_id = payment_entity.get("id")
        amount_paise = payment_entity.get("amount", 0)

        if not razorpay_order_id:
            logger.warning("payment.captured webhook missing order_id in payload.")
            return

        # Find the Payment by Razorpay order ID
        try:
            payment = Payment.objects.get(
                razorpay_order_id=razorpay_order_id
            )
        except Payment.DoesNotExist:
            logger.warning(
                "No Payment found for Razorpay order_id=%s", razorpay_order_id
            )
            return

        from apps.payments.services.payment_service import PaymentService
        PaymentService.process_successful_payment(payment, razorpay_payment_id)

    @classmethod
    @transaction.atomic
    def _handle_payment_failed(cls, payload: dict) -> None:
        """payment.failed — Mark the payment as FAILED. Do NOT credit wallet."""
        from apps.notifications.services.notification_service import NotificationService

        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        razorpay_order_id = payment_entity.get("order_id")

        if not razorpay_order_id:
            return

        try:
            payment = Payment.objects.select_for_update().get(
                razorpay_order_id=razorpay_order_id
            )
        except Payment.DoesNotExist:
            logger.warning(
                "No Payment found for failed payment order_id=%s", razorpay_order_id
            )
            return

        if payment.status in (Payment.Status.FAILED, Payment.Status.SUCCEEDED):
            return  # Already terminal

        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "updated_at"])

        error_code = (
            payment_entity.get("error_code", "")
            or payment_entity.get("error_description", "Payment failed")
        )
        logger.info(
            "Payment marked FAILED | ref=%s | reason=%s",
            payment.payment_reference,
            error_code,
        )

        NotificationService.notify_payment_failed(payment.user, payment.amount)

    @classmethod
    def _handle_order_paid(cls, payload: dict) -> None:
        """order.paid — fired when order is fully paid. Log only; capture handles wallet."""
        order_entity = payload.get("payload", {}).get("order", {}).get("entity", {})
        order_id = order_entity.get("id")
        logger.info("order.paid webhook received | order_id=%s", order_id)

    @classmethod
    def _handle_refund(cls, event_type: str, payload: dict) -> None:
        """refund.processed / refund.failed — log and update payment status."""
        refund_entity = payload.get("payload", {}).get("refund", {}).get("entity", {})
        payment_id = refund_entity.get("payment_id")
        refund_id = refund_entity.get("id")
        logger.info(
            "Refund event received | type=%s | refund_id=%s | payment_id=%s",
            event_type,
            refund_id,
            payment_id,
        )
        # Status is already updated by PaymentService.refund_payment()
