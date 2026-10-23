# SPDX-License-Identifier: EUPL-1.2
"""Regras de negocio das reservas. As vistas e a API usan só estas funcións."""

import datetime as dt
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import audit
from apps.facilities.models import Closure, Facility, Tariff
from apps.notifications.services import notify

from .models import Booking

HOLD_MINUTES = 15
RECOMMENDED_PER_DAY = 2
RECOMMEND_THRESHOLD = 0.3


class BookingError(Exception):
    pass


# ---------------------------------------------------------------- dispoñibilidade


def _aware(day, time):
    return timezone.make_aware(dt.datetime.combine(day, time))


def opening_intervals(facility, day):
    hours = [
        h for h in facility.opening_hours.all() if h.weekday == day.weekday() and h.applies_on(day)
    ]
    return [(_aware(day, h.opens), _aware(day, h.closes)) for h in hours]


def slot_starts(facility, day):
    step = dt.timedelta(minutes=facility.slot_minutes)
    out = []
    for opens, closes in opening_intervals(facility, day):
        t = opens
        while t + step <= closes:
            out.append(t)
            t += step
    return out


def closures_overlapping(facility, start, end):
    return Closure.objects.filter(municipality_id=facility.municipality_id).filter(
        Q(facility=facility) | Q(facility__isnull=True), starts_at__lt=end, ends_at__gt=start
    )


@dataclass
class Slot:
    start: dt.datetime
    end: dt.datetime
    status: str  # free | recommended | few | busy | mine | closed | past
    booked: int = 0
    capacity: int = 1
    closure_reason: str = ""
    mine: object = None
    labels: dict = field(default_factory=dict)

    @property
    def bookable(self):
        return self.status in ("free", "recommended", "few")

    @property
    def label(self):
        return {
            "free": _("Libre"),
            "recommended": _("Recomendada"),
            "few": _("Pouca xente"),
            "busy": _("Ocupada"),
            "mine": _("A túa reserva"),
            "closed": _("Pechada"),
            "past": _("Pasada"),
        }[self.status]

    @property
    def symbol(self):
        return {
            "free": "○",
            "recommended": "★",
            "few": "◔",
            "busy": "●",
            "mine": "✓",
            "closed": "✕",
            "past": "–",
        }[self.status]


def week_grid(facility, monday, user=None, now=None):
    """Grella semanal: días (columnas) × horas (filas). Devolve tamén a lista por día (móbil)."""
    from apps.analytics.recommend import expected_occupancy

    now = now or timezone.now()
    days = [monday + dt.timedelta(days=i) for i in range(7)]
    week_start = _aware(monday, dt.time.min)
    week_end = week_start + dt.timedelta(days=7)
    bookings = list(
        Booking.objects.filter(facility=facility).holding().overlapping(week_start, week_end)
    )
    closures = list(closures_overlapping(facility, week_start, week_end))
    expected = expected_occupancy(facility)
    step = dt.timedelta(minutes=facility.slot_minutes)
    max_day = timezone.localdate() + dt.timedelta(days=facility.municipality.max_advance_days)

    by_day = {}
    times = set()
    for day in days:
        slots = []
        for start in slot_starts(facility, day):
            end = start + step
            overlapping = [b for b in bookings if b.start < end and b.end > start]
            mine = next(
                (b for b in overlapping if user and user.is_authenticated and b.user_id == user.pk),
                None,
            )
            closure = next((c for c in closures if c.starts_at < end and c.ends_at > start), None)
            n = len(overlapping)
            if mine:
                status = "mine"
            elif closure:
                status = "closed"
            elif end <= now or day > max_day:
                status = "past"
            elif n >= facility.capacity:
                status = "busy"
            elif facility.capacity > 1 and n / facility.capacity < 0.5:
                status = "few"
            else:
                status = "free"
            slots.append(
                Slot(
                    start,
                    end,
                    status,
                    n,
                    facility.capacity,
                    closure.reason if closure else "",
                    mine,
                )
            )
            times.add(timezone.localtime(start).time())
        # Recomendadas: como moito as 2 franxas libres con menor demanda histórica do día
        candidates = sorted(
            (expected.get((s.start.weekday(), timezone.localtime(s.start).hour), 1), i)
            for i, s in enumerate(slots)
            if s.status in ("free", "few")
        )
        for value, i in candidates[:RECOMMENDED_PER_DAY]:
            if value < RECOMMEND_THRESHOLD:
                slots[i].status = "recommended"
        by_day[day] = slots

    rows = []
    for t in sorted(times):
        cells = []
        for day in days:
            cells.append(
                next((s for s in by_day[day] if timezone.localtime(s.start).time() == t), None)
            )
        rows.append({"time": t, "cells": cells})
    # Día despregado por defecto na vista móbil: o primeiro con franxas reservables
    open_day = next(
        (d for d in days if any(s.bookable for s in by_day[d])),
        next((d for d in days if any(s.status == "mine" for s in by_day[d])), days[0]),
    )
    return {
        "days": days,
        "rows": rows,
        "by_day": [(d, by_day[d]) for d in days],
        "open_day": open_day,
    }


