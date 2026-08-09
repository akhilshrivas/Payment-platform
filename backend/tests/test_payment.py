import json
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.payments.models import Payment, RazorpayWebhookEvent
from apps.transactions.models import Transaction


@pytest.mark.django_db
class TestPaymentAPI:
    """Test Razorpay order creation and verification."""

    def test_order_creation_authentication(self, api_client):
        """Unauthenticated user cannot create order."""
        url = reverse("payment-create-order")
        res = api_client.post(url, {"amount": 500})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_amount(self, api_client, user):
        api_client.force_authenticate(user=user)
        url = reverse("payment-create-order")
        
        res = api_client.post(url, {"amount": -10})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

        res = api_client.post(url, {"amount": 0})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_successful_order_creation(self, api_client, user, mocker):
        """Mocks Razorpay SDK and tests order creation."""
        api_client.force_authenticate(user=user)
        url = reverse("payment-create-order")

        # Mock the Razorpay service
        mock_create = mocker.patch("apps.payments.services.razorpay_service.RazorpayService.create_order")
        mock_create.return_value = {"id": "order_test_123"}

        res = api_client.post(url, {"amount": 500, "description": "Add money"})
        
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["success"] is True
        assert res.data["data"]["razorpay_order_id"] == "order_test_123"
        assert "razorpay_key_id" in res.data["data"]
        
        payment = Payment.objects.get(id=res.data["data"]["payment_id"])
        assert payment.user == user
        assert payment.amount == Decimal("500.00")
        assert payment.status == Payment.Status.PENDING

    def test_razorpay_api_failure(self, api_client, user, mocker):
        api_client.force_authenticate(user=user)
        url = reverse("payment-create-order")

        mock_create = mocker.patch("apps.payments.services.razorpay_service.RazorpayService.create_order")
        mock_create.side_effect = Exception("Razorpay API down")

        res = api_client.post(url, {"amount": 500})
        assert res.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Payment should be marked FAILED
        payment = Payment.objects.first()
        assert payment.status == Payment.Status.FAILED

    def test_valid_payment_signature_and_wallet_credit(self, api_client, user, mocker):
        """Verifies signature, ensures wallet is credited and tx created exactly once."""
        api_client.force_authenticate(user=user)
        
        payment = Payment.objects.create(
            user=user,
            amount=Decimal("100.00"),
            payment_reference="PAY_123",
            razorpay_order_id="order_123",
            status=Payment.Status.PENDING
        )
        
        mock_verify = mocker.patch("apps.payments.services.razorpay_service.RazorpayService.verify_payment_signature")
        mock_verify.return_value = True

        url = reverse("payment-verify")
        data = {
            "payment_id": str(payment.id),
            "razorpay_order_id": "order_123",
            "razorpay_payment_id": "pay_123",
            "razorpay_signature": "valid_signature"
        }

        # First verification
        res = api_client.post(url, data)
        assert res.status_code == status.HTTP_200_OK
        
        payment.refresh_from_db()
        assert payment.status == Payment.Status.SUCCEEDED
        assert payment.razorpay_payment_id == "pay_123"
        
        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("100.00")
        assert Transaction.objects.filter(receiver_wallet=user.wallet).count() == 1

        # Duplicate verification (idempotency)
        res2 = api_client.post(url, data)
        assert res2.status_code == status.HTTP_200_OK
        
        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("100.00") # Still 100
        assert Transaction.objects.filter(receiver_wallet=user.wallet).count() == 1 # Still 1

    def test_invalid_payment_signature(self, api_client, user, mocker):
        api_client.force_authenticate(user=user)
        
        payment = Payment.objects.create(
            user=user,
            amount=Decimal("100.00"),
            payment_reference="PAY_123",
            razorpay_order_id="order_123",
            status=Payment.Status.PENDING
        )
        
        mock_verify = mocker.patch("apps.payments.services.razorpay_service.RazorpayService.verify_payment_signature")
        mock_verify.return_value = False

        url = reverse("payment-verify")
        res = api_client.post(url, {
            "payment_id": str(payment.id),
            "razorpay_order_id": "order_123",
            "razorpay_payment_id": "pay_123",
            "razorpay_signature": "invalid_signature"
        })
        
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "signature verification failed" in res.data["message"].lower()

    def test_payment_belonging_to_another_user(self, api_client, user, another_user, mocker):
        """User2 tries to verify User1's payment"""
        api_client.force_authenticate(user=another_user)
        
        payment = Payment.objects.create(
            user=user,
            amount=Decimal("100.00"),
            payment_reference="PAY_123",
            razorpay_order_id="order_123",
            status=Payment.Status.PENDING
        )
        
        mock_verify = mocker.patch("apps.payments.services.razorpay_service.RazorpayService.verify_payment_signature")
        mock_verify.return_value = True

        url = reverse("payment-verify")
        res = api_client.post(url, {
            "payment_id": str(payment.id),
            "razorpay_order_id": "order_123",
            "razorpay_payment_id": "pay_123",
            "razorpay_signature": "valid_signature"
        })
        
        assert res.status_code == status.HTTP_200_OK
        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("100.00")
        
        another_user.wallet.refresh_from_db()
        assert another_user.wallet.balance == Decimal("0.00")


