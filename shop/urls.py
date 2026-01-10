"""
URL configuration for shop project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path, include


urlpatterns = [
    path('', views.home, name='home'),  # Главная
    path('admin/', admin.site.urls),
    
    path('catalog/', include('catalog.urls', namespace='catalog')),  # Каталог на /catalog/
    path("orders/", include("orders.urls", namespace="orders")),

    
    
    path("payments/", include("payments.urls", namespace="payments")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)