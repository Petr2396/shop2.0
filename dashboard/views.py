from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q, Count
from django.utils import timezone
from django.db.models import Sum
from .decorators import staff_required
from orders.models import Order  
from catalog.models import Product, Category
from support.models import SupportChat, SupportMessage
from .forms import ProductForm, ProductImageFormSet
from django.contrib import messages
from .forms import CategoryForm
from orders.models import PromoCode  # поправь импорт
from .forms import PromoCodeForm

@staff_required
def index(request):
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_orders = Order.objects.count()
    paid_orders = Order.objects.filter(is_paid=True).count()
    revenue = (
        Order.objects.filter(is_paid=True)
        .aggregate(s=Sum("total_with_discount"))["s"]
    )

    return render(request, "dashboard/index.html", {
        "total_products": total_products,
        "total_categories": total_categories,
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "revenue": revenue,
    })


@staff_required
def products_list(request):
    q = (request.GET.get("q") or "").strip()
    qs = Product.objects.select_related("category").all().order_by("-id")
    if q:
        qs = qs.filter(name__icontains=q)

    return render(request, "dashboard/products_list.html", {"products": qs, "q": q})


@staff_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all().order_by("name")

    if request.method == "POST":
        product.name = (request.POST.get("name") or "").strip()
        product.description = (request.POST.get("description") or "").strip()
        product.price = request.POST.get("price") or product.price
        cat_id = request.POST.get("category") or None
        product.category_id = cat_id if cat_id else None

        # если ты добавишь stock/is_active — сюда же
        if hasattr(product, "stock"):
            product.stock = int(request.POST.get("stock") or product.stock or 0)
        if hasattr(product, "is_active"):
            product.is_active = bool(request.POST.get("is_active"))

        product.save()
        return redirect("dashboard:products_list")

    return render(request, "dashboard/product_edit.html", {
        "product": product,
        "categories": categories,
    })


@staff_required
def categories_list(request):
    cats = Category.objects.all().order_by("order", "name")
    return render(request, "dashboard/categories_list.html", {"categories": cats})


@staff_required
def orders_list(request):
    orders = Order.objects.select_related("customer").all().order_by("-created")[:200]
    return render(request, "dashboard/orders_list.html", {"orders": orders})








@staff_required
def orders_list(request):
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    paid = (request.GET.get("paid") or "").strip()

    qs = Order.objects.select_related("customer").all().order_by("-created")

    if q:
        qs = qs.filter(
            Q(id__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q)
        )

    if status:
        qs = qs.filter(status=status)

    if paid == "1":
        qs = qs.filter(is_paid=True)
    elif paid == "0":
        qs = qs.filter(is_paid=False)

    orders = qs[:300]  # чтобы не грузить админку сильно
    return render(request, "dashboard/orders_list.html", {
        "orders": orders,
        "q": q,
        "status": status,
        "paid": paid,
        "status_choices": Order.ORDER_STATUS_CHOICES,
    })


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("customer").prefetch_related("items__product"),
        pk=pk
    )
    return render(request, "dashboard/order_detail.html", {
        "order": order,
        "status_choices": Order.ORDER_STATUS_CHOICES,
    })


@staff_required
@require_POST
def order_set_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    new_status = (request.POST.get("status") or "").strip()

    allowed = {s for s, _ in Order.ORDER_STATUS_CHOICES}
    if new_status not in allowed:
        return JsonResponse({"ok": False, "message": "Некорректный статус"}, status=400)

    order.status = new_status
    order.save(update_fields=["status", "updated"])
    return JsonResponse({"ok": True, "status": order.status})


