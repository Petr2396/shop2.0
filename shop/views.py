from django.shortcuts import render
from django.db.models import Avg, Count
from catalog.models import Product


def home(request):
    # Товары отмеченные для показа на главной + реальный рейтинг
    featured_products = (
        Product.objects
        .filter(on_main_page=True)
        .annotate(
            rating_avg=Avg("reviews__rating"),
            rating_count=Count("reviews")
        )[:6]
    )

    # Если ни один не отмечен, показываем последние + реальный рейтинг
    if not featured_products:
        featured_products = (
            Product.objects
            .all()
            .order_by("-id")
            .annotate(
                rating_avg=Avg("reviews__rating"),
                rating_count=Count("reviews")
            )[:6]
        )

    return render(request, "home.html", {
        "featured_products": featured_products
    })
