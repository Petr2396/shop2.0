from django.db import models
from django.conf import settings
from catalog.models import Product
from django.core.validators import MinValueValidator, MaxValueValidator


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('new', 'Новый'),
        ('processing', 'В сборке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('canceled', 'Отменён'),
    ]

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    address = models.CharField(max_length=250)
    phone = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=50, choices=ORDER_STATUS_CHOICES, default='new')
    customer = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="orders", null=True, blank=True)
    
    
    yandex_pvz_id = models.CharField(max_length=120, blank=True, null=True)
    yandex_pvz_address = models.CharField(max_length=255, blank=True, null=True)
    yandex_pvz_type = models.CharField(max_length=40, blank=True, null=True)
    yandex_pvz_payment_methods = models.JSONField(blank=True, null=True)
    yandex_pvz_position = models.JSONField(blank=True, null=True)



    is_paid = models.BooleanField(default=False, verbose_name="Оплачен")
    
    payment_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="ID платежа ЮKassa"
    )

    yandex_offer_raw = models.JSONField(null=True, blank=True, verbose_name="Яндекс: оффер (сырой ответ)")
    yandex_option_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="Яндекс: выбранный вариант")
    yandex_delivery_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Яндекс: стоимость доставки")


    DELIVERY_CHOICES = [
        ('yandex', 'Яндекс Доставка'),
        ('ozon', 'Ozon Доставка'),
        ('post', 'Почта России'),
        ('cdek', 'СДЭК'),
    ]
    
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        default='courier',
        verbose_name='Способ доставки'
    )

    


    promo_code = models.CharField(max_length=255, blank=True, null=True, verbose_name="Промокод")
    discount = models.IntegerField(default=0, verbose_name="Скидка %")
    total_with_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Сумма со скидкой"
    )

    def __str__(self):
        return f"Заказ {self.id}"

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

    def get_discount_amount(self):
        if self.discount and self.discount > 0:
            total = self.get_total_cost()
            return round(total * self.discount / 100, 2)
        return 0

    def get_final_total(self):
        """Возвращает сумму к оплате"""
        # Если есть сумма со скидкой - используем её
        if self.total_with_discount is not None:
            print(f"📦 get_final_total: используем total_with_discount = {self.total_with_discount}")
            return self.total_with_discount
        
        # Иначе считаем скидку на лету
        total = self.get_total_cost()
        if self.discount and self.discount > 0:
            discount_amount = total * Decimal(self.discount) / 100
            result = total - discount_amount
            print(f"📦 get_final_total: расчет на лету: {total} - {discount_amount} = {result}")
            return result
        
        print(f"📦 get_final_total: без скидки = {total}")
        return total
    
    def has_return_request(self):
        """Проверяет, есть ли ЛЮБАЯ заявка на возврат для этого заказа"""
        return self.returns.exists()
    
    def has_active_return_request(self):
        """Проверяет, есть ли активная заявка на возврат"""
        return self.returns.filter(status__in=['pending', 'processing']).exists()
    
    def can_create_return(self):
        """Проверяет, можно ли создать возврат для этого заказа"""
        from django.utils import timezone
        
        # Если уже есть ЛЮБОЙ возврат - нельзя создать новый
        if self.has_return_request():
            return False
            
        # Возврат можно создать в течение 14 дней после доставки
        if self.status != 'delivered' or not self.is_paid:
            return False
            
        days_since_delivery = (timezone.now() - self.created).days
        return days_since_delivery <= 14


    class Meta:
        ordering = ['-created']
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="order_items", on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)


    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def get_cost(self):
        return self.price * self.quantity


class PromoCode(models.Model):
    code = models.CharField(max_length=255, unique=True, verbose_name="Промокод")
    discount = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name="Скидка в %"
    )
    active = models.BooleanField(default=True, verbose_name="Активен")
    valid_from = models.DateTimeField(verbose_name="Действует с")
    valid_to = models.DateTimeField(verbose_name="Действует до")
    max_usage = models.IntegerField(default=1, verbose_name="Максимум использований")
    used_count = models.IntegerField(default=0, verbose_name="Использовано раз")

    class Meta:
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"

    def __str__(self):
        return f"{self.code} ({self.discount}%)"

    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        return (
            self.active and
            self.used_count < self.max_usage and
            self.valid_from <= now <= self.valid_to
        )

    def apply_discount(self, amount):
        return amount * (100 - self.discount) / 100


class ReturnRequest(models.Model):
    RETURN_STATUS_CHOICES = [
        ("pending", "На рассмотрении"),
        ("approved", "Одобрен"),
        ("rejected", "Отклонён"),
    ]

    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="returns")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    items = models.ManyToManyField("orders.OrderItem", related_name="returns")
    reason = models.TextField("Причина возврата")
    photo = models.ImageField(upload_to="returns/", blank=True, null=True)
    phone = models.CharField(max_length=255)
    email = models.EmailField()
    status = models.CharField(max_length=255, choices=RETURN_STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Заявка на возврат"
        verbose_name_plural = "Заявки на возврат"

    def __str__(self):
        return f"Возврат заказа #{self.order.id} от {self.user.username} ({self.status})"
