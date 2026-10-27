# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · F: menos ausencias. Recordatorios con acción e lista de espera dinámica nas reservas.

- Recordatorios ás 24 h e ás 2 h co «Confirmo» e o «Cancelo» (cancelar é un toque).
- «Avísame se queda libre» nunha franxa ocupada. A franxa libérase se:
  1. alguén cancela;
  2. o concello o activa (desactivado por defecto) e non se confirmou N minutos antes;
  3. non hai check-in aos 15 min do inicio (niveis 0, 2 e 3).
  Só se libera por 2 ou 3 se hai alguén agardando: sen lista de espera non se toca nada.
- Ofrécese por orde: a primeira persoa que acepta no prazo quédaa (e paga). O ciclo queda en
  `SlotRelease`.
- Devolución: as penalizacións que xa existen mantéñense; se a franxa se volve vender, a
  penalización por cancelación tardía devólvese (o concello non perde o ingreso)."""

import datetime as dt

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import audit
from apps.notifications.services import notify

from .models import Booking, SlotRelease, WaitlistEntry

RELEASE_LEVELS = (0, 2, 3)  # o nivel 1 (chave custodiada) non se libera sen check-in


class WaitlistError(Exception):
    pass


def _url(booking_or_tenant, name, *args):
    from apps.tenants.urlutils import treverse

    return treverse(booking_or_tenant, name, *args)


# ------------------------------------------------------------------ recordatorios
def send_reminders(now=None):
    """24 h e 2 h antes: aviso cos botóns «Confirmo» e «Cancelo» (na pantalla da reserva)."""
    now = now or timezone.now()
    sent = {"24h": 0, "2h": 0}
    base = Booking.objects.filter(
        status=Booking.Status.CONFIRMED, user__isnull=False, attendance_confirmed_at__isnull=True
    ).select_related("facility", "municipality", "user")
    for b in base.filter(
        reminder_24_at__isnull=True,
        start__gt=now + dt.timedelta(hours=2),
        start__lte=now + dt.timedelta(hours=24),
    ):
        _remind(b, hours=24)
        b.reminder_24_at = now
        b.save(update_fields=["reminder_24_at"])
        sent["24h"] += 1
    for b in base.filter(
        reminder_2_at__isnull=True, start__gt=now, start__lte=now + dt.timedelta(hours=2)
    ):
        _remind(b, hours=2)
        b.reminder_2_at = now
        b.save(update_fields=["reminder_2_at"])
        sent["2h"] += 1
    return sent


def _remind(booking, hours):
    when = timezone.localtime(booking.start)
    notify(
        booking.user,
        _("Vés a %(f)s? Confirma ou cancela") % {"f": booking.facility.name},
        _(
            "%(d)s ás %(h)s. Un toque: «Confirmo» ou «Cancelo». Se cancelas, a franxa ofrécese a quen a agarda."
        )
        % {"d": when.strftime("%d/%m"), "h": when.strftime("%H:%M")},
        url=_url(booking.municipality, "bookings:detail", booking.pk) + "#confirmar",
        municipality=booking.municipality,
        email=hours == 24,
    )


def can_confirm(booking, now=None):
    now = now or timezone.now()
    return (
        booking.status == Booking.Status.CONFIRMED
        and booking.attendance_confirmed_at is None
        and booking.start - dt.timedelta(hours=24) <= now < booking.start
    )


def confirm_attendance(booking, by=None):
    if not can_confirm(booking):
        raise WaitlistError(_("Esta reserva non se pode confirmar agora."))
    booking.attendance_confirmed_at = timezone.now()
    booking.save(update_fields=["attendance_confirmed_at"])
    audit("booking.attendance_confirmed", by, booking.municipality, booking)
    return booking


def todo_for(booking, now=None):
    """«Que tes que facer e cando»: os pasos que quedan, cada un coa súa hora."""
    now = now or timezone.now()
    m = booking.municipality
    f = booking.facility
    items = []
    local = timezone.localtime
    if booking.status == Booking.Status.PENDING_PAYMENT:
        items.append(
            {"key": "pay", "when": booking.hold_expires_at, "text": _("Paga para gardar a franxa")}
        )
    if booking.status == Booking.Status.PENDING_OFFICE:
        items.append(
            {
                "key": "pay",
                "when": booking.hold_expires_at,
                "text": _("Paga na oficina de deportes"),
            }
        )
    if booking.status == Booking.Status.PENDING_APPROVAL:
        items.append({"key": "wait", "when": None, "text": _("Agarda a aprobación do concello")})
    if booking.status in (Booking.Status.CONFIRMED, Booking.Status.USED) and booking.end > now:
        if booking.attendance_confirmed_at:
            items.append(
                {
                    "key": "confirm",
                    "when": booking.attendance_confirmed_at,
                    "done": True,
                    "text": _("Asistencia confirmada"),
                }
            )
        elif booking.status == Booking.Status.CONFIRMED:
            text = _("Confirma que vés (desde 24 h antes)")
            if m.confirm_release_enabled:
                text = _(
                    "Confirma que vés antes das %(h)s: se non, e hai lista de espera, a franxa ofrécese"
                ) % {
                    "h": local(
                        booking.start - dt.timedelta(minutes=m.confirm_release_minutes)
                    ).strftime("%H:%M")
                }
            items.append(
                {"key": "confirm", "when": booking.start - dt.timedelta(hours=24), "text": text}
            )
        if booking.can_cancel():
            items.append(
                {
                    "key": "cancel",
                    "when": booking.cancellation_cutoff(),
                    "text": _("Cancelación gratuíta ata esta hora"),
                }
            )
        if booking.checked_in_at:
            items.append(
                {
                    "key": "checkin",
                    "when": booking.checked_in_at,
                    "done": True,
                    "text": _("Entrada rexistrada"),
                }
            )
        else:
            text = {
                0: _("Ao chegar, escanea o QR da entrada"),
                1: _("Recolle a chave antes de empezar"),
                2: _("Abre co teu código no teclado"),
                3: _("Abre a porta desde o móbil"),
            }[f.access_level]
            if f.access_level in RELEASE_LEVELS:
                text += " " + _("(se hai lista de espera, aos %(n)s min libérase)") % {
                    "n": m.checkin_release_minutes
                }
            items.append({"key": "checkin", "when": booking.start, "text": text})
        if f.access_level >= 1:
            items.append(
                {
                    "key": "close",
                    "when": booking.end,
                    "text": _("Ao rematar, completa a lista de peche"),
                }
            )
    return items


# ------------------------------------------------------------------ lista de espera
def join(facility, start, user):
    end = start + dt.timedelta(minutes=facility.slot_minutes)
    if start <= timezone.now() - dt.timedelta(
        minutes=facility.municipality.checkin_release_minutes
    ):
        raise WaitlistError(_("Esa franxa xa comezou."))
    if Booking.objects.filter(facility=facility, user=user, start=start).holding().exists():
        raise WaitlistError(_("Xa tes esta franxa."))
    taken = Booking.objects.filter(facility=facility).holding().overlapping(start, end).count()
    if taken < facility.capacity:
        raise WaitlistError(_("A franxa está libre: resérvaa directamente."))
    entry, created = WaitlistEntry.objects.get_or_create(
        facility=facility,
        start=start,
        user=user,
        defaults={"municipality": facility.municipality, "end": end},
    )
    if not created and entry.status in (WaitlistEntry.Status.LEFT, WaitlistEntry.Status.EXPIRED):
        entry.status = WaitlistEntry.Status.WAITING
        entry.save(update_fields=["status"])
    audit("waitlist.join", user, facility.municipality, entry)
    return entry


def leave(entry, by=None):
    entry.status = WaitlistEntry.Status.LEFT
    entry.save(update_fields=["status"])
    if entry.release_id and entry.release.closed_at is None:
        entry.release.add("left", _first_name(entry.user))
        entry.release.save(update_fields=["log"])
        offer_next(entry.release)


def _waiting(facility, start):
    return WaitlistEntry.objects.filter(
        facility=facility, start=start, status=WaitlistEntry.Status.WAITING
    ).order_by("created_at", "pk")


def _first_name(user):
    name = (getattr(user, "display_name", "") or "").split()
    return name[0] if name else _("Persoa da lista")


def release_slot(booking, reason):
    """Libera a franxa dunha reserva e ofrécea á lista de espera (se hai alguén)."""
    if not _waiting(booking.facility, booking.start).exists():
        return None
    rel = SlotRelease.objects.create(
        municipality=booking.municipality,
        facility=booking.facility,
        start=booking.start,
        end=booking.end,
        released_booking=booking,
        reason=reason,
    )
    rel.add("released", reason)
    rel.save(update_fields=["log"])
    audit("waitlist.release", None, booking.municipality, booking, reason=reason)
    offer_next(rel)
    return rel


def offer_next(rel, now=None):
    """Ofrece a franxa á seguinte persoa da lista (unha cada vez, por orde)."""
    now = now or timezone.now()
    m = rel.municipality
    if rel.closed_at or now >= rel.end:
        if not rel.closed_at:
            rel.closed_at = now
            rel.add("closed", "")
            rel.save(update_fields=["closed_at", "log"])
        return None
    entry = _waiting(rel.facility, rel.start).first()
    if entry is None:
        rel.closed_at = now
        rel.add("nobody", "")
        rel.save(update_fields=["closed_at", "log"])
        return None
    entry.status = WaitlistEntry.Status.OFFERED
    entry.offered_at = now
    entry.offer_expires_at = min(now + dt.timedelta(minutes=m.waitlist_offer_minutes), rel.end)
    entry.release = rel
    entry.save(update_fields=["status", "offered_at", "offer_expires_at", "release"])
    rel.add("offered", _first_name(entry.user))
    rel.save(update_fields=["log"])
    when = timezone.localtime(rel.start)
    notify(
        entry.user,
        _("Quedou libre: %(f)s") % {"f": rel.facility.name},
        _("%(d)s ás %(h)s. Tes ata as %(x)s para collela; se non, pasa á seguinte persoa.")
        % {
            "d": when.strftime("%d/%m"),
            "h": when.strftime("%H:%M"),
            "x": timezone.localtime(entry.offer_expires_at).strftime("%H:%M"),
        },
        url=_url(m, "bookings:waitlist_offer", entry.pk),
        municipality=m,
        level="success",
        email=True,
    )
    return entry


def accept(entry, user, *, payment_method=None):
    """A primeira persoa que acepta no prazo quédaa e paga (como unha reserva normal)."""
    from .services import BookingError, create_booking

    if entry.user_id != user.pk or not entry.is_live_offer:
        raise WaitlistError(_("Esta oferta xa non está dispoñible."))
    rel = entry.release
    facility = entry.facility
    try:
        with transaction.atomic():
            booking = create_booking(
                facility,
                entry.start,
                user,
                rules_version=facility.current_rules(),
                payment_method=payment_method,
                allow_started=True,
            )
    except BookingError as exc:
        raise WaitlistError(str(exc)) from exc
    entry.status = WaitlistEntry.Status.ACCEPTED
    entry.booking = booking
    entry.save(update_fields=["status", "booking"])
    rel.taken_booking = booking
    rel.closed_at = timezone.now()
    rel.add("accepted", _first_name(user))
    _refund_penalty_if_resold(rel)
    rel.save(update_fields=["taken_booking", "closed_at", "log", "penalty_refunded_cents"])
    # O resto da lista desta franxa segue agardando por se volve quedar libre
    audit("waitlist.accept", user, facility.municipality, booking, release=rel.pk)
    return booking


def _refund_penalty_if_resold(rel):
    """Cancelación tardía cunha penalización: se a franxa se volve vender, devólvese."""
    original = rel.released_booking
    if original is None or rel.reason != SlotRelease.Reason.CANCELLED:
        return 0
    penalty = max(0, original.paid_cents - original.refunded_cents)
    if not penalty or original.status != Booking.Status.CANCELLED:
        return 0
    from .payments import refund_booking

    refund_booking(original, penalty)
    original.refunded_cents += penalty
    original.save(update_fields=["refunded_cents"])
    rel.penalty_refunded_cents = penalty
    rel.add("penalty_refunded", "")
    if original.user:
        notify(
            original.user,
            _("Devolvémosche a penalización: %(f)s") % {"f": original.facility.name},
            _("Outra persoa da lista de espera colleu a franxa. Devolución: %(r)s €.")
            % {"r": f"{penalty / 100:.2f}"},
            municipality=original.municipality,
            level="success",
        )
    return penalty


def process(now=None):
    """Tarefa periódica: ofertas caducadas, reservas sen confirmar e sen check-in."""
    from .services import cancel_booking

    now = now or timezone.now()
    done = {"expired": 0, "unconfirmed": 0, "no_checkin": 0}
    for entry in WaitlistEntry.objects.filter(
        status=WaitlistEntry.Status.OFFERED, offer_expires_at__lte=now
    ).select_related("release"):
        entry.status = WaitlistEntry.Status.EXPIRED
        entry.save(update_fields=["status"])
        if entry.release and entry.release.closed_at is None:
            entry.release.add("expired", _first_name(entry.user))
            entry.release.save(update_fields=["log"])
            offer_next(entry.release, now=now)
        done["expired"] += 1
    waiting = WaitlistEntry.objects.filter(status=WaitlistEntry.Status.WAITING, end__gt=now)
    slots = set(waiting.values_list("facility_id", "start"))
    if not slots:
        return done
    for b in Booking.objects.filter(
        status=Booking.Status.CONFIRMED, start__gt=now - dt.timedelta(hours=2), end__gt=now
    ).select_related("municipality", "facility", "user"):
        if (b.facility_id, b.start) not in slots:
            continue
        m = b.municipality
        if (
            m.confirm_release_enabled
            and b.start > now
            and b.attendance_confirmed_at is None
            and now >= b.start - dt.timedelta(minutes=m.confirm_release_minutes)
        ):
            cancel_booking(
                b,
                by=None,
                reason=_("Liberada: non se confirmou a asistencia a tempo."),
                release_reason=SlotRelease.Reason.UNCONFIRMED,
            )
            done["unconfirmed"] += 1
        elif (
            b.facility.access_level in RELEASE_LEVELS
            and b.checked_in_at is None
            and now >= b.start + dt.timedelta(minutes=m.checkin_release_minutes)
        ):
            b.status = Booking.Status.NO_SHOW
            b.cancel_reason = str(
                _("Liberada: sen check-in aos %(n)s min.") % {"n": m.checkin_release_minutes}
            )
            b.save(update_fields=["status", "cancel_reason"])
            audit("booking.released_no_checkin", None, m, b)
            if b.user:
                notify(
                    b.user,
                    _("Liberamos a túa franxa en %(f)s") % {"f": b.facility.name},
                    _("Non rexistraches a entrada aos %(n)s min e había lista de espera.")
                    % {"n": m.checkin_release_minutes},
                    municipality=m,
                    level="warning",
                )
            release_slot(b, SlotRelease.Reason.NO_CHECKIN)
            done["no_checkin"] += 1
    return done
