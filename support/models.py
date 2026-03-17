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

    class Meta:
        verbose_name = "Чат поддержки"
        verbose_name_plural = "Чаты поддержки"

    def __str__(self):
        return f"Чат с {self.user.username}"


def support_upload_to(instance, filename):
    return f"support/{instance.chat_id}/{filename}"


class SupportMessage(models.Model):
    chat = models.ForeignKey(
        SupportChat,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    text = models.TextField()
    is_from_admin = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    is_read_by_admin = models.BooleanField(default=False) 
    attachment = models.FileField(upload_to=support_upload_to, blank=True, null=True)
    attachment_name = models.CharField(max_length=255, blank=True, default="")
    attachment_mime = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return self.text[:50]

