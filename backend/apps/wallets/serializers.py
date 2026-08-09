"""Wallet serializers."""

from decimal import Decimal
from rest_framework import serializers

from apps.wallets.models import Wallet


class WalletSerializer(serializers.ModelSerializer):
    """Full wallet representation."""

    owner_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Wallet
        fields = [
            "id",
            "owner_email",
            "currency",
            "balance",
            "available_balance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class WalletBalanceSerializer(serializers.ModelSerializer):
    """Lightweight balance-only view."""

    class Meta:
        model = Wallet
        fields = ["currency", "balance", "available_balance"]
        read_only_fields = fields


class TransferSerializer(serializers.Serializer):
    """Input for wallet-to-wallet transfer."""

    receiver_email = serializers.EmailField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    description = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")

    def validate_amount(self, value):
        from django.conf import settings
        from decimal import Decimal

        max_amount = Decimal(getattr(settings, "MAXIMUM_TRANSFER_AMOUNT", "500000.00"))
        if value > max_amount:
            raise serializers.ValidationError(
                f"Transfer amount cannot exceed ₹{max_amount}."
            )
        return value
