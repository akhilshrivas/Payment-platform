"""
Signals for the accounts app.

- post_save on User: automatically creates a Wallet for every new user.
"""

import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def create_wallet_for_new_user(
    sender, instance: User, created: bool, **kwargs
) -> None:
    """
    Create a Wallet when a new User is saved for the first time.
    Import is deferred to avoid circular imports at module load time.
    """
    if created:
        from apps.wallets.models import Wallet

        wallet, was_created = Wallet.objects.get_or_create(user=instance)
        if was_created:
            logger.info("Wallet created for new user: %s", instance.email)
