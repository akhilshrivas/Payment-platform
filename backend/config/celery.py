"""
Celery application configuration for the Payment Platform.
"""

import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("payment_platform")

# Read configuration from Django settings (CELERY_ prefix).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps.
app.autodiscover_tasks()

# ============================================================
# Periodic Tasks (Celery Beat Schedule)
# ============================================================
app.conf.beat_schedule = {
    # Process recurring payments every day at 00:05 UTC
    "process-recurring-payments-daily": {
        "task": "apps.recurring_payments.tasks.process_recurring_payments",
        "schedule": crontab(hour=0, minute=5),
        "options": {"expires": 3600},  # Expire if not processed within 1 hour
    },
    # Clean up old unprocessed webhook events (weekly)
    "cleanup-old-webhook-events": {
        "task": "apps.payments.tasks.cleanup_old_webhook_events",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),  # Sunday 02:00
    },
}

app.conf.timezone = "UTC"


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:
    """Debug task — prints request info."""
    print(f"Request: {self.request!r}")