# ---------------------------------------------------------------- tarifas


def audience_for(facility, user):
    if user is None or not user.is_resident(facility.municipality):
        return Tariff.Audience.NON_RESIDENT
    age = user.age
    tariffs = {t.audience for t in facility.tariffs.all()}
    if age is not None and age <= 25 and Tariff.Audience.YOUTH in tariffs:
        return Tariff.Audience.YOUTH
    if age is not None and age >= 65 and Tariff.Audience.SENIOR in tariffs:
        return Tariff.Audience.SENIOR
    return Tariff.Audience.RESIDENT


def price_for(facility, user, audience=None):
    audience = audience or audience_for(facility, user)
    tariffs = {t.audience: t.price_cents for t in facility.tariffs.all()}
    price = tariffs.get(audience)
    if price is None:
        price = tariffs.get(Tariff.Audience.RESIDENT, 0)
    return audience, price


# ---------------------------------------------------------------- operacións


def _validate_slot(facility, start, end, exclude=None, now=None):
    now = now or timezone.now()
    if start <= now:
        raise BookingError(_("Esa franxa xa pasou."))
    if timezone.localdate(start) > timezone.localdate() + dt.timedelta(
        days=facility.municipality.max_advance_days
    ):
        raise BookingError(_("Aínda non se pode reservar con tanta antelación."))
    if start not in slot_starts(facility, timezone.localdate(start)) or end - start != dt.timedelta(
        minutes=facility.slot_minutes
    ):
        raise BookingError(_("A instalación non abre nesa franxa."))
    if closures_overlapping(facility, start, end).exists():
        raise BookingError(_("A instalación está pechada nesa franxa."))
    qs = Booking.objects.filter(facility=facility).holding().overlapping(start, end)
    if exclude is not None:
        qs = qs.exclude(pk=exclude.pk)
    if qs.count() >= facility.capacity:
        raise BookingError(_("Esa franxa acaba de quedar ocupada. Escolle outra."))