@pytest.mark.django_db
class TestWebhookAPI:
    """Test Razorpay Webhook processing."""
    
    def test_valid_webhook_payment_captured(self, api_client, user, mocker):
        payment = Payment.objects.create(
            user=user,
            amount=Decimal("250.00"),
            payment_reference="PAY_WH1",
            razorpay_order_id="order_WH1",
            status=Payment.Status.PENDING
        )
        
        mock_verify = mocker.patch("apps.payments.services.razorpay_service.RazorpayService.verify_webhook_signature")
        mock_verify.return_value = True

        url = reverse("razorpay-webhook")
        payload = {
            "id": "event_123",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_WH1",
                        "order_id": "order_WH1",
                        "amount": 25000
                    }
                }
            }
        }
        
        # First webhook
        res = api_client.post(url, json.dumps(payload), content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE="sig")
        assert res.status_code == status.HTTP_200_OK
        
        payment.refresh_from_db()
        assert payment.status == Payment.Status.SUCCEEDED
        
        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("250.00")
        
        # Second webhook (duplicate)
        res2 = api_client.post(url, json.dumps(payload), content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE="sig")
        assert res2.status_code == status.HTTP_200_OK
        
        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("250.00") # Still 250

    def test_invalid_webhook_signature(self, api_client, mocker):
        from apps.common.exceptions import WebhookVerificationError
        mock_verify = mocker.patch("apps.payments.services.razorpay_service.RazorpayService.verify_webhook_signature")
        mock_verify.side_effect = WebhookVerificationError("Bad sig")

        url = reverse("razorpay-webhook")
        res = api_client.post(url, "{}", content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE="invalid")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_failed_payment_webhook(self, api_client, user, mocker):
        payment = Payment.objects.create(
            user=user,
            amount=Decimal("250.00"),
            payment_reference="PAY_WH2",
            razorpay_order_id="order_WH2",
            status=Payment.Status.PENDING
        )
        
        mock_verify = mocker.patch("apps.payments.services.razorpay_service.RazorpayService.verify_webhook_signature")
        mock_verify.return_value = True

        url = reverse("razorpay-webhook")
        payload = {
            "id": "event_124",
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_WH2",
                        "order_id": "order_WH2",
                        "amount": 25000,
                        "error_code": "BAD_REQUEST"
                    }
                }
            }
        }
        
        res = api_client.post(url, json.dumps(payload), content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE="sig")
        assert res.status_code == status.HTTP_200_OK
        
        payment.refresh_from_db()
        assert payment.status == Payment.Status.FAILED
        
        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("0.00")

    def test_already_paid_payment(self, api_client, user, mocker):
        payment = Payment.objects.create(
            user=user,
            amount=Decimal("100.00"),
            payment_reference="PAY_WH3",
            razorpay_order_id="order_WH3",
            status=Payment.Status.SUCCEEDED
        )
        user.wallet.balance = Decimal("100.00")
        user.wallet.save()
        
        mock_verify = mocker.patch("apps.payments.services.razorpay_service.RazorpayService.verify_webhook_signature")
        mock_verify.return_value = True

        url = reverse("razorpay-webhook")
        payload = {
            "id": "event_125",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_WH3",
                        "order_id": "order_WH3",
                        "amount": 10000
                    }
                }
            }
        }
        
        res = api_client.post(url, json.dumps(payload), content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE="sig")
        assert res.status_code == status.HTTP_200_OK
        
        user.wallet.refresh_from_db()
        # Should not credit again!
        assert user.wallet.balance == Decimal("100.00")
