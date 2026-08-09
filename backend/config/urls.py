"""
Root URL configuration for the Payment Platform API.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),

    # Authentication
    path("api/auth/", include("apps.accounts.urls")),

    # Wallet
    path("api/wallet/", include("apps.wallets.urls")),

    # Transactions
    path("api/transactions/", include("apps.transactions.urls")),

    # Payments & Razorpay
    path("api/payments/", include("apps.payments.urls")),

    # Recurring payments
    path("api/recurring-payments/", include("apps.recurring_payments.urls")),

    # Notifications
    path("api/notifications/", include("apps.notifications.urls")),

    # OpenAPI / Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# ============================================================
# Development-only additions
# ============================================================
if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
