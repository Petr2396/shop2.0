from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser

class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    phone = models.CharField(
        max_length=20,
        unique=True,      # 🔥 обязательно
        verbose_name="Телефон"
    )

    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Профиль {self.phone}"

    
#@receiver(post_save, sender=User)
#def create_user_profile(sender, instance, created, **kwargs):
    #if created:
        # Проверяем, нет ли уже профиля
       # if not hasattr(instance, 'profile'):
            #Profile.objects.create(user=instance)

#@receiver(post_save, sender=User)
#def save_user_profile(sender, instance, **kwargs):
    #if hasattr(instance, 'profile'):
        #instance.profile.save()



