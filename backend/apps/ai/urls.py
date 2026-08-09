from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.ai.views import AIViewSet

router = DefaultRouter()
router.register(r'conversations', AIViewSet, basename='ai-conversations')

urlpatterns = [
    path('', include(router.urls)),
    path('chat/', AIViewSet.as_view({'post': 'chat'}), name='ai-chat'),
]
