# SPDX-License-Identifier: EUPL-1.2
"""Regras de negocio das reservas. As vistas e a API usan só estas funcións."""

import datetime as dt
from dataclasses import dataclass, field

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import audit
from apps.facilities.models import Closure, Facility, Tariff
from apps.notifications.services import notify

from .models import Booking

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
    discount_pct: int = 0
    price_cents: int | None = None  # prezo final para a persoa (con desconto)
    base_cents: int = 0  # prezo sen desconto
    light_cents: int = 0  # v5: suplemento de luz automático nesta franxa

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


def _context(facility, start, end):
    from apps.analytics.recommend import expected_occupancy

    bookings = list(Booking.objects.filter(facility=facility).holding().overlapping(start, end))
    closures = list(closures_overlapping(facility, start, end))
    return bookings, closures, expected_occupancy(facility)


def day_slots(facility, day, user=None, now=None, ctx=None):
    """Franxas dun día co seu estado. As «recomendadas» levan o desconto de baixa demanda do concello."""
    now = now or timezone.now()
    if ctx is None:
        ctx = _context(
            facility, _aware(day, dt.time.min), _aware(day + dt.timedelta(days=1), dt.time.min)
        )
    bookings, closures, expected = ctx
    step = dt.timedelta(minutes=facility.slot_minutes)
    max_day = timezone.localdate() + dt.timedelta(
        days=advance_days_for(facility.municipality, user)
    )
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
        elif start <= now or day > max_day:  # unha franxa xa empezada non se pode reservar
            status = "past"
        elif n >= facility.capacity:
            status = "busy"
        elif facility.capacity > 1 and n / facility.capacity < 0.5:
            status = "few"
        else:
            status = "free"
        slots.append(
            Slot(start, end, status, n, facility.capacity, closure.reason if closure else "", mine)
        )
    # Recomendadas: como moito as 2 franxas libres con menor demanda histórica do día
    candidates = sorted(
        (
            expected.get(
                (timezone.localtime(s.start).weekday(), timezone.localtime(s.start).hour), 1
            ),
            i,
        )
        for i, s in enumerate(slots)
        if s.status in ("free", "few")
    )
    discount = facility.municipality.low_demand_discount_pct
    for value, i in candidates[:RECOMMENDED_PER_DAY]:
        if value < RECOMMEND_THRESHOLD:
            slots[i].status = "recommended"
            slots[i].discount_pct = discount
    return slots


def low_demand_discount(facility, start):
    """Desconto (%) se a franxa é unha das recomendadas por baixa demanda; 0 se non."""
    for s in day_slots(facility, timezone.localdate(start)):
        if s.start == start:
            return s.discount_pct
    return 0


def week_grid(facility, monday, user=None, now=None):
    """Grella semanal: días (columnas) × horas (filas). Devolve tamén a lista por día (móbil)."""
    days = [monday + dt.timedelta(days=i) for i in range(7)]
    week_start = _aware(monday, dt.time.min)
    ctx = _context(facility, week_start, week_start + dt.timedelta(days=7))
    by_day = {day: day_slots(facility, day, user, now, ctx) for day in days}
    times = sorted({timezone.localtime(s.start).time() for slots in by_day.values() for s in slots})
    rows = [
        {
            "time": t,
            "cells": [
                next((s for s in by_day[d] if timezone.localtime(s.start).time() == t), None)
                for d in days
            ],
        }
        for t in times
    ]
    # Día seleccionado por defecto: o primeiro con franxas reservables
    open_day = next(
        (d for d in days if any(s.bookable for s in by_day[d])),
        next((d for d in days if any(s.status == "mine" for s in by_day[d])), days[0]),
    )
    # Prezo de cada franxa para esta persoa (tarifa máis favorable e desconto das tranquilas)
    if facility.tariffs.exists():
        base = price_for(facility, user if getattr(user, "is_authenticated", False) else None).base
        for slots in by_day.values():
            for s in slots:
                s.base_cents = base
                s.price_cents = base * (100 - s.discount_pct) // 100 if s.discount_pct else base
    # v5: franxas que levan o suplemento de luz (indicado na grella)
    if facility.lighting and facility.lighting_supplement_cents:
        from .lighting import slot_needs_light

        for slots in by_day.values():
            for s in slots:
                if s.bookable and slot_needs_light(facility, s.start, s.end):
                    s.light_cents = facility.lighting_supplement_cents
    picker = [
        {
            "day": d,
            "slots": [s for s in by_day[d] if s.status != "past"],
            "bookable": sum(1 for s in by_day[d] if s.bookable),
            "recommended": any(s.status == "recommended" for s in by_day[d]),
            "mine": any(s.status == "mine" for s in by_day[d]),
            "selected": d == open_day,
        }
        for d in days
    ]
    return {
        "days": days,
        "rows": rows,
        "by_day": [(d, by_day[d]) for d in days],
        "open_day": open_day,
        "picker": picker,
    }


