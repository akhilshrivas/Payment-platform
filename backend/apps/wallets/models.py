"""
Wallet model.

One wallet per user. Monetary values use DecimalField — never float.
Balance constraints are enforced at the database level.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Wallet(BaseModel):
    """
    User's digital wallet.

    Rules:
    - One wallet per user (OneToOneField).
    - Default currency: INR (configurable via settings.DEFAULT_CURRENCY).
    - balance and available_balance must never go negative
      (enforced by CheckConstraint + service-layer logic).
    - All balance mutations must occur inside a database transaction.
    - Use select_for_update() before any balance change.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    currency = models.CharField(
        max_length=3,
        default="INR",
        help_text="ISO 4217 currency code.",
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total balance including reserved funds.",
    )
    available_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Balance available for transfers.",
    )

    class Meta:
        db_table = "wallets_wallet"
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"
        constraints = [
            models.CheckConstraint(
                check=models.Q(balance__gte=0),
                name="balance_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(available_balance__gte=0),
                name="wallet_available_balance_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"Wallet({self.user.email}, {self.currency} {self.balance})"
