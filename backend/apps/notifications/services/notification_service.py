"""
Notification service.

Creates in-app notifications and dispatches async email notifications.
All methods are non-blocking (they enqueue Celery tasks for email sending).
"""

import logging
from decimal import Decimal

from apps.notifications.models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """Factory methods for creating notifications and triggering emails."""

    @staticmethod
    def _create(
        user,
        notification_type: str,
        title: str,
        message: str,
        metadata: dict | None = None,
        send_email: bool = True,
    ) -> Notification:
        """
        Create an in-app notification and optionally dispatch an email.
        """
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            metadata=metadata or {},
        )

        if send_email:
            from apps.notifications.tasks import send_email_notification
            send_email_notification.delay(notification.id)

        return notification

    @staticmethod
    def notify_deposit_success(user, amount: Decimal, tx_reference: str) -> None:
        try:
            NotificationService._create(
                user=user,
                notification_type=Notification.NotificationType.DEPOSIT_SUCCESS,
                title="Deposit Successful",
                message=f"₹{amount} has been added to your wallet. Reference: {tx_reference}",
                metadata={"amount": str(amount), "transaction_reference": tx_reference},
            )
        except Exception as e:
            logger.exception("Failed to create deposit notification: %s", e)

    @staticmethod
    def notify_payment_failed(user, amount: Decimal) -> None:
        try:
            NotificationService._create(
                user=user,
                notification_type=Notification.NotificationType.PAYMENT_FAILED,
                title="Payment Failed",
                message=f"Your payment of ₹{amount} failed. Please try again.",
                metadata={"amount": str(amount)},
            )
        except Exception as e:
            logger.exception("Failed to create payment failed notification: %s", e)

    @staticmethod
    def notify_transfer_sent(sender, receiver, amount: Decimal, tx_reference: str) -> None:
        try:
            NotificationService._create(
                user=sender,
                notification_type=Notification.NotificationType.TRANSFER_SENT,
                title="Transfer Sent",
                message=f"₹{amount} sent to {receiver.email}. Reference: {tx_reference}",
                metadata={
                    "amount": str(amount),
                    "receiver_email": receiver.email,
                    "transaction_reference": tx_reference,
                },
            )
        except Exception as e:
            logger.exception("Failed to create transfer-sent notification: %s", e)

    @staticmethod
    def notify_transfer_received(receiver, sender, amount: Decimal, tx_reference: str) -> None:
        try:
            NotificationService._create(
                user=receiver,
                notification_type=Notification.NotificationType.TRANSFER_RECEIVED,
                title="Transfer Received",
                message=f"You received ₹{amount} from {sender.email}. Reference: {tx_reference}",
                metadata={
                    "amount": str(amount),
                    "sender_email": sender.email,
                    "transaction_reference": tx_reference,
                },
            )
        except Exception as e:
            logger.exception("Failed to create transfer-received notification: %s", e)

    @staticmethod
    def notify_recurring_processed(user, receiver, amount: Decimal, tx_reference: str) -> None:
        try:
            NotificationService._create(
                user=user,
                notification_type=Notification.NotificationType.RECURRING_PROCESSED,
                title="Recurring Payment Processed",
                message=f"Recurring payment of ₹{amount} to {receiver.email} completed. Reference: {tx_reference}",
                metadata={
                    "amount": str(amount),
                    "receiver_email": receiver.email,
                    "transaction_reference": tx_reference,
                },
            )
        except Exception as e:
            logger.exception("Failed to create recurring-processed notification: %s", e)

    @staticmethod
    def notify_recurring_failed(user, amount: Decimal, receiver_email: str) -> None:
        try:
            NotificationService._create(
                user=user,
                notification_type=Notification.NotificationType.RECURRING_FAILED,
                title="Recurring Payment Failed",
                message=(
                    f"Recurring payment of ₹{amount} to {receiver_email} failed "
                    "and has been cancelled due to repeated failures."
                ),
                metadata={"amount": str(amount), "receiver_email": receiver_email},
            )
        except Exception as e:
            logger.exception("Failed to create recurring-failed notification: %s", e)
