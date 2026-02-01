from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import SupportChat, SupportMessage
from django.views.decorators.http import require_GET
from django.contrib.admin.views.decorators import staff_member_required
import json
import time

@login_required
def support_chat_view(request):
    chat, _ = SupportChat.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if text:
            message = SupportMessage.objects.create(
                chat=chat,
                text=text,
                is_from_admin=False
            )
        
        # Если это AJAX запрос - возвращаем JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'ok',
                'message_id': message.id if text else None
            })
        
        # Если обычный POST - редирект (для совместимости)
        return redirect('support_chat')
    
    messages = chat.messages.order_by("created")
    return render(request, "support/chat.html", {
        "messages": messages,
        "chat": chat
    })

# support/views.py
@login_required
@require_GET
def get_new_messages(request):
    """API для получения новых сообщений"""
    chat, _ = SupportChat.objects.get_or_create(user=request.user)
    
    # Получаем ID последнего сообщения
    last_id = request.GET.get('last_id', 0)
    try:
        last_id = int(last_id)
    except:
        last_id = 0
    
    # Получаем новые сообщения (созданные ПОСЛЕ last_id)
    new_messages = chat.messages.filter(id__gt=last_id).order_by('created')
    
    messages_data = []
    for msg in new_messages:
        messages_data.append({
            'id': msg.id,
            'text': msg.text,
            'is_from_admin': msg.is_from_admin,
            'created': msg.created.isoformat() if msg.created else None,
            'time': msg.created.strftime('%H:%M') if msg.created else ''
        })
    
    # Определяем новый last_id
    new_last_id = last_id
    if new_messages.exists():
        new_last_id = new_messages.last().id
    
    return JsonResponse({
        'status': 'ok',
        'messages': messages_data,
        'last_id': new_last_id,
        'has_new': len(messages_data) > 0
    })
# =========== АДМИНСКИЕ ФУНКЦИИ ===========

@staff_member_required
def admin_chat_list(request):
    """Список всех чатов для админа (простая версия)"""
    chats = SupportChat.objects.all().order_by('-created')
    
    # Добавляем информацию о каждом чате
    for chat in chats:
        # Последнее сообщение
        last_message = chat.messages.order_by('-created').first()
        chat.last_message = last_message.text[:50] + '...' if last_message else 'Нет сообщений'
        chat.last_message_time = last_message.created if last_message else None
        
        # Количество непрочитанных (от клиента)
        chat.unread_count = chat.messages.filter(is_from_admin=False).count()
        # Общее количество сообщений
        chat.total_count = chat.messages.count()
    
    return render(request, 'support/admin_chat_list.html', {
        'chats': chats
    })

@staff_member_required
def admin_chat_detail(request, chat_id):
    """Админский чат"""
    chat = get_object_or_404(SupportChat, id=chat_id)
    
    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if text:
            message = SupportMessage.objects.create(
                chat=chat,
                text=text,
                is_from_admin=True
            )
        
        # Если AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'ok',
                'message_id': message.id if text else None
            })
        
        return redirect('admin_chat_detail', chat_id=chat_id)
    
    messages = chat.messages.order_by("created")
    return render(request, 'support/admin_chat_detail.html', {
        'chat': chat,
        'messages': messages
    })

@staff_member_required
def admin_send_message(request, chat_id):
    """API для отправки сообщения от админа (AJAX)"""
    if request.method == "POST":
        chat = get_object_or_404(SupportChat, id=chat_id)
        
        # Получаем текст из разных форматов запросов
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                text = data.get('text', '').strip()
            except:
                text = ''
        else:
            text = request.POST.get('text', '').strip()
        
        if text:
            message = SupportMessage.objects.create(
                chat=chat,
                text=text,
                is_from_admin=True
            )
            
            return JsonResponse({
                'status': 'ok',
                'message_id': message.id,
                'text': text,
                'created': message.created.isoformat() if message.created else None
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@require_GET
def get_chat_messages_api(request, chat_id=None):
    """Универсальный API для получения новых сообщений"""
    
    # Определяем, чей это чат
    if chat_id:
        # Админ запрашивает конкретный чат
        chat = get_object_or_404(SupportChat, id=chat_id)
    else:
        # Клиент запрашивает свой чат
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=401)
        chat, _ = SupportChat.objects.get_or_create(user=request.user)
    
    last_id = request.GET.get('last_id', 0)
    try:
        last_id = int(last_id)
    except:
        last_id = 0
    
    # Long polling: ждем новые сообщения
    if request.GET.get('wait') == 'true':
        timeout = 30  # максимум 30 секунд
        check_interval = 1  # проверять каждую секунду
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Проверяем новые сообщения
            new_messages = chat.messages.filter(id__gt=last_id).order_by('created')
            if new_messages.exists():
                break
            time.sleep(check_interval)
    
    # Получаем ВСЕ новые сообщения
    new_messages = chat.messages.filter(id__gt=last_id).order_by('created')
    
    messages_data = []
    for msg in new_messages:
        messages_data.append({
            'id': msg.id,
            'text': msg.text,
            'is_from_admin': msg.is_from_admin,
            'created': msg.created.isoformat() if msg.created else None,
            'time': msg.created.strftime('%H:%M') if msg.created else ''
        })
    
    new_last_id = last_id
    if new_messages.exists():
        new_last_id = new_messages.last().id
    
    return JsonResponse({
        'status': 'ok',
        'messages': messages_data,
        'last_id': new_last_id,
        'chat_id': chat.id,
        'user': chat.user.username if chat.user else 'Аноним'
    })


    










