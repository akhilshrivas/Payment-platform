"""Notifications URL configuration."""

from django.urls import path

from apps.notifications.views import MarkAllReadView, MarkReadView, NotificationListView

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("mark-all-read/", MarkAllReadView.as_view(), name="notification-mark-all-read"),
    path("<uuid:pk>/read/", MarkReadView.as_view(), name="notification-mark-read"),
]
