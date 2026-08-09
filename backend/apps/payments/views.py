"""
Payment views.

Endpoints:
  POST /api/payments/create-order/    — Create Razorpay order
  POST /api/payments/verify/          — Verify payment signature
  GET  /api/payments/                 — List user's payments
  GET  /api/payments/<id>/            — Payment detail
  POST /api/payments/<id>/refund/     — Initiate refund
  POST /api/payments/webhook/         — Razorpay webhook (no auth)
"""

import json
import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView

from apps.common.exceptions import ApplicationError, PaymentNotFoundError, WebhookVerificationError
from apps.common.pagination import StandardPagination
from apps.payments.models import Payment
from apps.payments.serializers import (
    CreatePaymentOrderSerializer,
    PaymentSerializer,
    RefundPaymentSerializer,
    VerifyPaymentSerializer,
)
from apps.payments.services.payment_service import PaymentService
from apps.payments.services.razorpay_service import RazorpayService
from apps.payments.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)


class CreatePaymentOrderView(APIView):
    """
    POST /api/payments/create-order/

    Creates a Razorpay order and returns checkout data.
    The frontend uses this to open Razorpay Checkout.
    NEVER returns RAZORPAY_KEY_SECRET.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = CreatePaymentOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            service = PaymentService()
            checkout_data = service.create_payment_order(
                user=request.user,
                amount=serializer.validated_data["amount"],
                currency=serializer.validated_data.get("currency", "INR"),
                description=serializer.validated_data.get("description", ""),
            )
            return Response(
                {
                    "success": True,
                    "message": "Payment order created. Proceed to checkout.",
                    "data": checkout_data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ApplicationError as e:
            return Response(
                {"success": False, "message": e.message, "errors": {}},
                status=e.code,
            )
        except Exception as e:
            logger.exception("Failed to create payment order: %s", e)
            return Response(
                {"success": False, "message": "Failed to create payment order.", "errors": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VerifyPaymentView(APIView):
    """
    POST /api/payments/verify/

    Verifies the Razorpay signature after checkout.
    This confirms the payment is authentic, but wallet credit
    still happens only via the verified webhook.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            service = PaymentService()
            payment = service.verify_and_confirm_payment(
                payment_id=str(serializer.validated_data["payment_id"]),
                razorpay_order_id=serializer.validated_data["razorpay_order_id"],
                razorpay_payment_id=serializer.validated_data["razorpay_payment_id"],
                razorpay_signature=serializer.validated_data["razorpay_signature"],
            )
            return Response(
                {
                    "success": True,
                    "message": "Payment verified. Wallet update is being processed.",
                    "data": PaymentSerializer(payment).data,
                }
            )
        except (ApplicationError, PaymentNotFoundError) as e:
            return Response(
                {"success": False, "message": e.message, "errors": {}},
                status=e.code,
            )


class PaymentListView(ListAPIView):
    """GET /api/payments/ — User's payment history."""

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class PaymentDetailView(RetrieveAPIView):
    """GET /api/payments/<id>/ — Single payment detail."""

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(
            {
                "success": True,
                "message": "Payment retrieved.",
                "data": PaymentSerializer(instance).data,
            }
        )


class RefundPaymentView(APIView):
    """POST /api/payments/<id>/refund/ — Initiate a refund."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: str) -> Response:
        try:
            payment = Payment.objects.get(pk=pk, user=request.user)
        except Payment.DoesNotExist:
            return Response(
                {"success": False, "message": "Payment not found.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RefundPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            service = PaymentService()
            refund = service.refund_payment(
                payment=payment,
                amount=serializer.validated_data.get("amount"),
            )
            return Response(
                {
                    "success": True,
                    "message": "Refund initiated successfully.",
                    "data": {
                        "refund_id": refund.get("id"),
                        "payment_reference": payment.payment_reference,
                        "payment_status": payment.status,
                    },
                }
            )
        except ApplicationError as e:
            return Response(
                {"success": False, "message": e.message, "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RazorpayWebhookView(APIView):
    """
    POST /api/payments/webhook/

    Razorpay calls this endpoint for payment events.

    Security:
    - No authentication (Razorpay cannot authenticate)
    - Signature MUST be verified using RAZORPAY_WEBHOOK_SECRET
    - Raw body is used for signature verification (not parsed JSON)
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        # 1. Read raw body (critical for signature verification)
        raw_body = request.body.decode("utf-8")

        # 2. Get the signature header
        signature = request.headers.get("X-Razorpay-Signature", "")
        if not signature:
            logger.warning("Webhook received without X-Razorpay-Signature header.")
            return Response(
                {"success": False, "message": "Missing signature header.", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Verify the signature
        try:
            razorpay_service = RazorpayService()
            razorpay_service.verify_webhook_signature(raw_body, signature)
        except WebhookVerificationError:
            return Response(
                {"success": False, "message": "Webhook signature verification failed.", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4. Parse payload
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            logger.error("Webhook payload is not valid JSON.")
            return Response(
                {"success": False, "message": "Invalid JSON payload.", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event_id = payload.get("id", "")
        event_type = payload.get("event", "")

        if not event_id or not event_type:
            logger.warning("Webhook missing event id or type: %s", payload)
            return Response(
                {"success": False, "message": "Missing event id or type.", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("Webhook received | event_id=%s | type=%s", event_id, event_type)

        # 5. Process event (idempotent)
        try:
            WebhookService.process_event(
                event_id=event_id,
                event_type=event_type,
                payload=payload,
            )
        except Exception as e:
            logger.exception("Webhook processing error: %s", e)
            # Return 200 to prevent Razorpay retrying for application-level errors
            return Response(
                {"success": False, "message": "Webhook processing failed.", "errors": {}},
                status=status.HTTP_200_OK,
            )

        return Response({"success": True, "message": "Webhook processed."}, status=status.HTTP_200_OK)
