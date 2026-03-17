from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),

    path("products/", views.products_list, name="products_list"),
    path("products/<int:pk>/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),

    path("categories/", views.categories_list, name="categories_list"),
    path("categories/create/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_update, name="category_update"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),

    path("orders/", views.orders_list, name="orders_list"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/status/", views.order_set_status, name="order_set_status"),
    path("orders/<int:pk>/paid/", views.order_toggle_paid, name="order_toggle_paid"),
    path("support/", views.support_chats, name="support_chats"),
    path("support/<int:chat_id>/", views.support_chat_detail, name="support_chat_detail"),

    # AJAX
    path("support/<int:chat_id>/send/", views.support_send_message, name="support_send_message"),
    path("support/<int:chat_id>/messages/", views.support_messages, name="support_messages"),
    path("products/", views.products_list, name="products_list"),
    path("products/new/", views.product_create, name="product_create"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),


    path("promocodes/", views.promocodes_list, name="promocodes_list"),
    path("promocodes/create/", views.promocode_create, name="promocode_create"),
    path("promocodes/<int:pk>/edit/", views.promocode_edit, name="promocode_edit"),
    path("promocodes/<int:pk>/delete/", views.promocode_delete, name="promocode_delete"),
]