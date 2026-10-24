# SPDX-License-Identifier: EUPL-1.2
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.tenants.urlutils import treverse

from . import notices
from .models import (
    CATEGORY_BASIS,
    CATEGORY_ICON,
    CHANNELS,
    INFO,
    Category,
    Notice,
    Notification,
    PushSubscription,
)


def _categories(selected):
    return [
        {
            "value": c.value,
            "label": c.label,
            "icon": CATEGORY_ICON[c],
            "current": c.value == selected,
        }
        for c in Category
    ]


@login_required
def list_view(request):
    selected = request.GET.get("categoria", "")
    if selected not in Category.values:
        selected = ""
    qs = Notification.objects.filter(user=request.user, municipality=request.tenant)
    if selected:
        qs = qs.filter(category=selected)
    # Taboleiro: avisos xerais xa publicados. Velos aquí non é un envío, así que non precisa
    # consentimento (é como o taboleiro de anuncios do concello).
    board = Notice.objects.filter(
        municipality=request.tenant, audience=Notice.Audience.ALL, sent_at__isnull=False
    ).exclude(deliveries__user=request.user)
    if selected:
        board = board.filter(category=selected)
    return render(
        request,
        "notifications/list.html",
        {
            "notifications": qs[:100],
            "board": board.order_by("-sent_at")[:20],
            "categories": _categories(selected),
            "selected": selected,
            "has_consent": notices.has_consent(request.user, request.tenant),
            "telegram_channel": request.tenant.telegram_channel,
            "nav": "notifications",
        },
    )


@login_required
def preferences(request):
    pref = notices.preference(request.user, request.tenant)
    if request.method == "POST":
        if request.POST.get("consent") == "1":
            pref.comms_consent_at = pref.comms_consent_at or timezone.now()
        else:
            pref.comms_consent_at = None
        pref.matrix = {
            c.value: [
                ch
                for ch in CHANNELS
                if request.POST.get(f"{c.value}:{ch}") == "1"
                or (ch == "app" and CATEGORY_BASIS[c] != INFO)
            ]
            for c in Category
        }
        pref.save()
        messages.success(request, _("Preferencias gardadas."))
        return redirect(treverse(request.tenant, "notifications:preferences"))
    rows = [
        {
            "value": c.value,
            "label": c.label,
            "service": CATEGORY_BASIS[c] != INFO,
            "channels": [{"name": ch, "on": ch in pref.channels_for(c.value)} for ch in CHANNELS],
        }
        for c in Category
    ]
    code = request.session.pop("telegram_code", None)
    return render(
        request,
        "notifications/preferences.html",
        {
            "pref": pref,
            "rows": rows,
            "channels": CHANNELS,
            "telegram_code": code,
            "telegram_url": notices.bot_link_url(code) if code else None,
            "telegram_channel": request.tenant.telegram_channel,
            "nav": "notifications",
        },
    )


@login_required
@require_POST
def telegram_link(request):
    request.session["telegram_code"] = notices.new_link_code(request.user)
    return redirect(treverse(request.tenant, "notifications:preferences") + "#telegram")


@login_required
@require_POST
def telegram_unlink(request):
    notices.unlink(request.user)
    messages.success(request, _("Telegram desvinculado."))
    return redirect(treverse(request.tenant, "notifications:preferences") + "#telegram")


@csrf_exempt
@require_POST
def telegram_webhook(request, secret):
    """Webhook do bot (Bot API). Só existe se hai EIRA_TELEGRAM_WEBHOOK_SECRET e coincide."""
    expected = getattr(settings, "EIRA_TELEGRAM_WEBHOOK_SECRET", "")
    if not expected or secret != expected:
        raise Http404
    try:
        update = json.loads(request.body)
        msg = update.get("message") or {}
        chat_id, text = msg["chat"]["id"], msg.get("text", "")
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"ok": True})  # Telegram non debe reintentar actualizacións raras
    notices.handle_bot_message(chat_id, text)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(
        user=request.user, municipality=request.tenant, read_at__isnull=True
    ).update(read_at=timezone.now())
    if request.headers.get("HX-Request"):
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    return redirect(treverse(request.tenant, "notifications:list"))


@login_required
@require_POST
def subscribe_push(request):
    """Rexistra unha subscrición Web Push (RFC 8030). O envío real vai detrás do adaptador."""
    try:
        data = json.loads(request.body)
        PushSubscription.objects.update_or_create(
            endpoint=data["endpoint"][:500],
            defaults={"user": request.user, "keys": data.get("keys", {})},
        )
    except (ValueError, KeyError):
        return JsonResponse({"ok": False}, status=400)
    return JsonResponse({"ok": True})
