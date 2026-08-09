import pytest
from datetime import date
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from apps.recurring_payments.models import RecurringPayment
from apps.recurring_payments.services.recurring_service import RecurringPaymentService
from apps.recurring_payments.tasks import process_recurring_payments

@pytest.mark.django_db
class TestRecurringService:
    def test_calculate_next_date(self):
        d = date(2024, 1, 31)
        assert RecurringPaymentService.calculate_next_date(d, "DAILY") == date(2024, 2, 1)
        assert RecurringPaymentService.calculate_next_date(d, "WEEKLY") == date(2024, 2, 7)
        assert RecurringPaymentService.calculate_next_date(d, "MONTHLY") == date(2024, 2, 29) # leap year
        assert RecurringPaymentService.calculate_next_date(d, "YEARLY") == date(2025, 1, 31)

    def test_process_single_recurring_payment(self, user, api_client, mocker):
        from apps.accounts.models import User
        from apps.wallets.models import Wallet
        receiver = User.objects.create_user(email="receiver2@example.com", first_name="B", last_name="C", password="test")
        
        # Give sender balance
        user.wallet.available_balance = Decimal("1000.00")
        user.wallet.balance = Decimal("1000.00")
        user.wallet.save()

        rp = RecurringPayment.objects.create(
            user=user,
            receiver=receiver,
            amount=Decimal("100.00"),
            frequency="DAILY",
            start_date=date.today(),
            next_payment_date=date.today(),
            status="ACTIVE"
        )

        mock_notify = mocker.patch('apps.notifications.services.notification_service.NotificationService.notify_recurring_processed')
        
        RecurringPaymentService.process_single_recurring_payment(str(rp.id))
        
        rp.refresh_from_db()
        assert rp.last_payment_date == date.today()
        assert rp.next_payment_date > date.today()
        assert rp.failure_count == 0
        
        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("900.00")
        receiver.wallet.refresh_from_db()
        assert receiver.wallet.balance == Decimal("100.00")
        mock_notify.assert_called_once()

    def test_process_insufficient_balance(self, user, mocker):
        from apps.accounts.models import User
        receiver = User.objects.create_user(email="receiver3@example.com", first_name="B", last_name="C", password="test")
        
        user.wallet.available_balance = Decimal("50.00")
        user.wallet.balance = Decimal("50.00")
        user.wallet.save()

        rp = RecurringPayment.objects.create(
            user=user,
            receiver=receiver,
            amount=Decimal("100.00"),
            frequency="DAILY",
            start_date=date.today(),
            next_payment_date=date.today(),
            status="ACTIVE"
        )
        
        RecurringPaymentService.process_single_recurring_payment(str(rp.id))
        
        rp.refresh_from_db()
        assert rp.failure_count == 1
        assert rp.status == "ACTIVE"

@pytest.mark.django_db
class TestRecurringAPI:
    def test_create_recurring_payment(self, auth_client, user):
        client, user_obj = auth_client
        from apps.accounts.models import User
        receiver = User.objects.create_user(email="receiver4@example.com", first_name="B", last_name="C", password="test")

        url = reverse('recurring-list-create')
        data = {
            "receiver_email": receiver.email,
            "amount": "200.00",
            "frequency": "MONTHLY",
            "start_date": str(date.today()),
            "description": "Monthly rent"
        }
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        
        rp = RecurringPayment.objects.get(id=response.data["data"]["id"])
        assert rp.amount == Decimal("200.00")
        assert rp.receiver == receiver

    def test_pause_resume_recurring(self, auth_client, user):
        client, user_obj = auth_client
        from apps.accounts.models import User
        receiver = User.objects.create_user(email="receiver5@example.com", first_name="B", last_name="C", password="test")
        
        rp = RecurringPayment.objects.create(
            user=user_obj,
            receiver=receiver,
            amount=Decimal("100.00"),
            frequency="WEEKLY",
            start_date=date.today(),
            next_payment_date=date.today(),
            status="ACTIVE"
        )

        pause_url = reverse('recurring-pause', kwargs={'pk': rp.id})
        response = client.post(pause_url)
        assert response.status_code == status.HTTP_200_OK
        rp.refresh_from_db()
        assert rp.status == "PAUSED"

        resume_url = reverse('recurring-resume', kwargs={'pk': rp.id})
        response = client.post(resume_url)
        assert response.status_code == status.HTTP_200_OK
        rp.refresh_from_db()
        assert rp.status == "ACTIVE"
