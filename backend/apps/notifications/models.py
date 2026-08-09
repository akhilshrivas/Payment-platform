"""Notification model."""

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Notification(BaseModel):
    """
    In-app notification for a user.

    Also used as a trigger for async email sending.
    """

    class NotificationType(models.TextChoices):
        DEPOSIT_SUCCESS = "DEPOSIT_SUCCESS", "Deposit Success"
        PAYMENT_FAILED = "PAYMENT_FAILED", "Payment Failed"
        TRANSFER_SENT = "TRANSFER_SENT", "Transfer Sent"
        TRANSFER_RECEIVED = "TRANSFER_RECEIVED", "Transfer Received"
        RECURRING_PROCESSED = "RECURRING_PROCESSED", "Recurring Processed"
        RECURRING_FAILED = "RECURRING_FAILED", "Recurring Failed"
        SYSTEM = "SYSTEM", "System"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra data (transaction_reference, amount, etc.).",
    )

    class Meta:
        db_table = "notifications_notification"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Notification({self.user.email}, {self.notification_type}, read={self.is_read})"
