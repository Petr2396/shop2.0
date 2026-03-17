import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import Profile
from catalog.models import Product
from payments.views import create_payment

from .cart import Cart
from .forms import OrderCreateForm, ReturnRequestForm
from .models import Order, OrderItem, PromoCode, ReturnRequest
from .services.yandex_delivery import offers_info, normalize_offers, YandexDeliveryError

logger = logging.getLogger(__name__)
# Корзина
def cart_detail(request):
    cart = Cart(request)
    
    cart.clean() 
    return render(request, "orders/cart_detail.html", {
        "cart": cart,
        "total_price": cart.get_total_price()
    })


def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)

    ok, msg = cart.add(product=product, quantity=1)

    cart_qty = sum(item["quantity"] for item in cart.cart.values())

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "ok": bool(ok),
            "cart_qty": cart_qty,
            "message": msg if msg else f'Товар «{product.name}» добавлен в корзину',
        })

    if ok:
        messages.success(request, msg)
    else:
        messages.warning(request, msg)

    return redirect(request.META.get("HTTP_REFERER", reverse("catalog:product_list")))


def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect("orders:cart_detail")


@require_POST
def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)

    quantity = int(request.POST.get("quantity", 1))
    ok, msg = cart.update(product, quantity)

    cart_qty = sum(item["quantity"] for item in cart.cart.values())

    return JsonResponse({
        "success": bool(ok),
        "message": msg,
        "item_total": cart.get_item_total_price(product) if str(product.id) in cart.cart else 0,
        "total_price": cart.get_total_price(),
        "quantity": cart.cart.get(str(product.id), {}).get("quantity", 0),
        "cart_qty": cart_qty,
    })

# orders/views.py


def order_create(request):
    cart = Cart(request)

    if request.method == "POST":
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)

            # ====== ПРИВЯЗКА ПОЛЬЗОВАТЕЛЯ / ПРОФИЛЯ ======
            if request.user.is_authenticated:
                order.customer = request.user

                profile = getattr(request.user, "profile", None)

                order.first_name = request.user.first_name or order.first_name
                order.last_name = request.user.last_name or order.last_name
                order.email = request.user.email or order.email

                if profile:
                    order.phone = getattr(profile, "phone", "") or order.phone
                    if not (order.address or "").strip():
                        order.address = getattr(profile, "address", "") or order.address

            # ====== ЯНДЕКС ПВЗ ======
            if order.delivery_method == "yandex":
                order.yandex_pvz_id = (request.POST.get("yandex_pvz_id") or "").strip() or None
                order.yandex_pvz_address = (request.POST.get("yandex_pvz_address") or "").strip() or None
                order.yandex_pvz_type = (request.POST.get("yandex_pvz_type") or "").strip() or None

                pay = request.POST.get("yandex_pvz_payment_methods")
                pos = request.POST.get("yandex_pvz_position")

                import json
                try:
                    order.yandex_pvz_payment_methods = json.loads(pay) if pay else None
                except Exception:
                    order.yandex_pvz_payment_methods = None

                try:
                    order.yandex_pvz_position = json.loads(pos) if pos else None
                except Exception:
                    order.yandex_pvz_position = None

                if not order.yandex_pvz_id:
                    messages.error(request, "Выберите пункт выдачи Яндекса на карте.")
                    return render(request, "orders/create.html", {
                        "cart": cart,
                        "form": form,
                        "total_with_discount": cart.get_total_with_discount(),
                        "discount": cart.get_discount(),
                    })
            else:
                order.yandex_pvz_id = None
                order.yandex_pvz_address = None
                order.yandex_pvz_type = None
                order.yandex_pvz_payment_methods = None
                order.yandex_pvz_position = None

            # ====== ПРОМОКОД (как было) ======
            promo_applied = False
            now = timezone.now()

            if getattr(cart, "promo_code", None):
                code = (cart.promo_code.get("code") or "").strip()

                if code:
                    with transaction.atomic():
                        updated = (
                            PromoCode.objects
                            .select_for_update()
                            .filter(
                                code__iexact=code,
                                active=True,
                                valid_from__lte=now,
                                valid_to__gte=now,
                                used_count__lt=F("max_usage"),
                            )
                            .update(used_count=F("used_count") + 1)
                        )

                        if updated == 1:
                            promo = PromoCode.objects.get(code__iexact=code)
                            order.promo_code = promo.code
                            order.discount = promo.discount
                            order.total_with_discount = cart.get_total_with_discount()
                            promo_applied = True
                        else:
                            try:
                                cart.remove_promo_code()
                            except Exception:
                                pass

            if not promo_applied:
                order.promo_code = None
                order.discount = 0
                order.total_with_discount = None

            # ============================================================
            # ✅ ОСТАТКИ + СОЗДАНИЕ ЗАКАЗА (ОДИН РАЗ) В ОДНОЙ ТРАНЗАКЦИИ
            # ============================================================
            with transaction.atomic():
                items = list(cart)

                if not items:
                    messages.error(request, "Корзина пуста.")
                    return redirect("orders:cart_detail")

                # 1) сколько чего нужно
                need = {}
                for it in items:
                    pid = it["product"].id
                    need[pid] = need.get(pid, 0) + int(it["quantity"])

                product_ids = list(need.keys())

                # 2) лочим товары
                locked_products = {
                    p.id: p
                    for p in Product.objects.select_for_update().filter(id__in=product_ids)
                }

                # 3) проверяем остатки / активность
                for pid, qty in need.items():
                    p = locked_products.get(pid)

                    if not p:
                        messages.error(request, "Один из товаров больше не существует.")
                        return redirect("orders:cart_detail")

                    # если у тебя нет is_active — убери эту проверку
                    if hasattr(p, "is_active") and not p.is_active:
                        messages.error(request, f"Товар «{p.name}» сейчас недоступен.")
                        return redirect("orders:cart_detail")

                    # если у тебя нет stock — это место упадёт, значит поле нужно добавить
                    if getattr(p, "stock", None) is None:
                        messages.error(request, "Остатки ещё не настроены (нет поля stock).")
                        return redirect("orders:cart_detail")

                    if p.stock <= 0:
                        messages.error(request, f"Товар «{p.name}» закончился.")
                        return redirect("orders:cart_detail")

                    if p.stock < qty:
                        messages.error(request, f"Недостаточно товара «{p.name}». Доступно: {p.stock} шт.")
                        return redirect("orders:cart_detail")

                # 4) сохраняем заказ
                order.save()

                # 5) сохраняем позиции
                for it in items:
                    order.items.create(
                        product=it["product"],
                        price=it["price"],
                        quantity=it["quantity"],
                    )

                # 6) списываем остатки
                for pid, qty in need.items():
                    Product.objects.filter(id=pid).update(stock=F("stock") - qty)

            # ===== Очищаем корзину =====
            cart.clear()

            # 🔥 если пользователь не вошёл — подтверждение по телефону/паролю
            if not request.user.is_authenticated:
                request.session["order_id"] = order.id
                return redirect("orders:confirm_order")

            # 🔥 если вошёл — сразу оплата
            return create_payment(request, order)

    else:
        form = OrderCreateForm()

    return render(request, "orders/create.html", {
        "cart": cart,
        "form": form,
        "total_with_discount": cart.get_total_with_discount(),
        "discount": cart.get_discount(),
    })


