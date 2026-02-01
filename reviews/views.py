from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from catalog.models import Product
from orders.models import OrderItem
from .forms import ReviewForm
from .models import Review


def can_user_review_product(user, product) -> bool:
    return OrderItem.objects.filter(
        product=product,
        order__customer=user,
        order__is_paid=True,
        order__status="delivered",
    ).exists()


@login_required
def review_create_or_update(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug)

    # ✅ Проверка покупки
    if not can_user_review_product(request.user, product):
        messages.error(request, "Оставить отзыв могут только покупатели товара (после доставки).")
        return redirect(reverse("catalog:product_detail", kwargs={"slug": product.slug}))

    # ✅ 1 отзыв на 1 товар от 1 юзера (у тебя unique_together)
    review, _ = Review.objects.get_or_create(
        product=product,
        user=request.user,
        defaults={"rating": 5, "text": ""}
    )

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Спасибо! Отзыв сохранён.")
        else:
            messages.error(request, "Проверьте заполнение формы.")
    return redirect(reverse("catalog:product_detail", kwargs={"slug": product.slug}))
