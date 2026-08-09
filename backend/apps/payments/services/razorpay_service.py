"""
Razorpay service — wraps the razorpay SDK.

All Razorpay API calls go through this class.
Business logic lives in payment_service.py and webhook_service.py.
"""

import logging
from decimal import Decimal

import razorpay
from django.conf import settings

from apps.common.exceptions import WebhookVerificationError

logger = logging.getLogger(__name__)


class RazorpayService:
    """
    Thin wrapper around the Razorpay Python SDK.

    Reads credentials from Django settings (set from environment variables).
    Never exposes RAZORPAY_KEY_SECRET to the frontend.
    """

    def __init__(self) -> None:
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        self.client.set_app_details(
            {"title": "PaymentPlatform", "version": "1.0.0"}
        )

    def create_order(
        self,
        amount: Decimal,
        currency: str,
        receipt: str,
        notes: dict,
    ) -> dict:
        """
        Create a Razorpay Order.

        Amount is converted from INR (Decimal) to paise (int) here.
        Returns the full Razorpay order object.
        """
        amount_paise = int(amount * 100)
        if amount_paise < 100:
            raise ValueError(f"Minimum amount is ₹1 (100 paise). Got {amount_paise} paise.")

        order_data = {
            "amount": amount_paise,
            "currency": currency.upper(),
            "receipt": receipt,
            "notes": notes,
        }
        try:
            order = self.client.order.create(data=order_data)
            logger.info(
                "Razorpay order created | order_id=%s | amount_paise=%s | receipt=%s",
                order.get("id"),
                amount_paise,
                receipt,
            )
            return order
        except razorpay.errors.BadRequestError as e:
            logger.error("Razorpay order creation failed: %s", e)
            raise

    def fetch_order(self, order_id: str) -> dict:
        """Fetch a Razorpay order by ID."""
        return self.client.order.fetch(order_id)

    def fetch_payment(self, payment_id: str) -> dict:
        """Fetch a Razorpay payment by ID."""
        return self.client.payment.fetch(payment_id)

    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """
        Verify the HMAC-SHA256 signature returned by Razorpay Checkout.

        Returns True if valid, False if invalid.
        """
        params = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        }
        try:
            self.client.utility.verify_payment_signature(params)
            logger.info(
                "Payment signature verified | order_id=%s | payment_id=%s",
                razorpay_order_id,
                razorpay_payment_id,
            )
            return True
        except razorpay.errors.SignatureVerificationError:
            logger.warning(
                "Payment signature verification FAILED | order_id=%s | payment_id=%s",
                razorpay_order_id,
                razorpay_payment_id,
            )
            return False

    def verify_webhook_signature(self, body: str, signature: str) -> None:
        """
        Verify the Razorpay webhook signature.

        Raises WebhookVerificationError on failure.
        IMPORTANT: `body` must be the raw, unmodified request body string.
        """
        try:
            self.client.utility.verify_webhook_signature(
                body, signature, settings.RAZORPAY_WEBHOOK_SECRET
            )
            logger.debug("Webhook signature verified successfully.")
        except razorpay.errors.SignatureVerificationError:
            logger.warning("Webhook signature verification FAILED.")
            raise WebhookVerificationError()

    def refund_payment(
        self,
        payment_id: str,
        amount: Decimal | None = None,
        notes: dict | None = None,
    ) -> dict:
        """
        Initiate a full or partial refund.

        `amount` is in INR (Decimal). If None, full refund is issued.
        """
        refund_data: dict = {"speed": "optimum"}
        if amount is not None:
            refund_data["amount"] = int(amount * 100)
        if notes:
            refund_data["notes"] = notes

        try:
            refund = self.client.payment.refund(payment_id, refund_data)
            logger.info(
                "Razorpay refund initiated | payment_id=%s | refund_id=%s",
                payment_id,
                refund.get("id"),
            )
            return refund
        except razorpay.errors.BadRequestError as e:
            logger.error("Razorpay refund failed | payment_id=%s | error=%s", payment_id, e)
            raise
