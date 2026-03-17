
from django.contrib import admin
from .models import Product, ProductImage, Category

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'order')
    list_filter = ('parent',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Количество товаров'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "stock", "is_active", "category", "on_main_page")
    list_filter = ("is_active", "category", "on_main_page")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("stock", "is_active", "on_main_page")  # редактирование прямо в списке
    list_per_page = 50
    inlines = [ProductImageInline]

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image', 'is_main')
 