def order_success(request):
    return render(request, "orders/order_success.html")


def confirm_order(request):
    # Если уже авторизован — сразу к оплате
    if request.user.is_authenticated:
        return _redirect_to_payment(request)

    phone = ""
    show_password = False
    user_exists = False

    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password")

        if not phone:
            messages.error(request, "Введите номер телефона")
            return redirect("orders:confirm_order")

        profile = Profile.objects.filter(phone=phone).select_related("user").first()

        # ШАГ 1: ввели только телефон
        if not password:
            show_password = True
            user_exists = bool(profile)

        # ШАГ 2: телефон + пароль
        else:
            if profile:
                user = authenticate(
                    request,
                    username=profile.user.username,
                    password=password
                )
                if not user:
                    messages.error(request, "Неверный пароль")
                    show_password = True
                    user_exists = True
                else:
                    login(request, user)
                    return _redirect_to_payment(request)
            else:
                # создаём нового пользователя
                username = f"user_{phone.replace('+', '')}"

                user = User.objects.create_user(
                    username=username,
                    password=password
                )

                Profile.objects.create(
                    user=user,
                    phone=phone
                )

                login(request, user)
                return _redirect_to_payment(request)

    return render(
        request,
        "orders/confirm.html",
        {
            "phone": phone,
            "show_password": show_password,
            "user_exists": user_exists,
        }
    )


def _redirect_to_payment(request):
    order_id = request.session.get("order_id")
    if not order_id:
        messages.error(request, "Заказ не найден")
        return redirect("orders:my_orders")

    order = Order.objects.get(id=order_id)
    order.customer = request.user

    # ✅ ДОЗАПОЛНЯЕМ заказ данными профиля (важно для гостевого оформления)
    profile = getattr(request.user, "profile", None)

    if not order.first_name:
        order.first_name = request.user.first_name or ""
    if not order.last_name:
        order.last_name = request.user.last_name or ""
    if not order.email:
        order.email = request.user.email or ""

    if profile:
        if not order.phone:
            order.phone = getattr(profile, "phone", "") or ""
        if not order.address:
            order.address = getattr(profile, "address", "") or ""

    order.save()

    del request.session["order_id"]

    return create_payment(request, order)




