# shop/admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from orders.models import Order
from catalog.models import Product, Category
from django.db.models import Count, Sum, Q
from datetime import timedelta

class ShopAdminSite(admin.AdminSite):
    site_header = "🔥 Огонь Жизни - Админка"
    site_title = "Панель управления"
    index_title = "📊 Статистика и управление"
    
    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Статистика
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Заказы
        orders_today = Order.objects.filter(created__date=today)
        orders_week = Order.objects.filter(created__gte=week_ago)
        orders_month = Order.objects.filter(created__gte=month_ago)
        
        # Товары - ИСПРАВЛЕННАЯ ЧАСТЬ
        # Проверяем есть ли поле stock в модели Product
        product_fields = [f.name for f in Product._meta.get_fields()]
        
        if 'stock' in product_fields:
            # Если есть поле stock
            low_stock = Product.objects.filter(stock__lt=10, stock__gt=0)
            out_of_stock = Product.objects.filter(stock=0)
        else:
            # Если нет поля stock, используем available
            out_of_stock = Product.objects.filter(available=False)
            low_stock = Product.objects.none()  # пустой queryset
            
        # Выручка
        revenue_today = orders_today.filter(is_paid=True).aggregate(
            total=Sum('total_with_discount')
        )['total'] or 0
        
        revenue_month = orders_month.filter(is_paid=True).aggregate(
            total=Sum('total_with_discount')
        )['total'] or 0
        
        extra_context.update({
            'today': today,
            'orders_today_count': orders_today.count(),
            'orders_today_paid': orders_today.filter(is_paid=True).count(),
            'revenue_today': revenue_today,
            'revenue_month': revenue_month,
            'low_stock_count': low_stock.count(),
            'out_of_stock_count': out_of_stock.count(),
            'unpaid_orders': Order.objects.filter(is_paid=False).count(),
            'recent_orders': Order.objects.all().order_by('-created')[:10],
            'low_stock_products': low_stock[:5] if 'stock' in product_fields else [],
            'out_of_stock_products': out_of_stock[:5],
        })
        
        return super().index(request, extra_context)

# Создаем кастомную админку
admin_site = ShopAdminSite(name='admin')

# Регистрируем стандартные модели
from django.contrib.auth.models import User, Group
admin_site.register(User)
admin_site.register(Group)