"""
Wallet views.

Endpoints:
  GET  /api/wallet/          — Current user's wallet details
  GET  /api/wallet/balance/  — Balance only (lightweight)
  POST /api/wallet/transfer/ — Transfer to another user
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import ApplicationError, InsufficientBalanceError
from apps.transactions.serializers import TransactionSerializer
from apps.wallets.models import Wallet
from apps.wallets.serializers import (
    TransferSerializer,
    WalletBalanceSerializer,
    WalletSerializer,
)
from apps.wallets.services.wallet_service import WalletService

logger = logging.getLogger(__name__)


class WalletDetailView(APIView):
    """GET /api/wallet/ — Full wallet details."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        try:
            wallet = request.user.wallet
        except Wallet.DoesNotExist:
            return Response(
                {"success": False, "message": "Wallet not found.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "success": True,
                "message": "Wallet retrieved successfully.",
                "data": WalletSerializer(wallet).data,
            }
        )


class WalletBalanceView(APIView):
    """GET /api/wallet/balance/ — Balance only."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        try:
            wallet = request.user.wallet
        except Wallet.DoesNotExist:
            return Response(
                {"success": False, "message": "Wallet not found.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "success": True,
                "message": "Balance retrieved.",
                "data": WalletBalanceSerializer(wallet).data,
            }
        )


class WalletTransferView(APIView):
    """POST /api/wallet/transfer/ — Transfer funds to another user."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            tx = WalletService.transfer(
                sender=request.user,
                receiver_email=serializer.validated_data["receiver_email"],
                amount=serializer.validated_data["amount"],
                description=serializer.validated_data.get("description", ""),
            )
            return Response(
                {
                    "success": True,
                    "message": "Transfer completed successfully.",
                    "data": TransactionSerializer(tx).data,
                },
                status=status.HTTP_200_OK,
            )
        except InsufficientBalanceError as e:
            return Response(
                {"success": False, "message": e.message, "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ApplicationError as e:
            return Response(
                {"success": False, "message": e.message, "errors": {}},
                status=e.code if e.code < 600 else status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Unexpected error during transfer: %s", e)
            return Response(
                {"success": False, "message": "Transfer failed. Please try again.", "errors": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
