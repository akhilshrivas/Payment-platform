from django.db import models
from django.conf import settings
from apps.common.models import BaseModel

class AIConversation(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_conversations")
    title = models.CharField(max_length=255, blank=True, default="New Conversation")

    class Meta:
        db_table = "ai_conversation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Conversation({self.id}, User: {self.user.email})"

class AIMessage(BaseModel):
    class RoleChoices(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=RoleChoices.choices)
    content = models.TextField()

    class Meta:
        db_table = "ai_message"
        ordering = ["created_at"]

    def __str__(self):
        return f"Message({self.role}, {self.id})"
