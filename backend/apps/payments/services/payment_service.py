"""
Payment service — orchestrates payment lifecycle.

Sits between views and the Razorpay SDK service.
"""

import logging
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model

from apps.common.utils import generate_reference
from apps.payments.models import Payment
from apps.payments.services.razorpay_service import RazorpayService

logger = logging.getLogger(__name__)
User = get_user_model()


class PaymentService:
    """Manages the payment lifecycle from creation to refund."""

    def __init__(self) -> None:
        self.razorpay = RazorpayService()

    def create_payment_order(
        self,
        user: User,
        amount: Decimal,
        currency: str = "INR",
        description: str = "",
    ) -> dict:
        """
        Full payment creation flow:

        1. Create internal Payment record (status=CREATED).
        2. Create Razorpay Order with our payment_reference in notes.
        3. Update Payment with razorpay_order_id (status=PENDING).
        4. Return checkout data for the frontend.

        The frontend uses the returned order_id + key_id to open
        Razorpay Standard Checkout. We NEVER return the KEY_SECRET here.
        """
        payment_reference = generate_reference("PAY")

        # Step 1: Create internal record
        payment = Payment.objects.create(
            payment_reference=payment_reference,
            user=user,
            amount=amount,
            currency=currency.upper(),
            status=Payment.Status.CREATED,
            description=description,
            metadata={
                "user_id": str(user.id),
                "user_email": user.email,
            },
        )
        logger.info(
            "Payment record created | ref=%s | user=%s | amount=%s",
            payment_reference,
            user.email,
            amount,
        )

        # Step 2: Create Razorpay order
        try:
            order = self.razorpay.create_order(
                amount=amount,
                currency=currency,
                receipt=payment_reference,
                notes={
                    "payment_reference": payment_reference,
                    "user_id": str(user.id),
                    "user_email": user.email,
                },
            )
        except Exception as e:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "updated_at"])
            logger.error(
                "Razorpay order creation failed | ref=%s | error=%s",
                payment_reference,
                e,
            )
            raise

        # Step 3: Update payment with Razorpay order ID
        payment.razorpay_order_id = order["id"]
        payment.status = Payment.Status.PENDING
        payment.save(update_fields=["razorpay_order_id", "status", "updated_at"])

        logger.info(
            "Razorpay order linked | ref=%s | order_id=%s",
            payment_reference,
            order["id"],
        )

        # Step 4: Return checkout data (no KEY_SECRET!)
        return {
            "payment_id": str(payment.id),
            "payment_reference": payment_reference,
            "razorpay_order_id": order["id"],
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "amount": int(amount * 100),  # paise for Razorpay Checkout
            "currency": currency.upper(),
            "description": description,
        }

    def verify_and_confirm_payment(
        self,
        payment_id: str,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> Payment:
        """
        Verify Razorpay signature after frontend checkout completes.

        This is an additional server-side verification step. The actual wallet
        credit happens only via verified webhooks (webhook_service.py).

        Returns the Payment instance (status may still be PENDING until webhook).
        """
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            from apps.common.exceptions import PaymentNotFoundError
            raise PaymentNotFoundError()

        if payment.razorpay_order_id != razorpay_order_id:
            from apps.common.exceptions import ApplicationError
            raise ApplicationError("Order ID mismatch. Possible tampering detected.")

        # Verify the HMAC signature
        is_valid = self.razorpay.verify_payment_signature(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )

        if not is_valid:
            logger.warning(
                "Invalid payment signature | payment_id=%s | razorpay_payment_id=%s",
                payment_id,
                razorpay_payment_id,
            )
            from apps.common.exceptions import ApplicationError
            raise ApplicationError("Payment signature verification failed.")

        # Store Razorpay IDs for later webhook correlation
        if not payment.razorpay_payment_id:
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.save(update_fields=["razorpay_payment_id", "razorpay_signature", "updated_at"])

        logger.info(
            "Payment signature verified (waiting for webhook) | ref=%s | payment_id=%s",
            payment.payment_reference,
            razorpay_payment_id,
        )
        return payment

    def refund_payment(
        self,
        payment: Payment,
        amount: Decimal | None = None,
    ) -> dict:
        """
        Initiate a refund for a succeeded payment.
        Amount: None = full refund, Decimal = partial refund.
        """
        if payment.status != Payment.Status.SUCCEEDED:
            from apps.common.exceptions import ApplicationError
            raise ApplicationError(
                f"Cannot refund a payment with status '{payment.status}'."
            )

        if not payment.razorpay_payment_id:
            from apps.common.exceptions import ApplicationError
            raise ApplicationError("No Razorpay payment ID on record.")

        refund = self.razorpay.refund_payment(
            payment_id=payment.razorpay_payment_id,
            amount=amount,
            notes={"payment_reference": payment.payment_reference},
        )

        payment.status = Payment.Status.REFUNDED
        payment.save(update_fields=["status", "updated_at"])

        logger.info(
            "Payment refunded | ref=%s | razorpay_refund_id=%s",
            payment.payment_reference,
            refund.get("id"),
        )
        return refund
