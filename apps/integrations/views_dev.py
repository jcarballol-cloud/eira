# SPDX-License-Identifier: EUPL-1.2
"""Ferramentas de demostración (só con EIRA_DEMO_TOOLS=1): bandexa de correo, TPV e Cl@ve
simulados, simulador de pechadura e cambio rápido de perfil."""

import datetime as dt
import secrets

from django.contrib.auth import login
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.access.models import LockDevice
from apps.access.services import validate_code
from apps.accounts.models import User
from apps.tenants.prefs import THEME_KEY, write_prefs

from .demo import DEMO_PERSONAS, NEW_NEIGHBOUR
from .identity import FAKE_IDENTITIES
from .models import DevMail, FakePayment, OutboundMessage


def mailbox(request, pk=None):
    """v4: como unha bandexa real: lista (remitente, asunto, extracto, data) e vista da mensaxe."""
    from django.conf import settings

    to = request.GET.get("para", "")
    if not to and request.GET.get("min") == "1" and request.user.is_authenticated:
        to = request.user.email
    mails = DevMail.objects.all()
    if to:
        mails = mails.filter(to__iexact=to)
    current = get_object_or_404(DevMail, pk=pk) if pk else None
    if current is None and to and not request.GET.get("lista"):
        current = mails.first()  # filtrando por persoa, ábrese a última mensaxe
    return render(
        request,
        "dev/mailbox.html",
        {
            "mails": mails[:80],
            "to": to,
            "current": current,
            "sender": settings.EIRA_DEFAULT_FROM_EMAIL,
            "tool": "mail",
        },
    )


def outbox(request):
    return render(
        request,
        "dev/outbox.html",
        {
            "messages_out": OutboundMessage.objects.exclude(channel="telegram")[:100],
            "tool": "outbox",
        },
    )


def telegram(request):
    """v4: simulador de Telegram. Chats do bot persoal e canles públicas, con burbullas.
    Escribir ao bot fai o mesmo ca o webhook real (p. ex. `/start CODIGO` vincula a conta)."""
    from apps.notifications.notices import handle_bot_message
    from apps.tenants.models import Municipality

    start = request.GET.get("start", "")
    if request.method == "POST":
        chat = request.POST.get("chat") or f"sim-{secrets.randbelow(10**6):06d}"
        text = (request.POST.get("text") or "").strip()[:500]
        if text:
            OutboundMessage.objects.create(
                channel="telegram", target=chat, payload={"text": text, "from": "user"}
            )
            handle_bot_message(chat, text)
        return redirect(f"{request.path}?chat={chat}")
    msgs = OutboundMessage.objects.filter(channel="telegram")
    chats = {}
    for m in msgs.order_by("-sent_at"):
        chats.setdefault(m.target, m)
    users = {u.telegram_chat: u for u in User.objects.filter(telegram_chat__in=list(chats))}
    channels = dict(
        Municipality.objects.exclude(telegram_channel="").values_list("telegram_channel", "name")
    )
    rows = [
        {
            "id": cid,
            "last": last,
            "public": cid.startswith("@"),
            "title": (channels.get(cid) or cid)
            if cid.startswith("@")
            else (users[cid].display_name or users[cid].email if cid in users else cid),
        }
        for cid, last in chats.items()
    ]
    current = request.GET.get("chat") or ("" if start else (rows[0]["id"] if rows else ""))
    thread = list(msgs.filter(target=current).order_by("sent_at")[:200]) if current else []
    return render(
        request,
        "dev/telegram.html",
        {
            "chats": rows,
            "current": current,
            "current_row": next((r for r in rows if r["id"] == current), None),
            "thread": thread,
            "start": start,
            "tool": "telegram",
        },
    )


def tpv(request, reference):
    """Pasarela simulada tipo Redsys. Unha operación resolta xa non se pode cambiar (idempotente)."""
    from apps.bookings.payments import handle_notification

    from .registry import get_adapter

    fake = get_object_or_404(FakePayment, reference=reference)
    if fake.status != FakePayment.Status.PENDING:
        return render(request, "dev/tpv.html", {"payment": fake, "already": True})
    if request.method == "POST":
        ok = request.POST.get("result") == "ok"
        fake.status = FakePayment.Status.PAID if ok else FakePayment.Status.FAILED
        fake.save(update_fields=["status"])
        # Notificación servidor a servidor (simulada en proceso; nun TPV real é un POST á URL de notificación)
        handle_notification(get_adapter("payment").build_notification(fake, ok))
        target = fake.return_url if ok else (fake.return_url_ko or fake.return_url)
        if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
            target = "/"
        return redirect(target)
    return render(request, "dev/tpv.html", {"payment": fake})


def clave(request):
    state = request.GET.get("state") or request.POST.get("state", "")
    return render(request, "dev/clave.html", {"state": state, "identities": FAKE_IDENTITIES})


