"""Payments URL configuration."""

from django.urls import path

from apps.payments.views import (
    CreatePaymentOrderView,
    PaymentDetailView,
    PaymentListView,
    RazorpayWebhookView,
    RefundPaymentView,
    VerifyPaymentView,
)

urlpatterns = [
    path("create-order/", CreatePaymentOrderView.as_view(), name="payment-create-order"),
    path("verify/", VerifyPaymentView.as_view(), name="payment-verify"),
    path("webhook/", RazorpayWebhookView.as_view(), name="razorpay-webhook"),
    path("", PaymentListView.as_view(), name="payment-list"),
    path("<uuid:pk>/", PaymentDetailView.as_view(), name="payment-detail"),
    path("<uuid:pk>/refund/", RefundPaymentView.as_view(), name="payment-refund"),
]