@staff_required
@require_POST
def order_toggle_paid(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order.is_paid = not order.is_paid
    order.save(update_fields=["is_paid", "updated"])
    return JsonResponse({"ok": True, "is_paid": order.is_paid})    





def _serialize_message(m: SupportMessage):
    return {
        "id": m.id,
        "created": m.created.strftime("%d.%m.%Y %H:%M"),
        "is_from_admin": bool(m.is_from_admin),
        "text": m.text or "",
        "has_file": bool(getattr(m, "attachment", None)),
        "file_url": m.attachment.url if getattr(m, "attachment", None) else "",
        "file_name": getattr(m, "attachment_name", "") or "",
    }


@staff_required
def support_chats(request):
    q = (request.GET.get("q") or "").strip()
    only_unread = (request.GET.get("unread") or "").strip()  # "1" или ""

    qs = SupportChat.objects.all().order_by("-updated_at" if hasattr(SupportChat, "updated_at") else "-id")

    # поиск по id / пользователю / телефону / последнему сообщению (если есть поля)
    if q:
        qs = qs.filter(
            Q(id__icontains=q) |
            Q(user__username__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q)
        )

    # посчитаем непрочитанные сообщения от пользователя
    qs = qs.annotate(
        unread_cnt=Count("messages", filter=Q(messages__is_from_admin=False, messages__is_read_by_admin=False))
        if hasattr(SupportMessage, "is_read_by_admin")
        else Count("messages", filter=Q(messages__is_from_admin=False))
    )

    if only_unread == "1" and hasattr(SupportMessage, "is_read_by_admin"):
        qs = qs.filter(unread_cnt__gt=0)

    chats = qs[:300]

    return render(request, "dashboard/support_chats.html", {
        "chats": chats,
        "q": q,
        "only_unread": only_unread,
    })


@staff_required
def support_chat_detail(request, chat_id):
    chat = get_object_or_404(SupportChat, id=chat_id)

    # пометим все сообщения пользователя как прочитанные админом
    if hasattr(SupportMessage, "is_read_by_admin"):
        SupportMessage.objects.filter(chat=chat, is_from_admin=False, is_read_by_admin=False).update(is_read_by_admin=True)

    # последние 60 сообщений
    messages = chat.messages.order_by("-created")[:200]
    messages = list(messages)[::-1]

    return render(request, "dashboard/support_chat_detail.html", {
        "chat": chat,
        "messages": messages,
        
    })


@staff_required
@require_POST
def support_send_message(request, chat_id):
    chat = get_object_or_404(SupportChat, id=chat_id)

    text = (request.POST.get("text") or "").strip()
    file = request.FILES.get("file")

    if not text and not file:
        return JsonResponse({"ok": False, "message": "Пустое сообщение"}, status=400)

    msg = SupportMessage.objects.create(
        chat=chat,
        text=text,
        is_from_admin=True,
        created=timezone.now(),
    )

    # если у тебя поля вложений называются иначе — замени тут
    if file:
        if hasattr(msg, "attachment"):
            msg.attachment = file
        if hasattr(msg, "attachment_name"):
            msg.attachment_name = file.name or ""
        if hasattr(msg, "attachment_mime"):
            msg.attachment_mime = getattr(file, "content_type", "") or ""
        msg.save()

    # если у чата есть updated_at — обновим
    if hasattr(chat, "updated_at"):
        chat.updated_at = timezone.now()
        chat.save(update_fields=["updated_at"])

    return JsonResponse({"ok": True, "message": _serialize_message(msg)})


@staff_required
@require_GET
def support_messages(request, chat_id):
    chat = get_object_or_404(SupportChat, id=chat_id)
    after_id = int(request.GET.get("after_id", "0") or "0")

    qs = chat.messages.order_by("created")
    if after_id > 0:
        qs = qs.filter(id__gt=after_id)

    msgs = list(qs[:200])

    # пометим новые пользовательские как прочитанные админом
    if hasattr(SupportMessage, "is_read_by_admin"):
        SupportMessage.objects.filter(chat=chat, id__in=[m.id for m in msgs], is_from_admin=False, is_read_by_admin=False)\
            .update(is_read_by_admin=True)

    return JsonResponse({
        "ok": True,
        "messages": [_serialize_message(m) for m in msgs],
        "last_id": msgs[-1].id if msgs else after_id,
    })


    


@staff_member_required
def products_list(request):
    q = (request.GET.get("q") or "").strip()
    products = Product.objects.select_related("category").order_by("-id")
    if q:
        products = products.filter(name__icontains=q)

    return render(request, "dashboard/products_list.html", {
        "products": products,
        "q": q,
        "title": "Товары",
    })

@staff_member_required
def product_create(request):
    product = Product()

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        formset = ProductImageFormSet(request.POST, request.FILES, instance=product)

        if form.is_valid() and formset.is_valid():
            product = form.save()
            formset.instance = product
            formset.save()

            messages.success(request, "Товар создан ✅")
            return redirect("dashboard:products_list")
    else:
        form = ProductForm(instance=product)
        formset = ProductImageFormSet(instance=product)

    return render(request, "dashboard/product_form.html", {
        "form": form,
        "formset": formset,
        "title": "Добавить товар",
    })


@staff_member_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        formset = ProductImageFormSet(request.POST, request.FILES, instance=product)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()

            messages.success(request, "Товар сохранён ✅")
            return redirect("dashboard:products_list")
    else:
        form = ProductForm(instance=product)
        formset = ProductImageFormSet(instance=product)

    return render(request, "dashboard/product_form.html", {
        "form": form,
        "formset": formset,
        "title": f"Редактировать: {product.name}",
        "product": product,
    })




def categories_list(request):
    categories = Category.objects.all().order_by("id")
    return render(request, "dashboard/categories_list.html", {"categories": categories})

def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("dashboard:categories_list")
    else:
        form = CategoryForm()

    return render(request, "dashboard/category_form.html", {
        "form": form,
        "title": "Добавить категорию",
        "btn_text": "Создать",
    })

def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect("dashboard:categories_list")
    else:
        form = CategoryForm(instance=category)

    return render(request, "dashboard/category_form.html", {
        "form": form,
        "title": "Редактировать категорию",
        "btn_text": "Сохранить",
    })

def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == "POST":
        category.delete()
        return redirect("dashboard:categories_list")

    return render(request, "dashboard/category_confirm_delete.html", {"category": category})




def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        product.delete()
        messages.success(request, "Товар удалён.")
        return redirect("dashboard:products_list")

    return render(request, "dashboard/product_confirm_delete.html", {"product": product})


def promocodes_list(request):
    q = (request.GET.get("q") or "").strip()

    promocodes = PromoCode.objects.all().order_by("-id")

    if q:
        promocodes = promocodes.filter(
            Q(code__icontains=q)
        )

    return render(request, "dashboard/promocodes_list.html", {
        "promocodes": promocodes,
        "q": q,
    })



def promocode_create(request):
    if request.method == "POST":
        form = PromoCodeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Промокод создан ✅")
            return redirect("dashboard:promocodes_list")
    else:
        form = PromoCodeForm()

    return render(request, "dashboard/promocode_form.html", {
        "form": form,
        "title": "Создать промокод",
        "submit_text": "Создать",
    })




def promocode_edit(request, pk):
    promocode = get_object_or_404(PromoCode, pk=pk)

    if request.method == "POST":
        form = PromoCodeForm(request.POST, instance=promocode)
        if form.is_valid():
            form.save()
            messages.success(request, "Промокод сохранён ✅")
            return redirect("dashboard:promocodes_list")
    else:
        form = PromoCodeForm(instance=promocode)

    return render(request, "dashboard/promocode_form.html", {
        "form": form,
        "title": f"Редактировать промокод {promocode.code}",
        "submit_text": "Сохранить",
    })



def promocode_delete(request, pk):
    promocode = get_object_or_404(PromoCode, pk=pk)

    if request.method == "POST":
        promocode.delete()
        messages.success(request, "Промокод удалён.")
        return redirect("dashboard:promocodes_list")

    return render(request, "dashboard/promocode_confirm_delete.html", {
        "promocode": promocode
    })