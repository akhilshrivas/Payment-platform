"""
Payment and RazorpayWebhookEvent models.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Payment(BaseModel):
    """
    Represents a Razorpay-mediated payment.

    Status lifecycle:
      CREATED → PENDING → SUCCEEDED / FAILED / CANCELLED
      SUCCEEDED → REFUNDED (after refund)

    Wallet is credited ONLY when a verified webhook confirms SUCCEEDED.
    Frontend redirect alone is NOT sufficient to credit the wallet.
    """

    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        PENDING = "PENDING", "Pending"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"
        REFUNDED = "REFUNDED", "Refunded"

    payment_reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Payment amount in INR.",
    )
    currency = models.CharField(max_length=3, default="INR")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
    )
    # Razorpay IDs (populated as payment progresses)
    razorpay_order_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Razorpay Order ID (order_...).",
    )
    razorpay_payment_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Razorpay Payment ID (pay_...).",
    )
    razorpay_signature = models.CharField(
        max_length=512,
        blank=True,
        null=True,
        help_text="HMAC-SHA256 signature from Razorpay.",
    )
    description = models.TextField(blank=True, default="")
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary metadata (e.g. {user_id, payment_reference}).",
    )

    class Meta:
        db_table = "payments_payment"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["user", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=Decimal("0.00")),
                name="payment_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"Payment({self.payment_reference}, {self.status}, {self.amount} {self.currency})"


class RazorpayWebhookEvent(BaseModel):
    """
    Immutable record of every Razorpay webhook event received.

    Ensures idempotency: the same event is never processed twice.
    """

    razorpay_event_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Razorpay's unique event ID.",
    )
    event_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="e.g. payment.captured, payment.failed",
    )
    processed = models.BooleanField(default=False)
    payload = models.JSONField(help_text="Full raw webhook payload.")
    error_message = models.TextField(blank=True, default="")
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payments_razorpay_webhook_event"
        verbose_name = "Razorpay Webhook Event"
        verbose_name_plural = "Razorpay Webhook Events"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"WebhookEvent({self.razorpay_event_id}, {self.event_type}, processed={self.processed})"
