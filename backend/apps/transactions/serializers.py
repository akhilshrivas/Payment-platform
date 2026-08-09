"""Transaction serializers."""

from rest_framework import serializers

from apps.transactions.models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    """Full transaction representation."""

    sender_email = serializers.SerializerMethodField()
    receiver_email = serializers.SerializerMethodField()
    signed_amount = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "transaction_reference",
            "sender_email",
            "receiver_email",
            "amount",
            "signed_amount",
            "currency",
            "transaction_type",
            "status",
            "description",
            "razorpay_payment_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_sender_email(self, obj: Transaction) -> str | None:
        if obj.sender_wallet and obj.sender_wallet.user:
            return obj.sender_wallet.user.email
        return None

    def get_receiver_email(self, obj: Transaction) -> str | None:
        if obj.receiver_wallet and obj.receiver_wallet.user:
            return obj.receiver_wallet.user.email
        return None

    def get_signed_amount(self, obj: Transaction) -> str:
        """
        Returns amount with sign relative to the requesting user.
        Positive = received, Negative = sent.
        """
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return str(obj.amount)

        try:
            user_wallet = request.user.wallet
        except Exception:
            return str(obj.amount)

        if obj.receiver_wallet and obj.receiver_wallet.pk == user_wallet.pk:
            return f"+{obj.amount}"
        if obj.sender_wallet and obj.sender_wallet.pk == user_wallet.pk:
            return f"-{obj.amount}"
        return str(obj.amount)
