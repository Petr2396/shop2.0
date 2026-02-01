from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST 
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from accounts.models import Profile
from catalog.models import Product
from .cart import Cart
from .models import Order, OrderItem
from .forms import OrderCreateForm
from payments.views import create_payment
from .models import PromoCode
from .models import Order, ReturnRequest
from .forms import ReturnRequestForm
from payments.views import create_payment
from accounts.services import get_or_create_user_by_phone


# Корзина
def cart_detail(request):
    cart = Cart(request)
    return render(request, "orders/cart_detail.html", {
        "cart": cart,
        "total_price": cart.get_total_price()
    })


def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)

    cart.add(product=product, quantity=1)

    # 🔹 считаем общее количество товаров в корзине
    cart_qty = sum(item["quantity"] for item in cart.cart.values())

    # 🔹 если AJAX-запрос — возвращаем JSON
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "ok": True,
            "cart_qty": cart_qty,
            "message": f'Товар «{product.name}» добавлен в корзину',
        })

    # 🔹 обычное поведение (если JS отключён)
    messages.success(request, f'Товар «{product.name}» добавлен в корзину ✅')
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
    quantity = int(request.POST.get('quantity', 1))
    
    cart.update(product, quantity)
    
    # Возвращаем обновленные данные корзины в JSON
    return JsonResponse({
        'success': True,
        'item_total': cart.get_item_total_price(product),
        'total_price': cart.get_total_price(),
        'quantity': quantity
    })


# orders/views.py


def order_create(request):
    cart = Cart(request)

    if request.method == "POST":
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)

            if request.user.is_authenticated:
                order.customer = request.user

            if hasattr(cart, 'promo_code') and cart.promo_code:
                order.promo_code = cart.promo_code.get('code')
                order.discount = cart.promo_code.get('discount', 0)
                order.total_with_discount = cart.get_total_with_discount()

            order.save()

            for item in cart:
                order.items.create(
                    product=item["product"],
                    price=item["price"],
                    quantity=item["quantity"],
                )

            cart.clear()

            # 🔥 если пользователь не вошёл — подтверждение
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

        # 🔹 ШАГ 1 — ввели ТОЛЬКО телефон
        if not password:
            show_password = True
            user_exists = bool(profile)

        # 🔹 ШАГ 2 — телефон + пароль
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


"""

def confirm_order(request):
  

    # Если уже авторизован — сразу к оплате
    if request.user.is_authenticated:
        return _redirect_to_payment(request)

    phone = ""
    show_password = False
    user_exists = False

    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")

        if not phone:
            messages.error(request, "Введите номер телефона")
            return redirect("orders:confirm_order")

        # Ищем профиль по телефону
        profile = (
            Profile.objects
            .filter(phone=phone)
            .select_related("user")
            .first()
        )

        # ------------------------
        # Пользователь СУЩЕСТВУЕТ
        # ------------------------
        if profile:
            user_exists = True
            show_password = True

            if password:
                user = authenticate(
                    request,
                    username=profile.user.username,
                    password=password
                )
                if user:
                    login(request, user)
                    return _redirect_to_payment(request)
                else:
                    messages.error(request, "Неверный пароль")

        # ------------------------
        # Пользователя НЕТ
        # ------------------------
        else:
            show_password = True

            if password:
                # создаём пользователя
                username = f"user_{phone.replace('+', '').replace(' ', '')}"

                user = User.objects.create_user(
                    username=username,
                    password=password
                )

                # ❗️Профиль УЖЕ создан сигналом
                profile = user.profile
                profile.phone = phone
                profile.save()

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
"""

def _redirect_to_payment(request):
    order_id = request.session.get("order_id")
    if not order_id:
        messages.error(request, "Заказ не найден")
        return redirect("orders:my_orders")

    order = Order.objects.get(id=order_id)
    order.customer = request.user
    order.save(update_fields=["customer"])

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



def apply_promo_code(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        cart = Cart(request)
        
        success, result = cart.apply_promo_code(code)
        
        if success:
            return JsonResponse({
                'success': True,
                'discount': result.discount,
                'original_total': cart.get_total_price(),  # Добавляем
                'new_total': cart.get_total_with_discount(),
                'message': f'Промокод применен! Скидка {result.discount}%'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def remove_promo_code(request):
    cart = Cart(request)
    cart.remove_promo_code()
    return JsonResponse({
        'success': True,
        'new_total': cart.get_total_price(),
        'message': 'Промокод удален'
    })






@login_required
def create_return_request(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

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





