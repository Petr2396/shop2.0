"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile
from django.contrib.auth import get_user_model

#@receiver(post_save, sender=User)
#def create_or_update_user_profile(sender, instance, created, **kwargs):
    #if created:
        #Profile.objects.get_or_create(user=instance)


User = get_user_model()

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        # Создаем профиль с пустым телефоном (если phone может быть пустым)
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                'phone': '',  # ← Заполняем пустой строкой
                # добавь другие обязательные поля если есть
            }
        )

        """