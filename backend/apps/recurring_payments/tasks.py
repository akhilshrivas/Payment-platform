"""
Recurring payment Celery tasks.

Scheduled via Celery Beat to run daily at 00:05 UTC.
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.recurring_payments.tasks.process_recurring_payments",
    bind=True,
    max_retries=1,
)
def process_recurring_payments(self) -> None:
    """
    Find all ACTIVE recurring payments due today or earlier and process them.

    This task is idempotent: each RecurringPayment row is locked via
    select_for_update before processing, preventing double execution.
    """
    from apps.recurring_payments.models import RecurringPayment
    from apps.recurring_payments.services.recurring_service import RecurringPaymentService

    today = timezone.now().date()
    logger.info("Processing recurring payments for %s", today)

    due_ids = list(
        RecurringPayment.objects.filter(
            status=RecurringPayment.Status.ACTIVE,
            next_payment_date__lte=today,
        ).values_list("id", flat=True)
    )

    logger.info("Found %d recurring payment(s) due.", len(due_ids))

    processed = 0
    failed = 0
    for rp_id in due_ids:
        try:
            RecurringPaymentService.process_single_recurring_payment(str(rp_id))
            processed += 1
        except Exception as e:
            failed += 1
            logger.exception(
                "Error processing recurring payment %s: %s", rp_id, e
            )

    logger.info(
        "Recurring payment run complete | processed=%d | failed=%d",
        processed,
        failed,
    )
