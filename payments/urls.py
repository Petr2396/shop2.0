from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("pay/<int:order_id>/", views.create_payment, name="pay"),
    path("webhook/", views.payment_webhook, name="webhook"),
    path('success/', views.payment_success, name='success'),
]