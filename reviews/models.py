from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models


class Review(models.Model):
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField()  # 1..5
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "user")  # 1 отзыв на товар от 1 пользователя
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.product} — {self.rating}"
