from django.db import models
from django.contrib.auth.models import User


class SupportChat(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="support_chat"
    )
    created = models.DateTimeField(auto_now_add=True)
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return f"Чат с {self.user.username}"


class SupportMessage(models.Model):
    chat = models.ForeignKey(
        SupportChat,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    text = models.TextField()
    is_from_admin = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:50]

