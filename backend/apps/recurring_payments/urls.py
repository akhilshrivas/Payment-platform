"""Recurring payments URL configuration."""

from django.urls import path

from apps.recurring_payments.views import (
    RecurringPaymentDetailView,
    RecurringPaymentListCreateView,
    RecurringPaymentPauseView,
    RecurringPaymentResumeView,
)

urlpatterns = [
    path("", RecurringPaymentListCreateView.as_view(), name="recurring-list-create"),
    path("<uuid:pk>/", RecurringPaymentDetailView.as_view(), name="recurring-detail"),
    path("<uuid:pk>/pause/", RecurringPaymentPauseView.as_view(), name="recurring-pause"),
    path("<uuid:pk>/resume/", RecurringPaymentResumeView.as_view(), name="recurring-resume"),
]