# ---------------------------------------------------------------- tarifas


def applicable_audiences(facility, user):
    """Colectivos aos que a persoa ten dereito: empadroamento, idade e tarifa reducida validada."""
    if user is None or not user.is_resident(facility.municipality):
        return [Tariff.Audience.NON_RESIDENT]
    out = [Tariff.Audience.RESIDENT]
    age = user.age
    if age is not None and age <= 25:
        out.append(Tariff.Audience.YOUTH)
    if age is not None and age >= 65:
        out.append(Tariff.Audience.SENIOR)
    if any(e.is_valid for e in user.eligibilities.filter(municipality=facility.municipality)):
        out.append(Tariff.Audience.REDUCED)
    return out


def audience_for(facility, user):
    return price_for(facility, user)[0]


class PriceQuote(tuple):
    """(colectivo, prezo) para compatibilidade, con base e desconto como atributos."""

    def __new__(cls, audience, price, base, discount):
        obj = super().__new__(cls, (audience, price))
        obj.audience, obj.price, obj.base, obj.discount = audience, price, base, discount
        return obj


def price_for(facility, user, audience=None, start=None):
    """Prezo que se mostra antes de pagar: aplícase a tarifa máis favorable á persoa e, nas franxas
    de baixa demanda, o desconto do concello."""
    tariffs = {t.audience: t.price_cents for t in facility.tariffs.all()}
    if audience:
        options = [(tariffs.get(audience, tariffs.get(Tariff.Audience.RESIDENT, 0)), audience)]
    else:
        options = [(tariffs[a], a) for a in applicable_audiences(facility, user) if a in tariffs]
        if not options:
            options = [(tariffs.get(Tariff.Audience.RESIDENT, 0), Tariff.Audience.RESIDENT)]
    base, audience = min(options, key=lambda o: o[0])
    discount = low_demand_discount(facility, start) if (start and base) else 0
    final = base * (100 - discount) // 100 if discount else base
    return PriceQuote(audience, final, base, discount)


# ---------------------------------------------------------------- v5 · rede de concellos


def linked_to(municipality, user):
    """A persoa ten conta ou empadroamento neste concello?"""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return (
        user.memberships.filter(municipality=municipality).exists()
        or user.residencies.filter(municipality=municipality, revoked_at__isnull=True).exists()
    )


def network_origin(municipality, user):
    """Concello de orixe da persoa se reserva desde outro concello da mesma rede; se non, None."""
    if not municipality.region_id or linked_to(municipality, user):
        return None
    home = linked_home(user)
    if home and home.pk != municipality.pk and home.region_id == municipality.region_id:
        return home
    return None


def linked_home(user):
    """Concello propio da persoa só polos seus vínculos (empadroamento ou conta), sen supoñer."""
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    residency = user.residencies.filter(revoked_at__isnull=True).select_related("municipality")
    first = residency.first()
    if first:
        return first.municipality
    membership = user.memberships.select_related("municipality").first()
    return membership.municipality if membership else None