def create_booking(
    facility,
    start,
    user=None,
    *,
    rules_version,
    channel=Booking.Channel.ONLINE,
    created_by=None,
    holder_name="",
    holder_phone="",
):
    end = start + dt.timedelta(minutes=facility.slot_minutes)
    if rules_version is None or rules_version.facility_id != facility.pk:
        raise BookingError(_("Debes aceptar as normas de uso vixentes."))
    with transaction.atomic():
        Facility.objects.select_for_update().filter(pk=facility.pk).first()
        _validate_slot(facility, start, end)
        if user is not None:
            active = (
                Booking.objects.filter(
                    municipality=facility.municipality, user=user, end__gt=timezone.now()
                )
                .holding()
                .count()
            )
            if active >= facility.municipality.max_active_bookings:
                raise BookingError(
                    _("Xa tes o máximo de reservas activas permitidas neste concello.")
                )
        audience, price = price_for(facility, user)
        booking = Booking.objects.create(
            municipality=facility.municipality,
            facility=facility,
            user=user,
            start=start,
            end=end,
            channel=channel,
            created_by=created_by or user,
            holder_name=holder_name,
            holder_phone=holder_phone,
            tariff_audience=audience,
            price_cents=price,
            status=Booking.Status.CONFIRMED if price == 0 else Booking.Status.PENDING_PAYMENT,
            hold_expires_at=timezone.now() + dt.timedelta(minutes=HOLD_MINUTES) if price else None,
            rules_version=rules_version,
            rules_accepted_at=timezone.now(),
        )
    audit("booking.create", created_by or user, facility.municipality, booking, channel=channel)
    if booking.status == Booking.Status.CONFIRMED:
        _after_confirm(booking)
    return booking


def mark_paid(booking, payment_reference, amount_cents):
    if booking.status != Booking.Status.PENDING_PAYMENT:
        return booking
    if amount_cents < booking.price_cents:
        raise BookingError(_("Importe pagado insuficiente."))
    booking.status = Booking.Status.CONFIRMED
    booking.paid_cents = amount_cents
    booking.payment_reference = payment_reference
    booking.hold_expires_at = None
    booking.save(update_fields=["status", "paid_cents", "payment_reference", "hold_expires_at"])
    audit("booking.paid", booking.user, booking.municipality, booking, amount=amount_cents)
    _after_confirm(booking)
    return booking


def _after_confirm(booking):
    from apps.access.services import on_booking_confirmed
    from apps.tenants.urlutils import treverse

    url = treverse(booking.municipality, "bookings:detail", booking.pk)
    notify(
        booking.user,
        _("Reserva confirmada: %(f)s") % {"f": booking.facility.name},
        _("%(d)s de %(s)s a %(e)s. Referencia %(r)s.")
        % {
            "d": timezone.localtime(booking.start).strftime("%d/%m/%Y"),
            "s": timezone.localtime(booking.start).strftime("%H:%M"),
            "e": timezone.localtime(booking.end).strftime("%H:%M"),
            "r": booking.reference,
        },
        url=url,
        municipality=booking.municipality,
        level="success",
    )
    on_booking_confirmed(booking)


def cancel_booking(booking, by=None, reason="", force_full_refund=False):
    if booking.status not in (Booking.Status.CONFIRMED, Booking.Status.PENDING_PAYMENT):
        raise BookingError(_("Esta reserva xa non se pode cancelar."))
    if not force_full_refund and booking.start <= timezone.now():
        raise BookingError(_("A reserva xa comezou."))
    penalty = 0 if force_full_refund else booking.penalty_if_cancelled_now()
    refund = max(0, booking.paid_cents - penalty)
    if refund and booking.payment_reference:
        from apps.integrations.registry import get_adapter

        get_adapter("payment").refund(booking.payment_reference, refund)
    booking.status = Booking.Status.CANCELLED
    booking.cancelled_at = timezone.now()
    booking.cancel_reason = reason[:200]
    booking.refunded_cents = refund
    booking.save(update_fields=["status", "cancelled_at", "cancel_reason", "refunded_cents"])
    audit("booking.cancel", by, booking.municipality, booking, refund=refund, penalty=penalty)
    if booking.user and by != booking.user:
        notify(
            booking.user,
            _("Reserva cancelada: %(f)s") % {"f": booking.facility.name},
            (reason + "\n" if reason else "")
            + _("Devolución: %(r)s €.") % {"r": f"{refund / 100:.2f}"},
            municipality=booking.municipality,
            level="warning",
        )
    return refund, penalty


