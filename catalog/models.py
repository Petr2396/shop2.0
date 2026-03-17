from django.db import models
from django.utils.text import slugify
from django.urls import reverse

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории")
    slug = models.SlugField(max_length=100, unique=True, blank=True, verbose_name="URL")
    description = models.TextField(blank=True, verbose_name="Описание")
    icon = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Иконка",
        help_text="Например: 🕯️, 🌿, 🎁, ⛪, 🏺"
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок сортировки")

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Родительская категория"
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['order', 'name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="Категория"
    )
    
    on_main_page = models.BooleanField(default=False, verbose_name="Показывать на главной")
    
    # ✅ ОСТАТКИ
    stock = models.PositiveIntegerField(default=0, verbose_name="Остаток")
    
    # ✅ Ручное "в продаже/не в продаже" (на всякий случай)
    is_active = models.BooleanField(default=True, verbose_name="В продаже")
    
    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        
        # можно автоматически выключать при нуле (не обязательно, но удобно)
        if self.stock <= 0:
            self.stock = 0
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('catalog:product_detail', args=[self.slug])
    
    @property
    def available(self):
        return self.is_active and self.stock > 0


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    is_main = models.BooleanField(default=False)


    class Meta:
        verbose_name = "Фото товаров"
        verbose_name_plural = "Фото товаров"

    def __str__(self):
        return f"{self.product.name} - {self.image.name}"