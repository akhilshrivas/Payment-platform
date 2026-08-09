"""Wallets URL configuration."""

from django.urls import path

from apps.wallets.views import WalletBalanceView, WalletDetailView, WalletTransferView

urlpatterns = [
    path("", WalletDetailView.as_view(), name="wallet-detail"),
    path("balance/", WalletBalanceView.as_view(), name="wallet-balance"),
    path("transfer/", WalletTransferView.as_view(), name="wallet-transfer"),
]
