from django.urls import path
from . import views


app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),
    path('create/', views.order_create, name='order_create'),
    path("success/", views.order_success, name="order_success"),
    path("my-orders/", views.my_orders, name="my_orders"),
    path("cancel/<int:order_id>/", views.cancel_order, name="cancel_order"),
    path('cart/apply-promo/', views.apply_promo_code, name='apply_promo'),
    path('cart/remove-promo/', views.remove_promo_code, name='remove_promo'),
    path("return/<int:order_id>/", views.return_request, name="return_request"),
    path("my-returns/", views.my_returns, name="my_returns"),
    path("confirm/", views.confirm_order, name="confirm_order"),


]
