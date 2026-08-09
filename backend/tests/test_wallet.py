import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.wallets.models import Wallet
from apps.transactions.models import Transaction
from apps.wallets.services.wallet_service import WalletService
from apps.common.exceptions import InsufficientBalanceError, ApplicationError

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user1(db):
    user = User.objects.create_user(
        email="alice@example.com",
        password="password123",
        first_name="Alice",
        last_name="Doe"
    )
    # Wallet is auto-created by signal
    return user

@pytest.fixture
def user2(db):
    user = User.objects.create_user(
        email="bob@example.com",
        password="password123",
        first_name="Bob",
        last_name="Smith"
    )
    return user

@pytest.mark.django_db
class TestWalletAPI:
    def test_authenticated_wallet_access(self, api_client, user1):
        api_client.force_authenticate(user=user1)
        url = reverse("wallet-detail")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["owner_email"] == user1.email

    def test_unauthenticated_wallet_rejection(self, api_client):
        url = reverse("wallet-detail")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestWalletService:
    def test_credit_debit_balance(self, user1):
        wallet = user1.wallet
        assert wallet.balance == Decimal("0.00")
        
        # Credit
        WalletService.credit(wallet, Decimal("100.50"))
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("100.50")
        
        # Debit
        WalletService.debit(wallet, Decimal("50.00"))
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("50.50")
        
    def test_negative_credit_rejected(self, user1):
        wallet = user1.wallet
        with pytest.raises(ValueError):
            WalletService.credit(wallet, Decimal("-10.00"))
            
    def test_insufficient_balance_debit(self, user1):
        wallet = user1.wallet
        with pytest.raises(InsufficientBalanceError):
            WalletService.debit(wallet, Decimal("100.00"))

    def test_successful_transfer_and_isolation(self, user1, user2):
        # Alice starts with 200
        WalletService.credit(user1.wallet, Decimal("200.00"))
        
        tx = WalletService.transfer(
            sender=user1,
            receiver_email=user2.email,
            amount=Decimal("50.00"),
            description="Dinner"
        )
        
        user1.wallet.refresh_from_db()
        user2.wallet.refresh_from_db()
        
        assert user1.wallet.balance == Decimal("150.00")
        assert user2.wallet.balance == Decimal("50.00")
        
        assert tx.sender_wallet == user1.wallet
        assert tx.receiver_wallet == user2.wallet
        assert tx.amount == Decimal("50.00")
        assert tx.status == Transaction.Status.COMPLETED

    def test_transfer_insufficient_balance(self, user1, user2):
        WalletService.credit(user1.wallet, Decimal("20.00"))
        
        with pytest.raises(InsufficientBalanceError):
            WalletService.transfer(
                sender=user1,
                receiver_email=user2.email,
                amount=Decimal("50.00")
            )
            
        user1.wallet.refresh_from_db()
        user2.wallet.refresh_from_db()
        assert user1.wallet.balance == Decimal("20.00")
        assert user2.wallet.balance == Decimal("0.00")

    def test_transfer_zero_negative_amount(self, user1, user2):
        WalletService.credit(user1.wallet, Decimal("100.00"))
        with pytest.raises(ValueError):
            WalletService.transfer(sender=user1, receiver_email=user2.email, amount=Decimal("0.00"))
            
        with pytest.raises(ValueError):
            WalletService.transfer(sender=user1, receiver_email=user2.email, amount=Decimal("-10.00"))

    def test_transfer_nonexistent_receiver(self, user1):
        WalletService.credit(user1.wallet, Decimal("100.00"))
        with pytest.raises(ApplicationError, match="No active user found"):
            WalletService.transfer(sender=user1, receiver_email="ghost@example.com", amount=Decimal("50.00"))

    def test_self_transfer(self, user1):
        WalletService.credit(user1.wallet, Decimal("100.00"))
        with pytest.raises(ApplicationError, match="cannot transfer money to yourself"):
            WalletService.transfer(sender=user1, receiver_email=user1.email, amount=Decimal("10.00"))


@pytest.mark.django_db
class TestTransactionAPI:
    def test_transaction_history_isolation(self, api_client, user1, user2):
        WalletService.credit(user1.wallet, Decimal("200.00"))
        WalletService.transfer(sender=user1, receiver_email=user2.email, amount=Decimal("50.00"))
        
        # User 1 history
        api_client.force_authenticate(user=user1)
        res1 = api_client.get(reverse("transaction-list"))
        assert res1.status_code == status.HTTP_200_OK
        assert res1.data["pagination"]["count"] == 1
        
        # User 2 history
        api_client.force_authenticate(user=user2)
        res2 = api_client.get(reverse("transaction-list"))
        assert res2.status_code == status.HTTP_200_OK
        assert res2.data["pagination"]["count"] == 1
        
        # Third user sees nothing
        user3 = User.objects.create_user(email="charlie@test.com", password="pwd")
        api_client.force_authenticate(user=user3)
        res3 = api_client.get(reverse("transaction-list"))
        assert res3.data["pagination"]["count"] == 0
