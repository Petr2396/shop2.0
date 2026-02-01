from django.urls import path
from .views import support_chat_view
from . import views
from django.contrib.auth.decorators import login_required



urlpatterns = [
    path('chat/', views.support_chat_view, name='support_chat'),
    path('api/messages/', views.get_new_messages, name='get_messages'),
    path('api/chat/messages/', views.get_chat_messages_api, name='chat_messages_api'),
     
    path('admin/chats/', views.admin_chat_list, name='admin_chat_list'),
    path('admin/chat/<int:chat_id>/', views.admin_chat_detail, name='admin_chat_detail'),
    path('admin/api/chat/<int:chat_id>/messages/', views.get_chat_messages_api, name='admin_messages_api'),
]
