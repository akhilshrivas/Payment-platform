"""Payment admin registration."""

from django.contrib import admin

from apps.payments.models import Payment, RazorpayWebhookEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "payment_reference",
        "user",
        "amount",
        "currency",
        "status",
        "razorpay_order_id",
        "razorpay_payment_id",
        "created_at",
    ]
    list_filter = ["status", "currency", "created_at"]
    search_fields = [
        "payment_reference",
        "user__email",
        "razorpay_order_id",
        "razorpay_payment_id",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(RazorpayWebhookEvent)
class RazorpayWebhookEventAdmin(admin.ModelAdmin):
    list_display = [
        "razorpay_event_id",
        "event_type",
        "processed",
        "created_at",
        "processed_at",
    ]
    list_filter = ["processed", "event_type", "created_at"]
    search_fields = ["razorpay_event_id", "event_type"]
    readonly_fields = ["id", "created_at", "updated_at", "razorpay_event_id", "payload"]
    ordering = ["-created_at"]
