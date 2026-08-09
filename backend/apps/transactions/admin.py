"""Transaction admin registration."""

from django.contrib import admin

from apps.transactions.models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        "transaction_reference",
        "transaction_type",
        "status",
        "amount",
        "currency",
        "sender_email",
        "receiver_email",
        "created_at",
    ]
    list_filter = ["transaction_type", "status", "currency", "created_at"]
    search_fields = [
        "transaction_reference",
        "description",
        "razorpay_payment_id",
        "sender_wallet__user__email",
        "receiver_wallet__user__email",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]

    @admin.display(description="Sender")
    def sender_email(self, obj):
        return obj.sender_wallet.user.email if obj.sender_wallet else "-"

    @admin.display(description="Receiver")
    def receiver_email(self, obj):
        return obj.receiver_wallet.user.email if obj.receiver_wallet else "-"
