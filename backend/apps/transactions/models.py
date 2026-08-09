"""
Transaction model.

Records every money movement in the system.
"""

from decimal import Decimal

from django.db import models

from apps.common.models import BaseModel


class Transaction(BaseModel):
    """
    Immutable record of a monetary event.

    Fields:
    - transaction_reference — unique human-readable ID
    - sender_wallet         — source wallet (null for external deposits)
    - receiver_wallet       — destination wallet (null for external withdrawals)
    - amount                — always positive (direction inferred from type)
    - currency              — ISO 4217 code
    - transaction_type      — DEPOSIT/WITHDRAWAL/TRANSFER/PAYMENT/REFUND
    - status                — lifecycle state
    - description           — free-text note
    - razorpay_payment_id   — Razorpay payment ID (for Razorpay-initiated txns)
    """

    class TransactionType(models.TextChoices):
        DEPOSIT = "DEPOSIT", "Deposit"
        WITHDRAWAL = "WITHDRAWAL", "Withdrawal"
        TRANSFER = "TRANSFER", "Transfer"
        PAYMENT = "PAYMENT", "Payment"
        REFUND = "REFUND", "Refund"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"
        REFUNDED = "REFUNDED", "Refunded"

    transaction_reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique human-readable reference (e.g. TXN-ABC123).",
    )
    sender_wallet = models.ForeignKey(
        "wallets.Wallet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_transactions",
        help_text="Source wallet. Null for external deposits.",
    )
    receiver_wallet = models.ForeignKey(
        "wallets.Wallet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_transactions",
        help_text="Destination wallet. Null for external withdrawals.",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Always positive. Direction is inferred from transaction_type.",
    )
    currency = models.CharField(max_length=3, default="INR")
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    description = models.TextField(blank=True, default="")
    razorpay_payment_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Razorpay payment ID for gateway-initiated transactions.",
    )

    class Meta:
        db_table = "transactions_transaction"
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=Decimal("0.00")),
                name="transaction_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"Transaction({self.transaction_reference}, {self.transaction_type}, {self.status})"
