"""
RecurringPaymentService — handles scheduling and processing logic.

Uses python-dateutil for proper calendar arithmetic:
- MONTHLY does not assume 30 days
- YEARLY handles leap years correctly
"""

import logging
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import transaction

from apps.common.exceptions import ApplicationError, InsufficientBalanceError
from apps.recurring_payments.models import RecurringPayment

logger = logging.getLogger(__name__)

# Auto-cancel after this many consecutive failures
MAX_CONSECUTIVE_FAILURES = 3


class RecurringPaymentService:
    """Manages recurring payment creation, processing, and scheduling."""

    @staticmethod
    def calculate_next_date(current_date: date, frequency: str) -> date:
        """
        Calculate the next payment date using proper calendar arithmetic.

        DAILY:   +1 calendar day
        WEEKLY:  +7 calendar days
        MONTHLY: +1 month (handles Feb 28/29, month-end correctly via relativedelta)
        YEARLY:  +1 year  (handles Feb 29 → Feb 28 on non-leap years)
        """
        freq = frequency.upper()
        if freq == RecurringPayment.Frequency.DAILY:
            return current_date + relativedelta(days=1)
        elif freq == RecurringPayment.Frequency.WEEKLY:
            return current_date + relativedelta(weeks=1)
        elif freq == RecurringPayment.Frequency.MONTHLY:
            return current_date + relativedelta(months=1)
        elif freq == RecurringPayment.Frequency.YEARLY:
            return current_date + relativedelta(years=1)
        else:
            raise ValueError(f"Unknown frequency: {frequency}")

    @staticmethod
    @transaction.atomic
    def process_single_recurring_payment(recurring_payment_id: str) -> None:
        """
        Process one recurring payment atomically.

        Steps:
        1. Lock the RecurringPayment row.
        2. Validate it is still ACTIVE and due.
        3. Check sender balance.
        4. Perform wallet transfer.
        5. Update dates and status.
        6. Handle failures (increment counter, auto-cancel).
        """
        from apps.wallets.services.wallet_service import WalletService
        from apps.notifications.services.notification_service import NotificationService

        try:
            rp = RecurringPayment.objects.select_for_update().get(
                pk=recurring_payment_id, status=RecurringPayment.Status.ACTIVE
            )
        except RecurringPayment.DoesNotExist:
            logger.warning(
                "Recurring payment not found or not ACTIVE: %s", recurring_payment_id
            )
            return

        today = date.today()

        # Double-check it is due (guards against race conditions)
        if rp.next_payment_date > today:
            logger.debug("Recurring payment %s not yet due.", recurring_payment_id)
            return

        # Check end_date
        if rp.end_date and today > rp.end_date:
            rp.status = RecurringPayment.Status.COMPLETED
            rp.save(update_fields=["status", "updated_at"])
            logger.info(
                "Recurring payment completed (end_date passed) | id=%s", recurring_payment_id
            )
            return

        try:
            tx = WalletService.transfer(
                sender=rp.user,
                receiver_email=rp.receiver.email,
                amount=rp.amount,
                description=rp.description or f"Recurring payment (₹{rp.amount} {rp.frequency})",
            )

            # Success: update dates, reset failure count
            rp.last_payment_date = today
            rp.next_payment_date = RecurringPaymentService.calculate_next_date(today, rp.frequency)
            rp.failure_count = 0

            # Check if this was the last payment
            if rp.end_date and rp.next_payment_date > rp.end_date:
                rp.status = RecurringPayment.Status.COMPLETED

            rp.save(
                update_fields=[
                    "last_payment_date",
                    "next_payment_date",
                    "failure_count",
                    "status",
                    "updated_at",
                ]
            )

            logger.info(
                "Recurring payment processed | id=%s | tx_ref=%s | next=%s",
                recurring_payment_id,
                tx.transaction_reference,
                rp.next_payment_date,
            )

            NotificationService.notify_recurring_processed(
                rp.user, rp.receiver, rp.amount, tx.transaction_reference
            )

        except InsufficientBalanceError as e:
            logger.warning(
                "Recurring payment failed (insufficient balance) | id=%s | error=%s",
                recurring_payment_id,
                e,
            )
            rp.failure_count += 1
            if rp.failure_count >= MAX_CONSECUTIVE_FAILURES:
                rp.status = RecurringPayment.Status.FAILED
                logger.warning(
                    "Recurring payment auto-cancelled after %d failures | id=%s",
                    MAX_CONSECUTIVE_FAILURES,
                    recurring_payment_id,
                )
                NotificationService.notify_recurring_failed(rp.user, rp.amount, rp.receiver.email)
            rp.save(update_fields=["failure_count", "status", "updated_at"])

        except ApplicationError as e:
            logger.error(
                "Recurring payment application error | id=%s | error=%s",
                recurring_payment_id,
                e,
            )
            rp.failure_count += 1
            if rp.failure_count >= MAX_CONSECUTIVE_FAILURES:
                rp.status = RecurringPayment.Status.FAILED
            rp.save(update_fields=["failure_count", "status", "updated_at"])
