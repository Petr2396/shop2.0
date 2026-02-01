from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import SupportChat, SupportMessage


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0
    fields = ('created', 'text', 'is_from_admin')
    readonly_fields = ('created', 'text', 'is_from_admin')  # Сделаем все поля только для чтения
    ordering = ('-created',)
    
    # Запрещаем любые изменения через inline
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SupportChat)
class SupportChatAdmin(admin.ModelAdmin):
    list_display = ("id", "simple_user_info", "get_message_count", "get_last_message", "is_closed", "simple_chat_link")
    list_filter = ("is_closed", "created")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created",)
    inlines = [SupportMessageInline]
    fields = ('user', 'created', 'is_closed')
    
    # Опционально: запрещаем создавать/удалять чаты в админке
    def has_add_permission(self, request):
        return False  # Чаты создаются автоматически, не нужно создавать вручную
    
    def has_delete_permission(self, request, obj=None):
        return False  # Лучше не удалять чаты
    
    def simple_user_info(self, obj):
        """Простая информация о пользователе"""
        if obj.user:
            return f"{obj.user.username} ({obj.user.email or 'нет email'})"
        return "Аноним"
    simple_user_info.short_description = 'Пользователь'
    
    def get_message_count(self, obj):
        """Количество сообщений"""
        return obj.messages.count()
    get_message_count.short_description = 'Сообщений'
    
    def get_last_message(self, obj):
        """Последнее сообщение"""
        last = obj.messages.order_by('-created').first()
        if last:
            sender = "👑" if last.is_from_admin else "👤"
            return f"{sender} {last.text[:50]}{'...' if len(last.text) > 50 else ''}"
        return "Нет сообщений"
    get_last_message.short_description = 'Последнее сообщение'
    
    def simple_chat_link(self, obj):
        """Простая ссылка на чат"""
        try:
            chat_url = reverse('admin_chat_detail', args=[obj.id])
            return format_html('<a href="{}" style="background: #007bff; color: white; padding: 3px 8px; border-radius: 3px; text-decoration: none;">📨 Чат</a>', chat_url)
        except:
            return "—"
    simple_chat_link.short_description = 'Действия'


# ВАЖНО: либо закомментируй эту модель, либо сделай ее read-only
# Вариант А: Закомментировать вообще (рекомендуется)
# @admin.register(SupportMessage)
# class SupportMessageAdmin(admin.ModelAdmin):
#     ...

# Вариант Б: Сделать полностью read-only



