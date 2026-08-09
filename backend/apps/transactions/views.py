"""
Transaction views.

Endpoints:
  GET /api/transactions/      — Paginated list (current user's transactions)
  GET /api/transactions/<id>/ — Transaction detail
"""

import logging

from django.db.models import Q, QuerySet
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.pagination import StandardPagination
from apps.transactions.models import Transaction
from apps.transactions.serializers import TransactionSerializer

logger = logging.getLogger(__name__)


def get_user_transactions(user) -> QuerySet:
    """Return transactions where user is sender or receiver."""
    try:
        wallet = user.wallet
    except Exception:
        return Transaction.objects.none()

    return Transaction.objects.filter(
        Q(sender_wallet=wallet) | Q(receiver_wallet=wallet)
    ).select_related(
        "sender_wallet__user",
        "receiver_wallet__user",
    ).order_by("-created_at")


class TransactionListView(ListAPIView):
    """
    GET /api/transactions/

    Returns paginated list of all transactions involving the current user.

    Filters:
      ?type=DEPOSIT|WITHDRAWAL|TRANSFER|PAYMENT|REFUND
      ?status=PENDING|PROCESSING|COMPLETED|FAILED|CANCELLED|REFUNDED
      ?search=<reference or description>
      ?date_from=YYYY-MM-DD
      ?date_to=YYYY-MM-DD
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    pagination_class = StandardPagination

    def get_queryset(self) -> QuerySet:
        qs = get_user_transactions(self.request.user)

        # Type filter
        txn_type = self.request.query_params.get("type")
        if txn_type:
            qs = qs.filter(transaction_type=txn_type.upper())

        # Status filter
        txn_status = self.request.query_params.get("status")
        if txn_status:
            qs = qs.filter(status=txn_status.upper())

        # Search (reference or description)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(transaction_reference__icontains=search)
                | Q(description__icontains=search)
            )

        # Date range
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class TransactionDetailView(RetrieveAPIView):
    """GET /api/transactions/<id>/ — Single transaction detail."""

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self) -> QuerySet:
        return get_user_transactions(self.request.user)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "message": "Transaction retrieved.",
                "data": serializer.data,
            }
        )