# Личный кабинет заказов
@login_required
def my_orders(request):
    # Активные заказы (новый, в сборке, отправлен)
    active_orders = (
        Order.objects.filter(customer=request.user)
        .exclude(status__in=["delivered", "canceled"])
        .order_by("-created")
    )

    # Архивные (доставленные и отмененные)
    archived_orders = (
        Order.objects.filter(customer=request.user, status__in=["delivered", "canceled"])
        .order_by("-created")
    )

    # Возвраты текущего пользователя
    returns = (
        ReturnRequest.objects.filter(user=request.user)
        .select_related("order")
        .prefetch_related("items")
        .order_by("-created_at")
    )

    return render(
        request,
        "orders/my_orders.html",
        {
            "active_orders": active_orders,
            "archived_orders": archived_orders,
            "returns": returns,
        },
    )


@login_required
def cancel_order(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id, customer=request.user)

        if order.status in ["new", "processing"]:
            order.status = "canceled"
            order.save()

    return redirect("orders:my_orders")



@require_POST
def apply_promo_code(request):
    code = (request.POST.get("code") or "").strip()
    cart = Cart(request)

    if not code:
        return JsonResponse({
            "success": False,
            "message": "Введите промокод"
        })

    success, result = cart.apply_promo_code(code)

    if success:
        promo = PromoCode.objects.filter(code__iexact=code).first()
        return JsonResponse({
            "success": True,
            "discount": promo.discount,
            "original_total": str(cart.get_total_price()),
            "new_total": str(cart.get_total_with_discount()),
            "message": f"Промокод применён! Скидка {promo.discount}%"
        })

    return JsonResponse({
        "success": False,
        "message": result if isinstance(result, str) else "Ошибка при применении промокода"
    })
    
def remove_promo_code(request):
    cart = Cart(request)
    cart.remove_promo_code()
    return JsonResponse({
        'success': True,
        'original_total': cart.get_total_price(),
        'new_total': cart.get_total_price(),
        'message': 'Промокод удален'
    })






@login_required
def create_return_request(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)

    if request.method == "POST":
        form = ReturnRequestForm(request.POST, request.FILES, order=order)
        if form.is_valid():
            return_request = form.save(commit=False)
            return_request.order = order
            return_request.user = request.user
            return_request.save()
            form.save_m2m()
            messages.success(request, "Заявка на возврат отправлена и находится на рассмотрении ✅")
            return redirect("orders:my_orders")
    else:
        form = ReturnRequestForm(order=order)

    return render(request, "orders/return_request.html", {"form": form, "order": order})


@login_required
def return_request(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)

    if request.method == "POST":
        form = ReturnRequestForm(request.POST, request.FILES, order=order)
        if form.is_valid():
            return_req = form.save(commit=False)
            return_req.order = order
            return_req.user = request.user
            return_req.save()
            form.save_m2m()
            return redirect("orders:my_orders")
    else:
        form = ReturnRequestForm(order=order)

    return render(request, "orders/return_request.html", {"form": form, "order": order})


@login_required
def my_returns(request):
    returns = request.user.return_requests.select_related("order").prefetch_related("items")
    return render(request, "orders/my_returns.html", {"returns": returns})


@require_GET
def yandex_offers(request):
    address = (request.GET.get("address") or "").strip()

    if not address:
        return JsonResponse({"success": False, "message": "Не передан адрес"}, status=400)

    try:
        raw = offers_info(
            platform_station_id=settings.YANDEX_PLATFORM_STATION_ID,
            full_address=address,
            send_unix=True,
            last_mile_policy="time_interval",
        )

        variants = normalize_offers(raw)

        if not variants:
            return JsonResponse({
                "success": False,
                "message": "Нет доступных интервалов доставки для этого адреса",
                "raw": raw,
            }, status=200)

        return JsonResponse({
            "success": True,
            "variants": variants,
            "raw": raw,
        }, status=200)

    except YandexDeliveryError as e:
        # ✅ это ожидаемая ошибка: например no_delivery_options
        return JsonResponse({
            "success": False,
            "message": str(e),
        }, status=200)

    except Exception as e:
        # ❌ неожиданная ошибка
        print("YANDEX OFFERS ERROR:", e)
        return JsonResponse({
            "success": False,
            "message": "Ошибка связи с Яндекс Доставкой",
            "details": str(e),
        }, status=500)


