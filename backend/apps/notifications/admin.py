"""Notifications admin registration."""

from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "notification_type", "title", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["user__email", "title", "message"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]
