"""Notifications Celery tasks — async email sending."""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(name="apps.notifications.tasks.send_email_notification", bind=True, max_retries=3)
def send_email_notification(self, notification_id: str) -> None:
    """
    Send an email for a given Notification instance.
    Retries up to 3 times on failure (e.g. SMTP timeout).

    NOTE: Logs sensitive detail at WARNING level only (no card data/tokens).
    """
    from apps.notifications.models import Notification

    try:
        notification = Notification.objects.select_related("user").get(pk=notification_id)
    except Notification.DoesNotExist:
        logger.warning("Email task: Notification %s not found.", notification_id)
        return

    user = notification.user
    if not user.email:
        logger.warning("User %s has no email address.", user.id)
        return

    try:
        send_mail(
            subject=f"[PaymentPlatform] {notification.title}",
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(
            "Email sent | notification_id=%s | type=%s | to=%s",
            notification_id,
            notification.notification_type,
            user.email,
        )
    except Exception as exc:
        logger.error(
            "Email send failed | notification_id=%s | error=%s | retrying...",
            notification_id,
            exc,
        )
        raise self.retry(exc=exc, countdown=60)  # Retry after 60 seconds
