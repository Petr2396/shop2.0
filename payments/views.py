import uuid
import json
import requests

from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from datetime import datetime
from orders.models import Order



def create_payment(request, order):
    print("=" * 80)
    print("🔄 ЗАГРУЖЕН МОДУЛЬ: payments.views")
    print(f"Время загрузки: {datetime.now()}")
    print(f"Путь к файлу: {__file__}")
    print("=" * 80)
    url = "https://api.yookassa.ru/v3/payments"
    headers = {
        "Content-Type": "application/json",
        "Idempotence-Key": str(uuid.uuid4()),
    }
    auth = (settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_API_KEY)

    # Ваш текущий домен Cloudflare
    current_domain = "https://c733719dd334696c-85-235-168-54.serveousercontent.com"

    amount = order.get_final_total()
    
    data = {
        "amount": {
            "value": str(amount),
            "currency": "RUB",
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"{current_domain}/payments/success/",
        },
        "capture": True,
        "description": f"Заказ №{order.id}",
        "metadata": {
            "order_id": order.id
        },
        # Добавляем вебхук для этого конкретного платежа
        "receipt": {
            "customer": {"email": request.user.email},
            "items": [
                {
                    "description": f"Заказ №{order.id}",
                    "quantity": "1",
                    "amount": {
                        "value": str(order.get_final_total()),
                        "currency": "RUB"
                    },
                    "vat_code": 1
                }
            ]
        }
    }

    response = requests.post(url, json=data, headers=headers, auth=auth)
    payment = response.json()

    if response.status_code == 200 and payment.get("confirmation"):
        order.payment_id = payment.get("id")
        order.save(update_fields=["payment_id"])
        
        # Сохраняем ссылку для проверки
        request.session[f'payment_{order.id}'] = payment.get("id")
        
        return redirect(payment["confirmation"]["confirmation_url"])

    messages.error(request, "Ошибка создания платежа")
    return redirect("orders:my_orders")



def payment_success(request):
    messages.info(
        request,
        "Ваш заказ успешно оплачен! Мы начнем его обрабатывать в самые кротчайшие сроки, статус заказа вы можете отслеживать на странице 'Мои заказы' в профиле"
    )
    return redirect("orders:my_orders")



@csrf_exempt
def payment_webhook(request):
    print("🔥 WEBHOOK HIT")

    if request.method == "POST":
        data = json.loads(request.body)
        print("📦 DATA:", data)

        if data.get("event") == "payment.succeeded":
            payment = data["object"]
            order_id = payment.get("metadata", {}).get("order_id")

            print("🧾 ORDER:", order_id)

            if order_id:
                order = Order.objects.get(id=order_id)
                order.is_paid = True
                order.save()
                print("✅ ORDER PAID")

        return HttpResponse(status=200)