def lock_simulator(request):
    devices = LockDevice.objects.filter(kind=LockDevice.Kind.OFFLINE).select_related(
        "facility", "municipality"
    )
    result = None
    now = timezone.now().replace(second=0, microsecond=0)
    device_id = request.POST.get("device") or request.GET.get("device")
    at_raw = request.POST.get("at") or request.GET.get("at")
    at = parse_datetime(at_raw) if at_raw else None
    at = timezone.make_aware(at) if at and timezone.is_naive(at) else (at or now)
    shift = request.GET.get("shift")
    if request.method == "GET" and shift and shift.lstrip("-").isdigit():
        at = at + dt.timedelta(minutes=int(shift))
    device = devices.filter(pk=device_id).first() if device_id else None
    if device is None and request.user.is_authenticated and not at_raw:
        # Sen parámetros: o dispositivo e a hora da próxima reserva da persoa (nivel 2)
        from apps.bookings.models import Booking

        mine = (
            Booking.objects.filter(
                user=request.user,
                facility__lock__kind=LockDevice.Kind.OFFLINE,
                end__gt=timezone.now(),
            )
            .holding()
            .order_by("start")
            .select_related("facility__lock")
            .first()
        )
        if mine:
            device = mine.facility.lock
            at = max(mine.start, now)  # en curso: agora; se non, á hora de inicio
    device = device or devices.first()
    code = request.POST.get("code", "").strip()
    # v1.2 · B: estado da porta das pechaduras conectadas (nivel 3)
    connected = LockDevice.objects.filter(kind=LockDevice.Kind.CONNECTED).select_related(
        "facility", "municipality"
    )
    if request.method == "POST" and request.POST.get("action") == "door":
        door = connected.filter(pk=request.POST.get("door_device")).first()
        if door:
            value = request.POST.get("door")
            door.door_closed = {"closed": True, "open": False}.get(value)
            door.door_state_at = timezone.now()
            door.save(update_fields=["door_closed", "door_state_at"])
    if request.method == "POST" and device and request.POST.get("action") == "reset":
        device.failed_attempts, device.lockout_count, device.locked_until = 0, 0, None
        device.save(update_fields=["failed_attempts", "lockout_count", "locked_until"])
    elif request.method == "POST" and device and code:
        live = abs((at - timezone.now()).total_seconds()) < 300
        result = validate_code(device, code, at=at, record=live, lock_clock=timezone.now())
        result["live"] = live
        device.refresh_from_db()
    return render(
        request,
        "dev/lock_simulator.html",
        {
            "devices": devices,
            "device": device,
            "at": at,
            "result": result,
            "at_value": timezone.localtime(at).strftime("%Y-%m-%dT%H:%M"),
            "locked": bool(device and device.locked_until and device.locked_until > timezone.now()),
            "tool": "lock",
            "connected": connected,
        },
    )


def safe_next(request, fallback):
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return target
    return fallback


@require_POST
def login_as(request):
    email = request.POST.get("email", "")
    persona = next((p for p in DEMO_PERSONAS if p["email"] == email), None)
    if persona is None:
        raise Http404
    user = User.objects.filter(email=email).first()
    if user is None:
        raise Http404("Executa `make seed` primeiro")
    # login() baleira a sesión: o tema da demo mantense (ou cámbiase se vén do catálogo)
    theme = request.POST.get("tema") or request.session.get(THEME_KEY)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    if theme in ("light", "dark"):
        request.session[THEME_KEY] = theme
    from apps.accounts.profiles import home_url

    response = redirect(safe_next(request, home_url(user)))
    return write_prefs(response, {persona.get("prefs"): True} if persona.get("prefs") else {})


@require_POST
def theme(request):
    """v4.1: botón «Día / Noite» do simulador. Garda o tema na sesión; «system» volve á
    preferencia do sistema. Con JS respóndese 204 (o cambio xa se fixo no navegador)."""
    value = request.POST.get("tema", "")
    if value in ("light", "dark"):
        request.session[THEME_KEY] = value
    else:
        request.session.pop(THEME_KEY, None)
    if request.headers.get("X-Eira-Theme"):
        return HttpResponse(status=204)
    return redirect(safe_next(request, request.headers.get("Referer") or "/"))


def illustrations(request):
    """v4.1: catálogo das ilustracións (día, noite e estados baleiros) coa pantalla onde aparece
    cada unha e un atallo para ir a ela co perfil axeitado."""
    from django.utils.translation import gettext as _

    c = "/c/vilardeiras"
    items = [
        {
            "name": "cabecera-eira",
            "title": _("Cabeceira da app · día"),
            "where": _("Inicio da app da veciñanza, co tema de día."),
            "persona": "uxia@demo.eira.example",
            "url": f"{c}/app/",
            "theme": "light",
        },
        {
            "name": "cabecera-eira-noite",
            "title": _("Cabeceira da app · noite"),
            "where": _("Inicio da app da veciñanza, co tema escuro (botón «Día / Noite»)."),
            "persona": "uxia@demo.eira.example",
            "url": f"{c}/app/",
            "theme": "dark",
            "night": True,
        },
        {
            "name": "baleiro-reservas",
            "title": _("Sen reservas"),
            "where": _("«As miñas reservas» e o inicio da app dunha persoa sen reservas."),
            "persona": NEW_NEIGHBOUR,
            "url": f"{c}/reservas/",
        },
        {
            "name": "baleiro-avisos",
            "title": _("Sen avisos"),
            "where": _("Avisos dunha persoa que aínda non recibiu ningún."),
            "persona": NEW_NEIGHBOUR,
            "url": f"{c}/avisos/",
        },
        {
            "name": "baleiro-mantemento",
            "title": _("Mantemento ao día"),
            "where": _("App do operario, filtro «Mañá» sen ordes pendentes."),
            "persona": "brais@demo.eira.example",
            "url": f"{c}/operario/?dia=manha",
        },
        {
            "name": "eira-icono-baleiro",
            "title": _("Sen resultados"),
            "where": _("Instalacións cun filtro sen resultados (e páxina de créditos)."),
            "persona": None,
            "url": f"{c}/?kind=pool",
        },
    ]
    for item in items:
        persona = next((p for p in DEMO_PERSONAS if p["email"] == item["persona"]), None)
        item["persona_label"] = f"{persona['name']} ({persona['role']})" if persona else ""
    return render(request, "dev/illustrations.html", {"items": items, "tool": "illustrations"})
