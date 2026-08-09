"""Payment serializers."""

from rest_framework import serializers

from apps.payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """Full payment representation."""

    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "payment_reference",
            "user_email",
            "amount",
            "currency",
            "status",
            "razorpay_order_id",
            "razorpay_payment_id",
            "description",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


from decimal import Decimal

class CreatePaymentOrderSerializer(serializers.Serializer):
    """Input for creating a new Razorpay payment order."""

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("1.00"),
        help_text="Amount in INR. Minimum ₹1.00.",
    )
    currency = serializers.CharField(
        max_length=3,
        default="INR",
        required=False,
    )
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="Wallet deposit",
    )


class VerifyPaymentSerializer(serializers.Serializer):
    """Input for verifying Razorpay signature after checkout."""

    payment_id = serializers.UUIDField(help_text="Our internal Payment UUID.")
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()


class RefundPaymentSerializer(serializers.Serializer):
    """Input for initiating a payment refund (optional partial amount)."""

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
        allow_null=True,
        help_text="Partial refund amount in INR. Omit for full refund.",
    )
