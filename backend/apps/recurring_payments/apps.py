"""Recurring Payments app configuration."""

from django.apps import AppConfig


class RecurringPaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.recurring_payments"
    label = "recurring_payments"
    verbose_name = "Recurring Payments"
