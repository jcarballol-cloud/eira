# SPDX-License-Identifier: EUPL-1.2
"""Acceso por niveis: 0 QR de entrada, 1 chave custodiada, 2 código sen conexión, 3 pechadura conectada."""

import datetime as dt

from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import audit
from apps.facilities.models import AccessLevel
from apps.integrations.registry import get_adapter
from apps.notifications.services import notify_email_only

from . import offline_codes
from .models import AccessEvent, KeyHandover, LockDevice

CHECKIN_EARLY_MINUTES = 15


def on_booking_confirmed(booking):
    if booking.facility.access_level == AccessLevel.CUSTODIAN:
        handover, _created = KeyHandover.objects.get_or_create(
            booking=booking, defaults={"municipality": booking.municipality}
        )
        f = booking.facility
        if f.key_holder_email:
            notify_email_only(
                f.key_holder_email,
                _("Eira · Entrega de chave: %(f)s") % {"f": f.name},
                _("%(who)s recollerá a chave para %(d)s de %(s)s a %(e)s (ref. %(r)s).")
                % {
                    "who": booking.holder_label or _("Unha persoa"),
                    "d": timezone.localtime(booking.start).strftime("%d/%m/%Y"),
                    "s": timezone.localtime(booking.start).strftime("%H:%M"),
                    "e": timezone.localtime(booking.end).strftime("%H:%M"),
                    "r": booking.reference,
                },
            )
            handover.custodian_notified_at = timezone.now()
            handover.save(update_fields=["custodian_notified_at"])


def booking_access_info(booking):
    """O que ve a persoa na súa reserva segundo o nivel de acceso."""
    f = booking.facility
    info = {"level": f.access_level}
    if f.access_level == AccessLevel.OFFLINE_CODE and hasattr(f, "lock"):
        device = f.lock
        try:
            info["code"] = device.code_for_booking(booking)
        except ValueError:
            info["code"] = None
        start, end = offline_codes.window_for(booking.start, booking.end, device.params)
        info["valid_from"], info["valid_until"] = start, end
    elif f.access_level == AccessLevel.CONNECTED and hasattr(f, "lock"):
        device = f.lock
        tol = dt.timedelta(minutes=device.tolerance_minutes)
        now = timezone.now()
        info["can_open"] = booking.start - tol <= now <= booking.end and booking.status in (
            "confirmed",
            "used",
        )
        info["opens_from"] = booking.start - tol
        info["lights_on"] = device.lights_on()
        info["controls_lights"] = device.controls_lights
    elif f.access_level == AccessLevel.CUSTODIAN:
        info["handover"] = getattr(booking, "key_handover", None)
    return info


def validate_code(device, code, at=None, record=True):
    """Simula o firmware da pechadura: valida o código co reloxo `at` e aplica bloqueo por intentos."""
    from apps.bookings.models import Booking
    from apps.bookings.services import check_in

    at = at or timezone.now()
    if device.locked_until and device.locked_until > at:
        return {"ok": False, "reason": "locked", "until": device.locked_until}
    match = offline_codes.validate(code, at, device.params)
    if not match:
        device.failed_attempts += 1
        reason = "invalid"
        if device.failed_attempts >= LockDevice.MAX_FAILED:
            device.locked_until = at + dt.timedelta(minutes=LockDevice.LOCKOUT_MINUTES)
            device.failed_attempts = 0
            reason = "now_locked"
        device.save(update_fields=["failed_attempts", "locked_until"])
        if record:
            AccessEvent.objects.create(
                municipality=device.municipality,
                facility=device.facility,
                kind=AccessEvent.Kind.CODE_DENIED,
                at=at,
            )
        return {"ok": False, "reason": reason}
    device.failed_attempts = 0
    device.save(update_fields=["failed_attempts"])
    step = dt.timedelta(minutes=device.step_minutes)
    start = dt.datetime.fromtimestamp(match.block * step.total_seconds(), tz=dt.UTC)
    end = start + match.duration_blocks * step
    booking = (
        Booking.objects.filter(facility=device.facility, start=start, end=end).holding().first()
    )
    if record:
        AccessEvent.objects.create(
            municipality=device.municipality,
            facility=device.facility,
            booking=booking,
            kind=AccessEvent.Kind.CODE_OK,
            at=at,
        )
        if booking:
            check_in(booking, at)
    return {"ok": True, "match": match, "booking": booking, "slot_start": start, "slot_end": end}


def remote_open(booking, user):
    from apps.bookings.services import check_in

    device = booking.facility.lock
    info = booking_access_info(booking)
    if not info.get("can_open"):
        return False
    adapter = get_adapter("lock")
    adapter.open(device, booking)
    now = timezone.now()
    AccessEvent.objects.create(
        municipality=booking.municipality,
        facility=booking.facility,
        booking=booking,
        user=user,
        kind=AccessEvent.Kind.REMOTE_OPEN,
    )
    if device.controls_lights and booking.facility.lighting:
        adapter.set_lights(device, True, until=booking.end)
        device.lights_on_until = booking.end
        device.save(update_fields=["lights_on_until"])
        AccessEvent.objects.create(
            municipality=booking.municipality,
            facility=booking.facility,
            booking=booking,
            kind=AccessEvent.Kind.LIGHTS_ON,
            detail=f"ata {timezone.localtime(booking.end):%H:%M}",
        )
    check_in(booking, now)
    audit("access.remote_open", user, booking.municipality, booking)
    return True


def qr_checkin(facility, user, at=None):
    """QR fixo (nivel 0): rexistra o uso real. Con reserva activa, marca a reserva como usada."""
    from apps.bookings.models import Booking
    from apps.bookings.services import check_in

    at = at or timezone.now()
    booking = None
    if user and user.is_authenticated:
        booking = (
            Booking.objects.filter(facility=facility, user=user)
            .holding()
            .filter(start__lte=at + dt.timedelta(minutes=CHECKIN_EARLY_MINUTES), end__gt=at)
            .first()
        )
    if booking:
        check_in(booking, at)
        AccessEvent.objects.create(
            municipality=facility.municipality,
            facility=facility,
            booking=booking,
            user=user,
            kind=AccessEvent.Kind.CHECKIN,
            at=at,
        )
    else:
        AccessEvent.objects.create(
            municipality=facility.municipality,
            facility=facility,
            kind=AccessEvent.Kind.ANONYMOUS_USE,
            at=at,
        )
    return booking


def key_out(booking, by):
    from apps.bookings.services import check_in

    handover, _created = KeyHandover.objects.get_or_create(
        booking=booking, defaults={"municipality": booking.municipality}
    )
    handover.handed_at, handover.handed_by = timezone.now(), by
    handover.save()
    AccessEvent.objects.create(
        municipality=booking.municipality,
        facility=booking.facility,
        booking=booking,
        user=by,
        kind=AccessEvent.Kind.KEY_OUT,
    )
    check_in(booking)
    return handover


def key_in(booking, by):
    handover, _created = KeyHandover.objects.get_or_create(
        booking=booking, defaults={"municipality": booking.municipality}
    )
    handover.returned_at, handover.returned_to = timezone.now(), by
    handover.save()
    AccessEvent.objects.create(
        municipality=booking.municipality,
        facility=booking.facility,
        booking=booking,
        user=by,
        kind=AccessEvent.Kind.KEY_IN,
    )
    return handover