def advance_days_for(municipality, user):
    """Antelación máxima: a do concello ou, para persoas doutros concellos, a da rede."""
    if (
        municipality.network_advance_days is not None
        and user is not None
        and getattr(user, "is_authenticated", False)
        and not linked_to(municipality, user)
    ):
        return min(municipality.network_advance_days, municipality.max_advance_days)
    return municipality.max_advance_days


@dataclass
class Quote:
    """Prezo antes de pagar, desglosado: franxa (con desconto) + luz."""

    audience: str
    slot_cents: int
    base_cents: int
    discount_pct: int
    lighting_cents: int
    lighting_auto: bool
    method: str
    light_on: bool = False  # acéndese a luz (pagada ou incluída no bono ou na gratuíta)

    @property
    def total_cents(self):
        return self.slot_cents + self.lighting_cents


def quote(facility, user, start, *, needs_light=False, method=None):
    """Prezo final dunha franxa para unha persoa e unha forma de pagamento."""
    from apps.tenants.models import PaymentMethod

    from .lighting import lighting_supplement

    q = price_for(facility, user, start=start)
    end = start + dt.timedelta(minutes=facility.slot_minutes)
    light, auto = lighting_supplement(facility, start, end, requested=needs_light)
    method = method or facility.payment_method_list()[0]
    slot = q.price
    light_on = bool(light)
    if method in (PaymentMethod.FREE, PaymentMethod.VOUCHER):
        # Gratuíta: sen taxa. Bono: un uso cobre a franxa, luz incluída (DECISIONS v5).
        slot, light = 0, 0
    return Quote(q.audience, slot, q.base, q.discount, light, auto, method, light_on)


def usable_vouchers(facility, user):
    from .models import Voucher

    if user is None or not getattr(user, "is_authenticated", False):
        return []
    return [
        v
        for v in Voucher.objects.filter(
            user=user, municipality=facility.municipality, status=Voucher.Status.ACTIVE
        ).select_related("type")
        if v.usable_for(facility)
    ]


# ---------------------------------------------------------------- operacións


