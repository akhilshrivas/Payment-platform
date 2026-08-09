import pytest
from django.urls import reverse
from rest_framework import status
from apps.notifications.models import Notification

@pytest.mark.django_db
class TestNotificationsAPI:
    def test_list_notifications(self, auth_client, user):
        client, user_obj = auth_client
        
        Notification.objects.create(
            user=user_obj,
            notification_type="PAYMENT_SUCCESS",
            title="Test",
            message="Test msg"
        )
        Notification.objects.create(
            user=user_obj,
            notification_type="TRANSFER_SENT",
            title="Test 2",
            message="Test msg 2"
        )

        url = reverse('notification-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 2

    def test_mark_as_read(self, auth_client, user):
        client, user_obj = auth_client
        
        notif = Notification.objects.create(
            user=user_obj,
            notification_type="PAYMENT_SUCCESS",
            title="Test",
            message="Test msg",
            is_read=False
        )

        url = reverse('notification-mark-read', kwargs={'pk': notif.id})
        response = client.patch(url)
        assert response.status_code == status.HTTP_200_OK
        
        notif.refresh_from_db()
        assert notif.is_read is True
