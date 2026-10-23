# SPDX-License-Identifier: EUPL-1.2
"""Ferramentas de demostración (só con EIRA_DEMO_TOOLS=1): bandexa de correo, TPV e Cl@ve
simulados, simulador de pechadura e cambio rápido de perfil."""

import datetime as dt

from django.contrib.auth import login
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.access.models import LockDevice
from apps.access.services import validate_code
from apps.accounts.models import User
from apps.tenants.prefs import write_prefs

from .demo import DEMO_PERSONAS
from .identity import FAKE_IDENTITIES
from .models import DevMail, FakePayment, OutboundMessage


def mailbox(request):
    to = request.GET.get("para", "")
    mails = DevMail.objects.all()
    if to:
        mails = mails.filter(to__iexact=to)
    return render(request, "dev/mailbox.html", {"mails": mails[:50], "to": to, "tool": "mail"})


def outbox(request):
    return render(request, "dev/outbox.html", {"messages_out": OutboundMessage.objects.all()[:100], "tool": "outbox"}
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
        },
    )


@require_POST
def login_as(request):
    email = request.POST.get("email", "")
    persona = next((p for p in DEMO_PERSONAS if p["email"] == email), None)
    if persona is None:
        raise Http404
    user = User.objects.filter(email=email).first()
    if user is None:
        raise Http404("Executa `make seed` primeiro")
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    from apps.accounts.profiles import home_url

    response = redirect(home_url(user))
    return write_prefs(response, {persona.get("prefs"): True} if persona.get("prefs") else {})