def _validate_slot(facility, start, end, exclude=None, now=None, check_past=True, user=None):
    now = now or timezone.now()
    if check_past and start <= now:
        raise BookingError(_("Esa franxa xa pasou."))
    if timezone.localdate(start) > timezone.localdate() + dt.timedelta(
        days=advance_days_for(facility.municipality, user)
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
    participants=1,
    participant_names="",
    payment_method=None,
    needs_light=False,
    voucher=None,
):
    from apps.tenants.models import PaymentMethod

    end = start + dt.timedelta(minutes=facility.slot_minutes)
    m = facility.municipality
    if rules_version is None or rules_version.facility_id != facility.pk:
        raise BookingError(_("Debes aceptar as normas de uso vixentes."))
    participants = int(participants or 1)
    if not 1 <= participants <= max(1, facility.max_participants):
        raise BookingError(
            _("O número de persoas ten que estar entre 1 e %(n)s.")
            % {"n": facility.max_participants}
        )
    staff_channel = channel != Booking.Channel.ONLINE
    methods = facility.payment_method_list()
    if payment_method is None:
        payment_method = methods[0]
    elif payment_method not in methods and not staff_channel:
        raise BookingError(_("Esa forma de pagamento non está dispoñible nesta instalación."))
    # v5 · persoas doutros concellos da rede (ou sen vínculo co concello)
    origin = None
    guest = user is not None and not staff_channel and not linked_to(m, user)
    if guest:
        if not m.network_open:
            raise BookingError(
                _("%(c)s non admite agora reservas de persoas doutros concellos.") % {"c": m.name}
            )
        origin = network_origin(m, user)
    with transaction.atomic():
        Facility.objects.select_for_update().filter(pk=facility.pk).first()
        _validate_slot(facility, start, end, user=user if guest else None)
        if user is not None:
            active = (
                Booking.objects.filter(municipality=m, user=user, end__gt=timezone.now())
                .holding()
                .count()
            )
            limit = (
                min(m.max_active_bookings, m.network_max_active)
                if guest
                else (m.max_active_bookings)
            )
            if active >= limit:
                raise BookingError(
                    _("Xa tes o máximo de reservas activas permitidas neste concello.")
                )
        q = quote(facility, user, start, needs_light=needs_light, method=payment_method)
        if payment_method == PaymentMethod.VOUCHER:
            from .models import Voucher

            voucher = (
                Voucher.objects.select_for_update()
                .filter(pk=getattr(voucher, "pk", voucher))
                .first()
                if voucher
                else None
            )
            if (
                voucher is None
                or voucher.user_id != getattr(user, "pk", None)
                or not (voucher.usable_for(facility))
            ):
                raise BookingError(_("Non tes un bono válido para esta instalación."))
            voucher.uses_left -= 1
            if voucher.uses_left == 0:
                voucher.status = Voucher.Status.SPENT
            voucher.save(update_fields=["uses_left", "status"])
        else:
            voucher = None
        price = q.total_cents
        online_payment = price and payment_method == PaymentMethod.TPV
        booking = Booking.objects.create(
            municipality=m,
            facility=facility,
            user=user,
            start=start,
            end=end,
            channel=channel,
            created_by=created_by or user,
            holder_name=holder_name,
            holder_phone=holder_phone,
            tariff_audience=q.audience,
            price_cents=price,
            base_price_cents=q.base_cents,
            discount_pct=q.discount_pct,
            lighting_cents=q.lighting_cents,
            needs_light=q.light_on,
            participants=participants,
            participant_names=(participant_names or "")[:1000],
            payment_method=payment_method,
            voucher=voucher,
            network_origin=origin,
            status=Booking.Status.PENDING_PAYMENT if online_payment else Booking.Status.CONFIRMED,
            hold_expires_at=timezone.now()
            + dt.timedelta(minutes=settings.EIRA_PAYMENT_HOLD_MINUTES)
            if online_payment
            else None,
            rules_version=rules_version,
            rules_accepted_at=timezone.now(),
        )
    audit(
        "booking.create",
        created_by or user,
        m,
        booking,
        channel=channel,
        method=payment_method,
        network=bool(origin),
    )
    if booking.status != Booking.Status.PENDING_PAYMENT:
        _settle(booking)
    return booking


def _settle(booking, notify_person=True):
    """Seguinte estado despois de crear ou pagar: aprobación → pagamento na oficina → confirmada."""
    from apps.tenants.models import PaymentMethod

    if booking.facility.needs_approval and booking.approved_at is None:
        booking.status = Booking.Status.PENDING_APPROVAL
        booking.hold_expires_at = None
        booking.save(update_fields=["status", "hold_expires_at"])
        _notify_managers_pending(booking)
        if notify_person:
            notify(
                booking.user,
                _("Reserva pendente de aprobación: %(f)s") % {"f": booking.facility.name},
                _("O concello revisará a túa solicitude e avisarémoste da resposta."),
                url=_booking_url(booking),
                municipality=booking.municipality,
            )
        return booking
    if booking.payment_method == PaymentMethod.OFFICE and booking.outstanding_cents:
        deadline = timezone.now() + dt.timedelta(hours=booking.municipality.office_payment_hours)
        booking.status = Booking.Status.PENDING_OFFICE
        booking.hold_expires_at = min(deadline, booking.start)
        booking.save(update_fields=["status", "hold_expires_at"])
        if notify_person:
            notify(
                booking.user,
                _("Paga na oficina: %(f)s") % {"f": booking.facility.name},
                _("Gardámosche a franxa ata o %(d)s. Paga %(p)s € na oficina de deportes.")
                % {
                    "d": timezone.localtime(booking.hold_expires_at).strftime("%d/%m %H:%M"),
                    "p": f"{booking.outstanding_cents / 100:.2f}".replace(".", ","),
                },
                url=_booking_url(booking),
                municipality=booking.municipality,
                level="warning",
            )
        return booking
    booking.status = Booking.Status.CONFIRMED
    booking.hold_expires_at = None
    booking.save(update_fields=["status", "hold_expires_at"])
    _after_confirm(booking)
    return booking


