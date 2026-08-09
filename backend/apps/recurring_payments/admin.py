"""Recurring payments admin registration."""

from django.contrib import admin

from apps.recurring_payments.models import RecurringPayment


@admin.register(RecurringPayment)
class RecurringPaymentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "receiver",
        "amount",
        "currency",
        "frequency",
        "status",
        "next_payment_date",
        "last_payment_date",
        "failure_count",
        "created_at",
    ]
    list_filter = ["status", "frequency", "currency", "created_at"]
    search_fields = ["user__email", "receiver__email", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]
