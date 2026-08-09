"""Wallet admin registration."""

from django.contrib import admin

from apps.wallets.models import Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "currency", "balance", "available_balance", "created_at"]
    list_filter = ["currency", "created_at"]
    search_fields = ["user__email", "id"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]
