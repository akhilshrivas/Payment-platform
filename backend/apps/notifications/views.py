"""
Notifications views.

Endpoints:
  GET   /api/notifications/          — List unread + recent notifications
  POST  /api/notifications/mark-all-read/ — Mark all as read
  PATCH /api/notifications/<id>/read/ — Mark one as read
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPagination
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationListView(APIView):
    """GET /api/notifications/ — paginated list (newest first)."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = Notification.objects.filter(user=request.user).order_by("-created_at")

        # Optional filter for unread only
        unread_only = request.query_params.get("unread") == "true"
        if unread_only:
            qs = qs.filter(is_read=False)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = NotificationSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)

        # Append unread count
        response.data["unread_count"] = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
        return response


class MarkAllReadView(APIView):
    """POST /api/notifications/mark-all-read/"""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response(
            {
                "success": True,
                "message": f"{count} notification(s) marked as read.",
                "data": {},
            }
        )


class MarkReadView(APIView):
    """PATCH /api/notifications/<id>/read/"""

    permission_classes = [IsAuthenticated]

    def patch(self, request: Request, pk: str) -> Response:
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response(
                {"success": False, "message": "Notification not found.", "errors": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(
            {
                "success": True,
                "message": "Notification marked as read.",
                "data": NotificationSerializer(notification).data,
            }
        )
