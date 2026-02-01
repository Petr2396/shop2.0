from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Avg, Count
from django.http import JsonResponse
from django.urls import reverse
from orders.models import OrderItem
from .models import Product, Category
from reviews.forms import ReviewForm
from django.views.decorators.http import require_GET


def product_list(request):
    products = Product.objects.all()

    category_slug = request.GET.get("category")
    query = request.GET.get("q")

    # Фильтрация по категории
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    else:
        category = None

    # Поиск
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    # ✅ Добавляем рейтинги (среднее и кол-во отзывов) к каждому товару
    products = products.annotate(
        rating_avg=Avg("reviews__rating"),
        rating_count=Count("reviews")
    )

    # Категории для меню
    categories = Category.objects.all()

    return render(request, "catalog/product_list.html", {
        "products": products,
        "query": query,
        "categories": categories,
        "current_category": category
    })


def product_detail(request, slug):
    # ✅ Берём товар + сразу считаем рейтинг
    product = get_object_or_404(
        Product.objects.annotate(
            rating_avg=Avg("reviews__rating"),
            rating_count=Count("reviews")
        ),
        slug=slug
    )

    images = product.images.all()

    # ✅ Список отзывов
    reviews = product.reviews.select_related("user").all()

    # ✅ Форма отзыва
    form = ReviewForm()

    # ✅ Может ли пользователь оставить отзыв (только если покупал, оплатил и доставлено)
    can_review = False
    if request.user.is_authenticated:
        can_review = OrderItem.objects.filter(
            product=product,
            order__customer=request.user,
            order__is_paid=True,
            order__status="delivered",
        ).exists()

    return render(request, "catalog/product_detail.html", {
        "product": product,
        "images": images,
        "reviews": reviews,
        "form": form,
        "can_review": can_review,
    })



def product_search(request):
    q = request.GET.get("q", "").strip()
    results = []

    if q:
        qs = Product.objects.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )[:10]

        for p in qs:
            url = ""
            try:
                url = reverse("catalog:product_detail", args=[p.slug])
            except Exception:
                url = ""

            image = ""
            try:
                if hasattr(p, "images") and p.images.exists():
                    image = p.images.first().image.url
            except Exception:
                image = ""

            results.append({
                "id": p.id,
                "name": p.name,
                "price": str(p.price),
                "url": url,
                "image": image,
            })

    return JsonResponse({"results": results})


@require_GET
def product_quick_view(request, slug):
    # берем товар + рейтинг (у тебя уже reviews связаны)
    product = get_object_or_404(
        Product.objects.annotate(
            rating_avg=Avg("reviews__rating"),
            rating_count=Count("reviews")
        ),
        slug=slug
    )

    image = ""
    try:
        if product.images.first():
            image = product.images.first().image.url
    except Exception:
        image = ""

    return JsonResponse({
        "id": product.id,
        "name": product.name,
        "price": str(product.price),
        "description": product.description or "",
        "image": image,
        "detail_url": reverse("catalog:product_detail", args=[product.slug]),
        "cart_url": reverse("orders:cart_add", args=[product.id]),
        "rating_avg": float(product.rating_avg) if product.rating_avg is not None else None,
        "rating_count": int(product.rating_count) if product.rating_count else 0,
        "category": product.category.name if product.category else "",
    })
