"""
Phase 1 smoke tests — project setup and infrastructure.
Tests Django configuration, app registration, and basic imports.
"""

import pytest
from django.conf import settings


class TestDjangoConfiguration:
    """Smoke tests for Django settings and app registration."""

    def test_auth_user_model(self):
        """Custom User model should be used."""
        assert settings.AUTH_USER_MODEL == "accounts.User"

    def test_database_is_postgresql(self):
        """Database engine should be PostgreSQL."""
        db_engine = settings.DATABASES["default"]["ENGINE"]
        assert "postgresql" in db_engine

    def test_jwt_configured(self):
        """SimpleJWT should be in installed apps and configured."""
        assert "rest_framework_simplejwt" in settings.INSTALLED_APPS

    def test_drf_uses_jwt_auth(self):
        """DRF default authentication should use JWT."""
        auth_classes = settings.REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES", [])
        assert "rest_framework_simplejwt.authentication.JWTAuthentication" in auth_classes

    def test_required_apps_installed(self):
        """All required local apps should be registered."""
        required = [
            "apps.accounts",
            "apps.wallets",
            "apps.transactions",
            "apps.payments",
            "apps.recurring_payments",
            "apps.notifications",
            "apps.common",
        ]
        for app in required:
            assert app in settings.INSTALLED_APPS, f"{app} not in INSTALLED_APPS"

    def test_celery_configured(self):
        """Celery should be configured."""
        assert hasattr(settings, "CELERY_BROKER_URL")
        assert hasattr(settings, "CELERY_RESULT_BACKEND")

    def test_razorpay_config_keys_present(self):
        """Razorpay config keys should exist in settings."""
        assert hasattr(settings, "RAZORPAY_KEY_ID")
        assert hasattr(settings, "RAZORPAY_KEY_SECRET")
        assert hasattr(settings, "RAZORPAY_WEBHOOK_SECRET")

    def test_cors_configured(self):
        """CORS middleware and allowed origins should be configured."""
        assert "corsheaders.middleware.CorsMiddleware" in settings.MIDDLEWARE


class TestModelImports:
    """Verify all models can be imported without errors."""

    def test_user_model_import(self):
        from apps.accounts.models import User
        assert User is not None

    def test_wallet_model_import(self):
        from apps.wallets.models import Wallet
        assert Wallet is not None

    def test_transaction_model_import(self):
        from apps.transactions.models import Transaction
        assert Transaction is not None

    def test_payment_model_import(self):
        from apps.payments.models import Payment, RazorpayWebhookEvent
        assert Payment is not None
        assert RazorpayWebhookEvent is not None

    def test_recurring_payment_model_import(self):
        from apps.recurring_payments.models import RecurringPayment
        assert RecurringPayment is not None

    def test_notification_model_import(self):
        from apps.notifications.models import Notification
        assert Notification is not None


class TestServiceImports:
    """Verify all service classes can be imported."""

    def test_razorpay_service_import(self):
        from apps.payments.services.razorpay_service import RazorpayService
        assert RazorpayService is not None

    def test_payment_service_import(self):
        from apps.payments.services.payment_service import PaymentService
        assert PaymentService is not None

    def test_webhook_service_import(self):
        from apps.payments.services.webhook_service import WebhookService
        assert WebhookService is not None

    def test_wallet_service_import(self):
        from apps.wallets.services.wallet_service import WalletService
        assert WalletService is not None

    def test_recurring_service_import(self):
        from apps.recurring_payments.services.recurring_service import RecurringPaymentService
        assert RecurringPaymentService is not None

    def test_notification_service_import(self):
        from apps.notifications.services.notification_service import NotificationService
        assert NotificationService is not None


class TestUtilities:
    """Test shared utility functions."""

    def test_generate_reference(self):
        from apps.common.utils import generate_reference
        ref = generate_reference("TXN")
        assert ref.startswith("TXN-")
        assert len(ref) == 20  # "TXN-" (4) + 16 hex chars = 20

    def test_generate_reference_uniqueness(self):
        from apps.common.utils import generate_reference
        refs = {generate_reference() for _ in range(100)}
        assert len(refs) == 100  # All unique

    def test_inr_to_paise(self):
        from apps.common.utils import inr_to_paise
        from decimal import Decimal
        assert inr_to_paise(Decimal("100.00")) == 10000
        assert inr_to_paise(Decimal("1.00")) == 100
        assert inr_to_paise(Decimal("0.50")) == 50

    def test_paise_to_inr(self):
        from apps.common.utils import paise_to_inr
        from decimal import Decimal
        assert paise_to_inr(10000) == Decimal("100.00")
        assert paise_to_inr(100) == Decimal("1.00")

    def test_recurring_next_date_daily(self):
        from datetime import date
        from apps.recurring_payments.services.recurring_service import RecurringPaymentService
        d = date(2024, 1, 31)
        assert RecurringPaymentService.calculate_next_date(d, "DAILY") == date(2024, 2, 1)

    def test_recurring_next_date_monthly(self):
        from datetime import date
        from apps.recurring_payments.services.recurring_service import RecurringPaymentService
        # Month-end: Jan 31 → Feb 28 (not March 3!)
        d = date(2024, 1, 31)
        result = RecurringPaymentService.calculate_next_date(d, "MONTHLY")
        assert result == date(2024, 2, 29)  # 2024 is leap year

    def test_recurring_next_date_monthly_non_leap(self):
        from datetime import date
        from apps.recurring_payments.services.recurring_service import RecurringPaymentService
        d = date(2023, 1, 31)
        result = RecurringPaymentService.calculate_next_date(d, "MONTHLY")
        assert result == date(2023, 2, 28)  # Non-leap year

    def test_recurring_next_date_yearly_leap(self):
        from datetime import date
        from apps.recurring_payments.services.recurring_service import RecurringPaymentService
        # Feb 29 2024 (leap) → Feb 28 2025 (non-leap)
        d = date(2024, 2, 29)
        result = RecurringPaymentService.calculate_next_date(d, "YEARLY")
        assert result == date(2025, 2, 28)

    def test_recurring_next_date_weekly(self):
        from datetime import date
        from apps.recurring_payments.services.recurring_service import RecurringPaymentService
        d = date(2024, 1, 1)
        assert RecurringPaymentService.calculate_next_date(d, "WEEKLY") == date(2024, 1, 8)
