import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.ai.models import AIConversation
from apps.ai.serializers import AIConversationSerializer, ChatRequestSerializer
from apps.ai.services.assistant_service import AssistantService

logger = logging.getLogger(__name__)

class AIViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing AI conversations and chat.
    Ensures users can only access their own conversations.
    """
    serializer_class = AIConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AIConversation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def chat(self, request):
        """
        Process a chat message.
        Expects: {"message": "Hello", "conversation_id": "uuid"} (optional)
        """
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        message_content = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id')
        
        if conversation_id:
            try:
                conversation = self.get_queryset().get(id=conversation_id)
            except AIConversation.DoesNotExist:
                return Response(
                    {"error": "Conversation not found or unauthorized."},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Create a new conversation if none provided
            title = message_content[:50] + "..." if len(message_content) > 50 else message_content
            conversation = AIConversation.objects.create(user=request.user, title=title)
            
        logger.info(f"Processing AI chat | user={request.user.id} | conversation={conversation.id}")
        
        assistant = AssistantService(user=request.user)
        reply = assistant.process_message(conversation, message_content)
        
        return Response({
            "conversation_id": conversation.id,
            "message": reply,
            "title": conversation.title
        })
