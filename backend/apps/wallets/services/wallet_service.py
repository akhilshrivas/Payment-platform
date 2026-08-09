"""
Wallet service layer.

All business logic for wallet operations lives here — not in views.
"""

import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.common.exceptions import InsufficientBalanceError
from apps.common.utils import generate_reference
from apps.wallets.models import Wallet

logger = logging.getLogger(__name__)
User = get_user_model()


class WalletService:
    """Provides atomic wallet operations."""

    @staticmethod
    @transaction.atomic
    def credit(wallet: Wallet, amount: Decimal, description: str = "") -> None:
        """
        Credit (add) an amount to a wallet.
        Must be called inside a transaction. Uses select_for_update.
        """
        if amount <= Decimal("0"):
            raise ValueError(f"Credit amount must be positive, got {amount}.")

        locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        locked_wallet.balance += amount
        locked_wallet.available_balance += amount
        locked_wallet.save(update_fields=["balance", "available_balance", "updated_at"])
        logger.info(
            "Wallet credited | user=%s | amount=%s | new_balance=%s",
            locked_wallet.user_id,
            amount,
            locked_wallet.balance,
        )

    @staticmethod
    @transaction.atomic
    def debit(wallet: Wallet, amount: Decimal, description: str = "") -> None:
        """
        Debit (subtract) an amount from a wallet.
        Raises InsufficientBalanceError if not enough available balance.
        """
        if amount <= Decimal("0"):
            raise ValueError(f"Debit amount must be positive, got {amount}.")

        locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        if locked_wallet.available_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance. Available: {locked_wallet.available_balance}, "
                f"Requested: {amount}."
            )

        locked_wallet.balance -= amount
        locked_wallet.available_balance -= amount
        locked_wallet.save(update_fields=["balance", "available_balance", "updated_at"])
        logger.info(
            "Wallet debited | user=%s | amount=%s | new_balance=%s",
            locked_wallet.user_id,
            amount,
            locked_wallet.balance,
        )

    @staticmethod
    @transaction.atomic
    def transfer(
        sender: User,
        receiver_email: str,
        amount: Decimal,
        description: str = "",
    ):
        """
        Atomic wallet-to-wallet transfer.

        Steps:
        1. Validate inputs.
        2. Resolve receiver.
        3. Lock both wallets in consistent order (by PK) to prevent deadlocks.
        4. Check available balance.
        5. Debit sender, credit receiver.
        6. Create a completed Transaction record.
        7. Trigger notifications.

        Returns the completed Transaction instance.
        """
        from apps.transactions.models import Transaction
        from apps.notifications.services.notification_service import NotificationService

        # --- Validation ---
        if amount <= Decimal("0"):
            raise ValueError("Transfer amount must be greater than zero.")

        normalized_email = receiver_email.lower().strip()

        if sender.email.lower() == normalized_email:
            from apps.common.exceptions import ApplicationError

            raise ApplicationError("You cannot transfer money to yourself.")

        try:
            receiver = User.objects.get(email=normalized_email, is_active=True)
        except User.DoesNotExist:
            from apps.common.exceptions import ApplicationError

            raise ApplicationError(
                f"No active user found with email '{receiver_email}'.",
                code=404,
            )

        try:
            sender_wallet = Wallet.objects.get(user=sender)
            receiver_wallet = Wallet.objects.get(user=receiver)
        except Wallet.DoesNotExist:
            from apps.common.exceptions import ApplicationError

            raise ApplicationError("Wallet not found for sender or receiver.")

        # Lock wallets in consistent PK order to avoid deadlocks
        wallets = Wallet.objects.select_for_update().filter(
            pk__in=[sender_wallet.pk, receiver_wallet.pk]
        ).order_by("pk")
        wallet_map = {w.pk: w for w in wallets}

        locked_sender = wallet_map[sender_wallet.pk]
        locked_receiver = wallet_map[receiver_wallet.pk]

        # Check balance
        if locked_sender.available_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance. Available: ₹{locked_sender.available_balance}, "
                f"Requested: ₹{amount}."
            )

        # Debit sender
        locked_sender.balance -= amount
        locked_sender.available_balance -= amount
        locked_sender.save(update_fields=["balance", "available_balance", "updated_at"])

        # Credit receiver
        locked_receiver.balance += amount
        locked_receiver.available_balance += amount
        locked_receiver.save(update_fields=["balance", "available_balance", "updated_at"])

        # Create Transaction record
        tx = Transaction.objects.create(
            transaction_reference=generate_reference("TRF"),
            sender_wallet=locked_sender,
            receiver_wallet=locked_receiver,
            amount=amount,
            currency=locked_sender.currency,
            transaction_type=Transaction.TransactionType.TRANSFER,
            status=Transaction.Status.COMPLETED,
            description=description or f"Transfer to {receiver.email}",
        )

        logger.info(
            "Transfer completed | ref=%s | sender=%s | receiver=%s | amount=%s",
            tx.transaction_reference,
            sender.email,
            receiver.email,
            amount,
        )

        # Async notifications (non-blocking)
        NotificationService.notify_transfer_sent(sender, receiver, amount, tx.transaction_reference)
        NotificationService.notify_transfer_received(receiver, sender, amount, tx.transaction_reference)

        return tx
