from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils import timezone

from django.contrib.admin.sites import site as admin_site
from django.template.response import TemplateResponse


from .models import SupportChat, SupportMessage

import json
import time


# ---------- helpers ----------

def _serialize_message(msg: SupportMessage):
    local_dt = timezone.localtime(msg.created) if msg.created else None

    return {
        "id": msg.id,
        "text": msg.text or "",
        "is_from_admin": bool(msg.is_from_admin),
        "created": msg.created.isoformat() if msg.created else None,
        "time": local_dt.strftime("%H:%M") if local_dt else "",
        "attachment": msg.attachment.url if getattr(msg, "attachment", None) else None,
        "attachment_name": getattr(msg, "attachment_name", "") or "",
        "attachment_mime": getattr(msg, "attachment_mime", "") or "",
    }


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


# =========== КЛИЕНТ: чат ===========

@login_required
def support_chat_view(request):
    chat, _ = SupportChat.objects.get_or_create(user=request.user)

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        file = request.FILES.get("file")

        if not text and not file:
            return JsonResponse(
                {"status": "error", "message": "empty"},
                status=400
            )

        message = SupportMessage.objects.create(
            chat=chat,
            text=text,
            is_from_admin=False,
            attachment=file if file else None
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "status": "ok",
                "message": {
                    "id": message.id,
                    "text": message.text,
                    "is_from_admin": message.is_from_admin,
                    "time": timezone.localtime(message.created).strftime("%H:%M"),

                    "attachment": message.attachment.url if message.attachment else None,
                    "attachment_name": message.attachment.name.split("/")[-1] if message.attachment else None,
                    "attachment_mime": message.attachment.file.content_type if message.attachment else None,
                }
            })

        return redirect("support_chat")

    messages = chat.messages.order_by("created")
    return render(request, "support/chat.html", {
        "messages": messages,
        "chat": chat
    })


# =========== API: новые сообщения (клиент) ===========
@login_required
@require_GET
def get_new_messages(request):
    chat, _ = SupportChat.objects.get_or_create(user=request.user)

    last_id = request.GET.get("last_id", 0)
    try:
        last_id = int(last_id)
    except Exception:
        last_id = 0

    new_messages = chat.messages.filter(id__gt=last_id).order_by("created")

    data = [_serialize_message(m) for m in new_messages]
    new_last_id = new_messages.last().id if new_messages.exists() else last_id

    return JsonResponse({
        "status": "ok",
        "messages": data,
        "last_id": new_last_id,
        "has_new": bool(data),
    })


# =========== АДМИН: список чатов ===========

@staff_member_required
def admin_chat_list(request):
    chats = SupportChat.objects.all().order_by("-created")

    for chat in chats:
        last_message = chat.messages.order_by("-created").first()
        chat.last_message = (last_message.text[:50] + "...") if last_message and last_message.text else "Нет сообщений"
        chat.last_message_time = last_message.created if last_message else None
        chat.unread_count = chat.messages.filter(is_from_admin=False).count()
        chat.total_count = chat.messages.count()

    return render(request, "support/admin_chat_list.html", {"chats": chats})


# =========== АДМИН: чат ===========

@staff_member_required
def admin_chat_detail(request, chat_id):
    chat = get_object_or_404(SupportChat, id=chat_id)

    # ===== POST: отправка сообщения =====
    if request.method == "POST":
        text = (request.POST.get("text") or "").strip()
        file = request.FILES.get("file")

        if not text and not file:
            if _is_ajax(request):
                return JsonResponse({"status": "error", "message": "Пустое сообщение"}, status=400)
            return redirect("admin_chat_detail", chat_id=chat_id)

        msg = SupportMessage.objects.create(
            chat=chat,
            text=text,
            is_from_admin=True,
            created=timezone.now(),
        )

        if file:
            msg.attachment = file
            msg.attachment_name = file.name or ""
            msg.attachment_mime = getattr(file, "content_type", "") or ""
            msg.save(update_fields=["attachment", "attachment_name", "attachment_mime"])

        if _is_ajax(request):
            return JsonResponse({"status": "ok", "message": _serialize_message(msg)})

        return redirect("admin_chat_detail", chat_id=chat_id)

    # ===== GET: показ сообщений =====
    messages_qs = chat.messages.order_by("created")

    context = {
        **admin_site.each_context(request),   # ✅ меню/юзер/хедер и т.д. для Jazzmin/Django admin
        "chat": chat,
        "messages": messages_qs,
        "title": f"Чат #{chat.id}",
    }

    # ✅ ВАЖНО: этот шаблон должен наследоваться от admin/base_site.html
    return TemplateResponse(request, "support/admin_chat_detail.html", context)

# =========== АДМИН: API отправки (AJAX) ===========

@staff_member_required
def admin_send_message(request, chat_id):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

    chat = get_object_or_404(SupportChat, id=chat_id)

    # поддержка json/form + file
    text = ""
    if request.content_type == "application/json":
        try:
            payload = json.loads(request.body.decode("utf-8"))
            text = (payload.get("text") or "").strip()
        except Exception:
            text = ""
        file = None
    else:
        text = (request.POST.get("text") or "").strip()
        file = request.FILES.get("file")

    if not text and not file:
        return JsonResponse({"status": "error", "message": "Пустое сообщение"}, status=400)

    msg = SupportMessage.objects.create(
        chat=chat,
        text=text,
        is_from_admin=True,
        created=timezone.now(),
    )

    if file:
        msg.attachment = file
        msg.attachment_name = file.name or ""
        msg.attachment_mime = getattr(file, "content_type", "") or ""
        msg.save(update_fields=["attachment", "attachment_name", "attachment_mime"])

    return JsonResponse({"status": "ok", "message": _serialize_message(msg)})


# =========== УНИВЕРСАЛЬНЫЙ LONG-POLL API (клиент/админ) ===========

@require_GET
def get_chat_messages_api(request, chat_id=None):
    # кто запрашивает
    if chat_id:
        # админ
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)
        chat = get_object_or_404(SupportChat, id=chat_id)
    else:
        # клиент
        if not request.user.is_authenticated:
            return JsonResponse({"status": "error", "message": "Not authenticated"}, status=401)
        chat, _ = SupportChat.objects.get_or_create(user=request.user)

    last_id = request.GET.get("last_id", 0)
    try:
        last_id = int(last_id)
    except Exception:
        last_id = 0

    # long polling
    if request.GET.get("wait") == "true":
        timeout = 30
        check_interval = 1
        start_time = time.time()

        while time.time() - start_time < timeout:
            if chat.messages.filter(id__gt=last_id).exists():
                break
            time.sleep(check_interval)

    new_messages = chat.messages.filter(id__gt=last_id).order_by("created")
    data = [_serialize_message(m) for m in new_messages]
    new_last_id = new_messages.last().id if new_messages.exists() else last_id

    return JsonResponse({
        "status": "ok",
        "messages": data,
        "last_id": new_last_id,
        "chat_id": chat.id,
        "user": chat.user.username if chat.user else "Аноним",
    })










