from django import template

register = template.Library()

@register.filter
def cart_total_quantity(cart_data):
    """
    Фильтр для подсчета общего количества товаров в корзине.
    cart_data - это request.session.cart
    
    Использование в шаблоне:
    {{ request.session.cart|cart_total_quantity }}
    """
    if not cart_data or not isinstance(cart_data, dict):
        return 0
    
    total = 0
    for item in cart_data.values():
        if isinstance(item, dict) and 'quantity' in item:
            # Если структура: {'quantity': X, 'price': Y, ...}
            total += item['quantity']
        elif isinstance(item, dict) and 'qty' in item:
            # Если структура: {'qty': X, ...}
            total += item['qty']
        elif isinstance(item, (int, float, str)):
            # Если просто количество
            try:
                total += int(item)
            except:
                total += 1
        else:
            # Любой другой случай
            total += 1
    
    return total

@register.filter
def cart_item_count(cart_data):
    """Количество уникальных позиций в корзине"""
    if not cart_data:
        return 0
    return len(cart_data)

# Дополнительные полезные фильтры для корзины
@register.filter
def cart_total_price(cart_data, price_field='price'):
    """Общая стоимость корзины"""
    if not cart_data:
        return 0
    
    total = 0
    for item in cart_data.values():
        if isinstance(item, dict):
            quantity = item.get('quantity', 1)
            price = item.get(price_field, 0)
            try:
                total += float(quantity) * float(price)
            except:
                pass
    
    return round(total, 2)