def _booking_url(booking):
    from apps.tenants.urlutils import treverse

    return treverse(booking.municipality, "bookings:detail", booking.pk)


def _notify_managers_pending(booking, change=False):
    from apps.accounts.models import Membership, Role
    from apps.tenants.urlutils import treverse

    url = treverse(booking.municipality, "manage:booking", booking.pk)
    title = (_("Cambio para aprobar: %(f)s") if change else _("Reserva para aprobar: %(f)s")) % {
        "f": booking.facility.name
    }
    when = booking.requested_start if change else booking.start
    body = _("%(d)s ás %(h)s · %(n)s persoas · %(p)s") % {
        "d": timezone.localtime(when).strftime("%d/%m/%Y"),
        "h": timezone.localtime(when).strftime("%H:%M"),
        "n": booking.participants,
        "p": booking.holder_label or "—",
    }
    for ms in Membership.objects.filter(
        municipality=booking.municipality, role=Role.ADMIN
    ).select_related("user"):
        notify(ms.user, title, body, url=url, municipality=booking.municipality, level="warning")


def approve_booking(booking, by):
    """O concello aproba a reserva (ou o cambio pendente) e avisa á persoa."""
    if booking.requested_start:
        new_start = booking.requested_start
        booking.requested_start = None
        booking.save(update_fields=["requested_start"])
        modify_booking(booking, new_start, by=by, staff=True)
        booking.decided_by, booking.decision_reason = by, ""
        booking.save(update_fields=["decided_by", "decision_reason"])
        notify(
            booking.user,
            _("Cambio aprobado: %(f)s") % {"f": booking.facility.name},
            _("A túa reserva pasa ao %(d)s ás %(h)s.")
            % {
                "d": timezone.localtime(new_start).strftime("%d/%m/%Y"),
                "h": timezone.localtime(new_start).strftime("%H:%M"),
            },
            url=_booking_url(booking),
            municipality=booking.municipality,
            level="success",
        )
        audit("booking.change_approved", by, booking.municipality, booking)
        return booking
    if booking.status != Booking.Status.PENDING_APPROVAL:
        raise BookingError(_("Esta reserva non está pendente de aprobación."))
    booking.approved_at = timezone.now()
    booking.decided_by = by
    booking.save(update_fields=["approved_at", "decided_by"])
    audit("booking.approved", by, booking.municipality, booking)
    _settle(booking)
    return booking


def decline_booking(booking, by, reason):
    """Rexeita a reserva (ou o cambio) cun motivo. Se xa estaba pagada, devólvese íntegra."""
    reason = (reason or "").strip()
    if not reason:
        raise BookingError(_("Indica o motivo do rexeitamento."))
    if booking.requested_start:
        booking.requested_start = None
        booking.decided_by, booking.decision_reason = by, reason[:300]
        booking.save(update_fields=["requested_start", "decided_by", "decision_reason"])
        notify(
            booking.user,
            _("Cambio non aprobado: %(f)s") % {"f": booking.facility.name},
            _("A túa reserva segue como estaba. Motivo: %(m)s") % {"m": reason},
            url=_booking_url(booking),
            municipality=booking.municipality,
            level="warning",
        )
        audit("booking.change_declined", by, booking.municipality, booking, reason=reason)
        return booking, 0
    if booking.status != Booking.Status.PENDING_APPROVAL:
        raise BookingError(_("Esta reserva non está pendente de aprobación."))
    refund = 0
    if booking.paid_cents:
        from .payments import refund_booking

        refund = refund_booking(booking, booking.paid_cents - booking.refunded_cents)
    _restore_voucher(booking)
    booking.status = Booking.Status.DECLINED
    booking.decided_by, booking.decision_reason = by, reason[:300]
    booking.cancel_reason = reason[:200]
    booking.refunded_cents += refund
    booking.cancelled_at = timezone.now()
    booking.save(
        update_fields=[
            "status",
            "decided_by",
            "decision_reason",
            "cancel_reason",
            "refunded_cents",
            "cancelled_at",
        ]
    )
    body = _("Motivo: %(m)s") % {"m": reason}
    if refund:
        body += "\n" + _("Devolvémosche %(r)s € automaticamente.") % {
            "r": f"{refund / 100:.2f}".replace(".", ",")
        }
    notify(
        booking.user,
        _("Reserva non aprobada: %(f)s") % {"f": booking.facility.name},
        body,
        url=_booking_url(booking),
        municipality=booking.municipality,
        level="warning",
    )
    audit("booking.declined", by, booking.municipality, booking, reason=reason, refund=refund)
    return booking, refund


