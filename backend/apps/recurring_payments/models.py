"""
RecurringPayment model.

Represents a scheduled, repeating wallet-to-wallet transfer.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class RecurringPayment(BaseModel):
    """
    A recurring scheduled transfer from one user to another.

    next_payment_date is calculated using proper calendar arithmetic:
    - DAILY:   +1 day
    - WEEKLY:  +7 days
    - MONTHLY: dateutil.relativedelta(months=+1) — handles month-end correctly
    - YEARLY:  dateutil.relativedelta(years=+1)  — handles leap years
    """

    class Frequency(models.TextChoices):
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"
        YEARLY = "YEARLY", "Yearly"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PAUSED = "PAUSED", "Paused"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_payments",
        help_text="The user who initiates and pays for this recurring payment.",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="incoming_recurring_payments",
        help_text="The user who receives funds.",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount to transfer each period.",
    )
    currency = models.CharField(max_length=3, default="INR")
    frequency = models.CharField(
        max_length=10,
        choices=Frequency.choices,
        db_index=True,
    )
    start_date = models.DateField(help_text="Date when recurring payment starts.")
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional end date. If null, runs indefinitely.",
    )
    next_payment_date = models.DateField(
        db_index=True,
        help_text="Date when the next payment is due.",
    )
    last_payment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of the last successful payment.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    description = models.TextField(blank=True, default="")
    failure_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="Consecutive failure count (auto-cancels after threshold).",
    )

    class Meta:
        db_table = "recurring_payments_recurringpayment"
        verbose_name = "Recurring Payment"
        verbose_name_plural = "Recurring Payments"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=Decimal("0.00")),
                name="recurring_payment_amount_positive",
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F("receiver")),
                name="recurring_payment_no_self_transfer",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"RecurringPayment({self.user.email} → {self.receiver.email}, "
            f"₹{self.amount} {self.frequency}, {self.status})"
        )
