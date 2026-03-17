from decimal import Decimal
from django.utils import timezone
from catalog.models import Product
from .models import PromoCode


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get("cart")
        if not cart:
            cart = self.session["cart"] = {}
        self.cart = cart
        self.promo_code = self.session.get("promo_code")

    def add(self, product, quantity=1):
        product_id = str(product.id)
        quantity = int(quantity)

        if not getattr(product, "is_active", True) or getattr(product, "stock", 0) <= 0:
            return False, "Товара нет в наличии"

        if product_id not in self.cart:
            self.cart[product_id] = {
                "quantity": 0,
                "price": str(product.price),
            }

        new_qty = self.cart[product_id]["quantity"] + quantity

        if getattr(product, "stock", None) is not None and new_qty > int(product.stock):
            self.cart[product_id]["quantity"] = int(product.stock)
            self.save()
            return False, f"Доступно только {product.stock} шт."

        self.cart[product_id]["quantity"] = new_qty
        self.save()
        return True, "Добавлено в корзину"

    def update(self, product, quantity):
        product_id = str(product.id)

        if product_id not in self.cart:
            return False, "Товара нет в корзине"

        if not getattr(product, "is_active", True) or getattr(product, "stock", 0) <= 0:
            del self.cart[product_id]
            self.save()
            return False, "Товара больше нет в наличии"

        quantity = int(quantity)

        if quantity < 1:
            del self.cart[product_id]
            self.save()
            return True, "Удалено"

        if getattr(product, "stock", None) is not None and quantity > int(product.stock):
            self.cart[product_id]["quantity"] = int(product.stock)
            self.save()
            return False, f"Доступно только {product.stock} шт."

        self.cart[product_id]["quantity"] = quantity
        self.save()
        return True, "Количество обновлено"

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def get_item_total_price(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            price = Decimal(str(self.cart[product_id]["price"]))
            quantity = int(self.cart[product_id]["quantity"])
            return price * quantity
        return Decimal("0")

    def get_total_price(self):
        total = Decimal("0")
        for item in self.cart.values():
            price = Decimal(str(item["price"]))
            quantity = int(item["quantity"])
            total += price * quantity
        return total.quantize(Decimal("0.01"))

    # =========================
    # ПРОМОКОДЫ
    # =========================

    def apply_promo_code(self, code):
        code = (code or "").strip()

        if not code:
            return False, "Введите промокод"

        promo = PromoCode.objects.filter(code__iexact=code).first()

        if not promo:
            self.remove_promo_code()
            return False, "Промокод не найден"

        now = timezone.now()

        if not promo.active:
            self.remove_promo_code()
            return False, "Промокод отключён"

        if promo.used_count >= promo.max_usage:
            self.remove_promo_code()
            return False, "Лимит использований этого промокода исчерпан"

        if promo.valid_from > now:
            self.remove_promo_code()
            return False, "Промокод ещё не начал действовать"

        if promo.valid_to < now:
            self.remove_promo_code()
            return False, "Срок действия промокода истёк"

        promo_data = {
            "code": promo.code,
            "discount": promo.discount,
        }

        self.session["promo_code"] = promo_data
        self.promo_code = promo_data
        self.save()

        return True, promo_data

    def set_promo_code(self, promo_data):
        self.session["promo_code"] = promo_data
        self.promo_code = promo_data
        self.save()

    def remove_promo_code(self):
        if "promo_code" in self.session:
            del self.session["promo_code"]
        self.promo_code = None
        self.save()

    def get_discount(self):
        if self.promo_code:
            return int(self.promo_code.get("discount", 0) or 0)
        return 0

    def get_total_with_discount(self):
        total = self.get_total_price()
        discount = self.get_discount()

        if discount:
            discounted_total = total * (Decimal("100") - Decimal(str(discount))) / Decimal("100")
            return discounted_total.quantize(Decimal("0.01"))

        return total

    def clean(self):
        keys = list(self.cart.keys())

        bad_keys = [k for k in keys if not k or not str(k).isdigit()]
        for k in bad_keys:
            self.cart.pop(k, None)

        keys = [k for k in self.cart.keys() if str(k).isdigit()]
        if keys:
            existing_ids = set(Product.objects.filter(id__in=keys).values_list("id", flat=True))
            existing_ids = set(str(x) for x in existing_ids)
            missing = [k for k in keys if k not in existing_ids]
            for k in missing:
                self.cart.pop(k, None)

        self.save()

    def __iter__(self):
        self.clean()
        product_ids = list(self.cart.keys())
        products = Product.objects.filter(id__in=product_ids)
        products_map = {str(p.id): p for p in products}

        for pid, item in self.cart.items():
            product = products_map.get(pid)
            if not product:
                continue

            item = item.copy()
            item["product"] = product
            item["price"] = Decimal(str(item.get("price", 0)))
            item["total_price"] = item["price"] * int(item.get("quantity", 0))
            yield item

    def __len__(self):
        return sum(int(item["quantity"]) for item in self.cart.values())

    def save(self):
        self.session.modified = True

    def clear(self):
        self.session["cart"] = {}
        if "promo_code" in self.session:
            del self.session["promo_code"]
        self.promo_code = None
        self.save()