def _restore_voucher(booking):
    """Devolve o uso ao bono (cancelación a tempo ou rexeitamento)."""
    if not booking.voucher_id:
        return
    from .models import Voucher

    v = Voucher.objects.select_for_update().get(pk=booking.voucher_id)
    v.uses_left = min(v.uses_total, v.uses_left + 1)
    if v.status == Voucher.Status.SPENT and v.uses_left:
        v.status = Voucher.Status.ACTIVE
    v.save(update_fields=["uses_left", "status"])


def mark_paid(booking, payment_reference, amount_cents):
    """Pagamento aceptado (pasarela ou mostrador). Tamén cobra as pendentes na oficina e as
    aprazadas xa confirmadas."""
    paying = (Booking.Status.PENDING_PAYMENT, Booking.Status.PENDING_OFFICE)
    if booking.status not in paying:
        if booking.outstanding_cents and booking.status in (
            Booking.Status.CONFIRMED,
            Booking.Status.USED,
            Booking.Status.PENDING_APPROVAL,
        ):
            booking.paid_cents += amount_cents
            booking.payment_reference = payment_reference
            booking.save(update_fields=["paid_cents", "payment_reference"])
            audit("booking.paid", booking.user, booking.municipality, booking, amount=amount_cents)
        return booking
    if amount_cents < booking.price_cents - booking.paid_cents:
        raise BookingError(_("Importe pagado insuficiente."))
    booking.paid_cents += amount_cents
    booking.payment_reference = payment_reference
    booking.hold_expires_at = None
    booking.save(update_fields=["paid_cents", "payment_reference", "hold_expires_at"])
    audit("booking.paid", booking.user, booking.municipality, booking, amount=amount_cents)
    _settle(booking)
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
    if booking.status not in Booking.OPEN_STATUSES:
        raise BookingError(_("Esta reserva xa non se pode cancelar."))
    if not force_full_refund and booking.start <= timezone.now():
        raise BookingError(_("A reserva xa comezou."))
    penalty = 0 if force_full_refund else booking.penalty_if_cancelled_now()
    refund = max(0, booking.paid_cents - penalty)
    if refund:
        from .payments import refund_booking

        refund_booking(booking, refund)
    # Bono: o uso devólvese se se cancela a tempo (como a devolución do importe)
    if booking.voucher_id and (force_full_refund or timezone.now() < booking.cancellation_cutoff()):
        _restore_voucher(booking)
    if booking.status in (Booking.Status.PENDING_PAYMENT, Booking.Status.PENDING_OFFICE):
        from .models import Payment

        booking.payments.filter(status=Payment.Status.PENDING).update(
            status=Payment.Status.EXPIRED, resolved_at=timezone.now()
        )
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