def modify_booking(booking, new_start, by=None):
    if not booking.can_modify():
        raise BookingError(_("Xa non se pode modificar esta reserva (prazo superado)."))
    facility = booking.facility
    new_end = new_start + dt.timedelta(minutes=facility.slot_minutes)
    with transaction.atomic():
        Facility.objects.select_for_update().filter(pk=facility.pk).first()
        _validate_slot(facility, new_start, new_end, exclude=booking)
        old = booking.start
        booking.start, booking.end = new_start, new_end
        booking.save(update_fields=["start", "end"])
    audit(
        "booking.modify",
        by,
        booking.municipality,
        booking,
        old=old.isoformat(),
        new=new_start.isoformat(),
    )
    from apps.access.services import on_booking_confirmed

    on_booking_confirmed(booking)
    return booking


def check_in(booking, at=None):
    if booking.status not in (Booking.Status.CONFIRMED, Booking.Status.USED):
        return False
    booking.checked_in_at = booking.checked_in_at or at or timezone.now()
    booking.status = Booking.Status.USED
    booking.save(update_fields=["checked_in_at", "status"])
    return True


def submit_closing_checklist(booking, door_ok, key_ok, all_ok, notes="", by=None):
    from apps.incidents.models import Incident

    booking.closed_at = timezone.now()
    booking.close_door_ok, booking.close_key_ok, booking.close_all_ok = door_ok, key_ok, all_ok
    booking.close_notes = notes[:1000]
    booking.save(
        update_fields=["closed_at", "close_door_ok", "close_key_ok", "close_all_ok", "close_notes"]
    )
    problems = []
    if door_ok is False:
        problems.append(_("A porta non quedou pechada."))
    if key_ok is False:
        problems.append(_("A chave non se devolveu."))
    if all_ok is False:
        problems.append(_("Non todo quedou en orde."))
    incident = None
    if problems:
        category = (
            Incident.Category.ACCESS
            if (door_ok is False or key_ok is False)
            else Incident.Category.DAMAGE
        )
        incident = Incident.objects.create(
            municipality=booking.municipality,
            facility=booking.facility,
            reporter=booking.user,
            booking=booking,
            category=category,
            source=Incident.Source.CHECKLIST,
            description=" ".join(problems) + (f"\n{notes}" if notes else ""),
        )
        from apps.incidents.services import notify_staff_new_incident

        notify_staff_new_incident(incident)
    return incident


def apply_closure(closure, by=None):
    """Ao crear un peche, cancela con devolución íntegra as reservas afectadas e avisa."""
    qs = (
        Booking.objects.filter(municipality=closure.municipality)
        .holding()
        .overlapping(closure.starts_at, closure.ends_at)
    )
    if closure.facility_id:
        qs = qs.filter(facility_id=closure.facility_id)
    affected = list(qs.select_related("facility", "user"))
    reason = _("Peche da instalación: %(r)s") % {"r": closure.reason}
    for booking in affected:
        cancel_booking(booking, by=by, reason=reason, force_full_refund=True)
    audit("closure.apply", by, closure.municipality, closure, affected=len(affected))
    return affected


def expire_holds(now=None):
    now = now or timezone.now()
    return Booking.objects.filter(
        status=Booking.Status.PENDING_PAYMENT, hold_expires_at__lte=now
    ).update(status=Booking.Status.CANCELLED, cancelled_at=now, cancel_reason="hold expired")


def mark_no_shows(now=None):
    """Reservas confirmadas que remataron sen rexistro de uso (chave, código ou apertura).

    Nas instalacións abertas (nivel 0) o QR é voluntario, así que non se marcan como non presentadas.
    """
    now = now or timezone.now()
    qs = Booking.objects.filter(
        status=Booking.Status.CONFIRMED,
        end__lte=now,
        checked_in_at__isnull=True,
        facility__access_level__gte=1,
    )
    return qs.update(status=Booking.Status.NO_SHOW)
