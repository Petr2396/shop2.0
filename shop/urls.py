from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", admin.site.urls),

    path("catalog/", include(("catalog.urls", "catalog"), namespace="catalog")),
    path("orders/", include(("orders.urls", "orders"), namespace="orders")),
    path("payments/", include(("payments.urls", "payments"), namespace="payments")),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("support/", include("support.urls")),
    path("reviews/", include(("reviews.urls", "reviews"), namespace="reviews")),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)