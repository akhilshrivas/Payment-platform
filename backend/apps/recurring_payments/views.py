"""
Recurring payment views.

Endpoints:
  GET    /api/recurring-payments/           — List user's recurring payments
  POST   /api/recurring-payments/           — Create new recurring payment
  GET    /api/recurring-payments/<id>/      — Detail
  PATCH  /api/recurring-payments/<id>/      — Update (amount, description, end_date)
  DELETE /api/recurring-payments/<id>/      — Cancel
  POST   /api/recurring-payments/<id>/pause/  — Pause
  POST   /api/recurring-payments/<id>/resume/ — Resume
"""

import logging
from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView

from apps.common.pagination import StandardPagination
from apps.recurring_payments.models import RecurringPayment
from apps.recurring_payments.serializers import (
    CreateRecurringPaymentSerializer,
    RecurringPaymentSerializer,
    UpdateRecurringPaymentSerializer,
)
from apps.recurring_payments.services.recurring_service import RecurringPaymentService

logger = logging.getLogger(__name__)
User = get_user_model()


class RecurringPaymentListCreateView(APIView):
    """
    GET  /api/recurring-payments/ — list
    POST /api/recurring-payments/ — create
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = RecurringPayment.objects.filter(
            user=request.user
        ).select_related("user", "receiver").order_by("-created_at")

        # Status filter
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = RecurringPaymentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = CreateRecurringPaymentSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        receiver = User.objects.get(email=data["receiver_email"])
        start_date = data["start_date"]

        rp = RecurringPayment.objects.create(
            user=request.user,
            receiver=receiver,
            amount=data["amount"],
            currency=data.get("currency", "INR").upper(),
            frequency=data["frequency"],
            start_date=start_date,
            end_date=data.get("end_date"),
            next_payment_date=start_date,  # First payment on start_date
            description=data.get("description", ""),
            status=RecurringPayment.Status.ACTIVE,
        )

        logger.info(
            "Recurring payment created | id=%s | from=%s | to=%s | amount=%s | freq=%s",
            rp.id,
            request.user.email,
            receiver.email,
            rp.amount,
            rp.frequency,
        )

        return Response(
            {
                "success": True,
                "message": "Recurring payment created successfully.",
                "data": RecurringPaymentSerializer(rp).data,
            },
            status=status.HTTP_201_CREATED,
        )


class RecurringPaymentDetailView(APIView):
    """
    GET    /api/recurring-payments/<id>/
    PATCH  /api/recurring-payments/<id>/
    DELETE /api/recurring-payments/<id>/
    """

    permission_classes = [IsAuthenticated]

    def _get_object(self, request: Request, pk: str) -> RecurringPayment | None:
        try:
            return RecurringPayment.objects.get(pk=pk, user=request.user)
        except RecurringPayment.DoesNotExist:
            return None

    def get(self, request: Request, pk: str) -> Response:
        rp = self._get_object(request, pk)
        if not rp:
            return Response(
                {"success": False, "message": "Recurring payment not found.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "success": True,
                "message": "Recurring payment retrieved.",
                "data": RecurringPaymentSerializer(rp).data,
            }
        )

    def patch(self, request: Request, pk: str) -> Response:
        rp = self._get_object(request, pk)
        if not rp:
            return Response(
                {"success": False, "message": "Recurring payment not found.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if rp.status in (RecurringPayment.Status.CANCELLED, RecurringPayment.Status.COMPLETED):
            return Response(
                {
                    "success": False,
                    "message": f"Cannot edit a {rp.status} recurring payment.",
                    "errors": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UpdateRecurringPaymentSerializer(rp, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "success": True,
                "message": "Recurring payment updated.",
                "data": RecurringPaymentSerializer(rp).data,
            }
        )

    def delete(self, request: Request, pk: str) -> Response:
        rp = self._get_object(request, pk)
        if not rp:
            return Response(
                {"success": False, "message": "Recurring payment not found.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if rp.status == RecurringPayment.Status.CANCELLED:
            return Response(
                {"success": False, "message": "Already cancelled.", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rp.status = RecurringPayment.Status.CANCELLED
        rp.save(update_fields=["status", "updated_at"])
        logger.info("Recurring payment cancelled | id=%s | user=%s", pk, request.user.email)

        return Response(
            {"success": True, "message": "Recurring payment cancelled.", "data": {}},
            status=status.HTTP_200_OK,
        )


class RecurringPaymentPauseView(APIView):
    """POST /api/recurring-payments/<id>/pause/"""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: str) -> Response:
        try:
            rp = RecurringPayment.objects.get(pk=pk, user=request.user)
        except RecurringPayment.DoesNotExist:
            return Response(
                {"success": False, "message": "Recurring payment not found.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if rp.status != RecurringPayment.Status.ACTIVE:
            return Response(
                {
                    "success": False,
                    "message": f"Can only pause ACTIVE payments. Current status: {rp.status}.",
                    "errors": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        rp.status = RecurringPayment.Status.PAUSED
        rp.save(update_fields=["status", "updated_at"])
        logger.info("Recurring payment paused | id=%s", pk)

        return Response(
            {
                "success": True,
                "message": "Recurring payment paused.",
                "data": RecurringPaymentSerializer(rp).data,
            }
        )


class RecurringPaymentResumeView(APIView):
    """POST /api/recurring-payments/<id>/resume/"""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: str) -> Response:
        try:
            rp = RecurringPayment.objects.get(pk=pk, user=request.user)
        except RecurringPayment.DoesNotExist:
            return Response(
                {"success": False, "message": "Recurring payment not found.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if rp.status != RecurringPayment.Status.PAUSED:
            return Response(
                {
                    "success": False,
                    "message": f"Can only resume PAUSED payments. Current status: {rp.status}.",
                    "errors": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        rp.status = RecurringPayment.Status.ACTIVE
        rp.save(update_fields=["status", "updated_at"])
        logger.info("Recurring payment resumed | id=%s", pk)

        return Response(
            {
                "success": True,
                "message": "Recurring payment resumed.",
                "data": RecurringPaymentSerializer(rp).data,
            }
        )
