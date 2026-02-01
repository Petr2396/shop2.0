from django.urls import path
from .views import review_create_or_update

app_name = "reviews"

urlpatterns = [
    path("product/<slug:product_slug>/review/", review_create_or_update, name="create_or_update"),
]
