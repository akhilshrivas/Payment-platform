"""Payments Celery tasks."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="apps.payments.tasks.cleanup_old_webhook_events")
def cleanup_old_webhook_events() -> None:
    """
    Clean up processed webhook events older than 90 days.
    Keeps unprocessed events for investigation.
    """
    from apps.payments.models import RazorpayWebhookEvent

    cutoff = timezone.now() - timezone.timedelta(days=90)
    deleted_count, _ = RazorpayWebhookEvent.objects.filter(
        processed=True,
        processed_at__lt=cutoff,
    ).delete()
    logger.info("Deleted %d old processed webhook events.", deleted_count)