def modify_booking(booking, new_start, by=None, staff=False):
    if not booking.can_modify():
        raise BookingError(_("Xa non se pode modificar esta reserva (prazo superado)."))
    facility = booking.facility
    new_end = new_start + dt.timedelta(minutes=facility.slot_minutes)
    if facility.needs_approval and not staff:
        # v5: nas instalacións con aprobación, o cambio queda pendente ata que o concello o aprobe
        _validate_slot(facility, new_start, new_end, exclude=booking)
        booking.requested_start = new_start
        booking.save(update_fields=["requested_start"])
        audit(
            "booking.change_requested", by, booking.municipality, booking, new=new_start.isoformat()
        )
        _notify_managers_pending(booking, change=True)
        return booking
    with transaction.atomic():
        Facility.objects.select_for_update().filter(pk=facility.pk).first()
        _validate_slot(facility, new_start, new_end, exclude=booking)
        old = booking.start
        booking.start, booking.end = new_start, new_end
        fields = ["start", "end"]
        if facility.lighting_supplement_cents and not booking.needs_light:
            # O suplemento non se recalcula ao cambiar de hora; se a nova franxa precisa luz,
            # acéndese igual (DECISIONS v5).
            from .lighting import slot_needs_light

            booking.needs_light = slot_needs_light(facility, new_start, new_end)
            fields.append("needs_light")
        booking.save(update_fields=fields)
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


def submit_closing_checklist(
    booking, door_ok, key_ok, all_ok, notes="", by=None, needs_cleaning=False
):
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
    if needs_cleaning:
        # v1.1: etiqueta «limpeza» ao saír → incidencia de limpeza (tarefa para o persoal)
        cleaning_incident = Incident.objects.create(
            municipality=booking.municipality,
            facility=booking.facility,
            reporter=booking.user,
            booking=booking,
            category=Incident.Category.CLEANING,
            source=Incident.Source.CHECKLIST,
            description=str(_("Ao saír: fai falta limpeza."))
            + (f"\n{notes}" if notes and not problems else ""),
        )
        from apps.incidents.services import notify_staff_new_incident

        notify_staff_new_incident(cleaning_incident)
        incident = incident or cleaning_incident
    return incident


def submit_start_state(booking, ok, notes="", photo=None, by=None, cleaning=False):
    """v5 · D: estado da pista e do material ao entrar.

    Se hai un problema, créase unha incidencia **atribuída a antes desta reserva**
    (`prior_to_booking`), para que non se lle culpe a quen a detectou."""
    from apps.incidents.models import Incident

    booking.start_state_at = timezone.now()
    booking.start_state_ok = bool(ok)
    booking.start_state_notes = (notes or "")[:500]
    fields = ["start_state_at", "start_state_ok", "start_state_notes"]
    if photo:
        booking.start_state_photo = photo
        fields.append("start_state_photo")
    booking.save(update_fields=fields)
    audit("booking.start_state", by, booking.municipality, booking, ok=bool(ok))
    if ok:
        return None
    previous = (
        Booking.objects.filter(
            facility=booking.facility,
            end__lte=booking.start,
            status__in=[Booking.Status.USED, Booking.Status.CONFIRMED],
        )
        .order_by("-end")
        .first()
    )
    text = _("Ao comezar a reserva %(r)s, a persoa atopou un problema que xa estaba antes.") % {
        "r": booking.reference
    }
    if previous:
        text += " " + _("Última reserva anterior: %(r)s (%(d)s).") % {
            "r": previous.reference,
            "d": timezone.localtime(previous.end).strftime("%d/%m %H:%M"),
        }
    incident = Incident.objects.create(
        municipality=booking.municipality,
        facility=booking.facility,
        reporter=booking.user,
        prior_to_booking=booking,
        category=Incident.Category.CLEANING if cleaning else Incident.Category.DAMAGE,
        source=Incident.Source.START_STATE,
        description="\n\n".join(p for p in ((notes or "").strip(), text) if p),
        photo=booking.start_state_photo.name if booking.start_state_photo else "",
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
    from .payments import expire_pending

    return expire_pending(now)


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
