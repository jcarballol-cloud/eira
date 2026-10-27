# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · D: rendemento de cada instalación. Fórmulas en docs/rendemento-instalacions.md.

- Ocupación: horas reservadas ÷ horas dispoñibles (× prazas nas de uso compartido) e uso real
  (só as reservas con entrada rexistrada).
- Consumo **estimado** (kWh) a partir do inventario de equipos, os horarios reais de apertura,
  as reservas que se usaron, os suplementos de luz e o tempo continuo. Coste (€/kWh) e CO₂
  (kg/kWh) configurables por concello. Sempre «estimación orientativa».
- Perfil de persoas usuarias só agregado e con n ≥ 10."""

import datetime as dt
from decimal import Decimal

from django.db.models import Q, prefetch_related_objects
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import opening_intervals
from apps.facilities.models import Equipment

MIN_N = 10
AGE_BANDS = (
    (0, 17, "0–17"),
    (18, 34, "18–34"),
    (35, 54, "35–54"),
    (55, 64, "55–64"),
    (65, 200, "65+"),
)
# Reservas que contan como uso (o equipo «só con reserva» acéndese): usadas, ou confirmadas
# no nivel 0 (alí o QR é voluntario). As non presentadas non acenden nada.
NOT_USED = (Booking.Status.NO_SHOW,)


def _hours(seconds):
    return seconds / 3600


def _union_seconds(intervals):
    total, cur_s, cur_e = 0, None, None
    for s, e in sorted(intervals):
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += (cur_e - cur_s).total_seconds()
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += (cur_e - cur_s).total_seconds()
    return total


def available_seconds(facility, start_day, end_day):
    """Segundos de apertura reais entre dúas datas [start_day, end_day), sen os peches."""
    from apps.facilities.models import Closure

    if "opening_hours" not in getattr(facility, "_prefetched_objects_cache", {}):
        prefetch_related_objects([facility], "opening_hours")  # unha consulta, non unha por día
    closures = list(
        Closure.objects.filter(
            Q(facility=facility) | Q(facility__isnull=True),
            municipality=facility.municipality,
            starts_at__lt=_aware(end_day),
            ends_at__gt=_aware(start_day),
        ).values_list("starts_at", "ends_at")
    )
    total = 0
    day = start_day
    while day < end_day:
        for opens, closes in opening_intervals(facility, day):
            secs = (closes - opens).total_seconds()
            for c_start, c_end in closures:
                overlap = (min(closes, c_end) - max(opens, c_start)).total_seconds()
                secs -= max(0, overlap)
            total += max(0, secs)
        day += dt.timedelta(days=1)
    return total


def _bookings(facility, start, end):
    return Booking.objects.filter(
        facility=facility,
        start__gte=start,
        start__lt=end,
        status__in=[Booking.Status.CONFIRMED, Booking.Status.USED, Booking.Status.NO_SHOW],
    ).select_related("user")


def _aware(day):
    return timezone.make_aware(dt.datetime.combine(day, dt.time()))


def period_stats(facility, start_day, end_day, *, bookings=None):
    """Indicadores dun período [start_day, end_day). Ver docs/rendemento-instalacions.md."""
    m = facility.municipality
    start, end = _aware(start_day), _aware(end_day)
    rows = list(bookings if bookings is not None else _bookings(facility, start, end))
    avail = available_seconds(facility, start_day, end_day)
    booked = sum((b.end - b.start).total_seconds() for b in rows)
    used_rows = [b for b in rows if b.checked_in_at is not None and b.status == Booking.Status.USED]
    used = sum((b.end - b.start).total_seconds() for b in used_rows)
    on_rows = [
        b
        for b in rows
        if b.status not in NOT_USED
        and (b.checked_in_at is not None or facility.access_level == 0)
        and b.start < timezone.now()
    ]
    on_union = _union_seconds([(b.start, b.end) for b in on_rows])
    lit_union = _union_seconds(
        [(b.start, b.end) for b in on_rows if b.needs_light or b.lighting_cents]
    )
    days = (end_day - start_day).days
    hours_by_mode = {
        Equipment.Mode.OPENING: _hours(avail),
        Equipment.Mode.BOOKING: _hours(on_union),
        Equipment.Mode.LIGHT: _hours(lit_union),
        Equipment.Mode.CONTINUOUS: 24.0 * days,
    }
    kwh = Decimal("0")
    by_kind = {}
    for eq in facility.energy_equipment.all():
        part = eq.power_kw * eq.use_factor * Decimal(str(round(hours_by_mode[eq.mode], 3)))
        kwh += part
        by_kind[eq.get_kind_display()] = by_kind.get(eq.get_kind_display(), Decimal("0")) + part
    capacity = max(1, facility.capacity)
    use_minutes = [(b.end - max(b.start, b.checked_in_at)).total_seconds() / 60 for b in used_rows]
    used_h = _hours(used)
    cost = kwh * m.energy_price_eur_kwh
    return {
        "start": start_day,
        "end": end_day,
        "available_h": round(_hours(avail), 1),
        "booked_h": round(_hours(booked), 1),
        "used_h": round(used_h, 1),
        "occupancy_pct": round(100 * booked / (avail * capacity)) if avail else 0,
        "real_use_pct": round(100 * used / (avail * capacity)) if avail else 0,
        "avg_use_min": round(sum(use_minutes) / len(use_minutes)) if use_minutes else None,
        "uses": len(used_rows),
        "kwh": round(kwh, 1),
        "kwh_by_kind": {k: round(v, 1) for k, v in by_kind.items()},
        "cost_eur": round(cost, 2),
        "co2_kg": round(kwh * m.co2_kg_kwh, 1),
        "kwh_per_use_h": round(kwh / Decimal(str(used_h)), 2) if used_h else None,
        "eur_per_use_h": round(cost / Decimal(str(used_h)), 2) if used_h else None,
        "has_equipment": bool(by_kind),
    }


def profile(facility, start_day, end_day):
    """Perfil agregado das persoas usuarias (idade, empadroamento, rede). Só con n ≥ 10."""
    rows = _bookings(facility, _aware(start_day), _aware(end_day)).filter(
        user__isnull=False, status=Booking.Status.USED
    )
    people = {}
    for b in rows:
        people.setdefault(b.user_id, b)
    n = len(people)
    if n < MIN_N:
        return {"n": n, "enough": False}
    year = timezone.localdate().year
    bands = {label: 0 for _a, _b, label in AGE_BANDS}
    unknown = 0
    resident = sum(
        1 for b in people.values() if b.tariff_audience in ("resident", "youth", "senior")
    )
    network = sum(1 for b in people.values() if b.network_origin_id)
    for b in people.values():
        by = b.user.birth_year
        if not by:
            unknown += 1
            continue
        age = year - by
        for lo, hi, label in AGE_BANDS:
            if lo <= age <= hi:
                bands[label] += 1
    return {
        "n": n,
        "enough": True,
        "bands": [{"label": k, "pct": round(100 * v / n)} for k, v in bands.items()],
        "unknown_pct": round(100 * unknown / n),
        "resident_pct": round(100 * resident / n),
        "network_pct": round(100 * network / n),
    }


def _month_start(day, back=0):
    """Primeiro día do mes `back` meses atrás (negativo = meses adiante)."""
    index = day.year * 12 + (day.month - 1) - back
    return dt.date(index // 12, index % 12 + 1, 1)


def monthly_trend(facility, months=12, today=None):
    today = today or timezone.localdate()
    # Desde o primeiro mes con reservas (mínimo 3 meses), para non encher a gráfica de ceros
    first = (
        Booking.objects.filter(facility=facility)
        .order_by("start")
        .values_list("start", flat=True)
        .first()
    )
    if first is not None:
        f = timezone.localdate(first)
        span = (today.year - f.year) * 12 + today.month - f.month + 1
        months = max(3, min(months, span))
    out = []
    for back in range(months - 1, -1, -1):
        first = _month_start(today, back)
        nxt = _month_start(first, -1)
        end = min(nxt, today + dt.timedelta(days=1))
        s = period_stats(facility, first, end)
        out.append({"month": first, **s})
    return out


def readings_vs_estimate(facility):
    out = []
    for r in facility.energy_readings.all():
        est = period_stats(facility, r.period_start, r.period_end + dt.timedelta(days=1))["kwh"]
        diff = round(100 * (est - r.kwh) / r.kwh) if r.kwh else None
        out.append({"reading": r, "estimate": est, "diff_pct": diff})
    return out


def facility_panel(facility, today=None):
    today = today or timezone.localdate()
    tomorrow = today + dt.timedelta(days=1)
    return {
        "week": period_stats(facility, today - dt.timedelta(days=6), tomorrow),
        "month": period_stats(facility, today - dt.timedelta(days=29), tomorrow),
        "year": period_stats(facility, today - dt.timedelta(days=364), tomorrow),
        "profile": profile(facility, today - dt.timedelta(days=364), tomorrow),
        "trend": monthly_trend(facility, today=today),
        "readings": readings_vs_estimate(facility),
    }


def municipality_summary(municipality, days=30, today=None):
    """Agregado do concello para a comparativa da deputación (sen datos persoais)."""
    from apps.facilities.models import Facility

    today = today or timezone.localdate()
    start, end = today - dt.timedelta(days=days - 1), today + dt.timedelta(days=1)
    totals = {
        "available_h": 0,
        "booked_h": 0,
        "used_h": 0,
        "kwh": Decimal("0"),
        "cost_eur": Decimal("0"),
    }
    weighted_avail = 0
    for f in Facility.objects.filter(municipality=municipality, is_published=True).prefetch_related(
        "energy_equipment"
    ):
        s = period_stats(f, start, end)
        cap = max(1, f.capacity)
        weighted_avail += s["available_h"] * cap
        for k in totals:
            totals[k] += s[k] if not isinstance(totals[k], Decimal) else Decimal(str(s[k]))
    return {
        "occupancy_pct": round(100 * totals["booked_h"] / weighted_avail) if weighted_avail else 0,
        "real_use_pct": round(100 * totals["used_h"] / weighted_avail) if weighted_avail else 0,
        "kwh": round(totals["kwh"]),
        "cost_eur": round(totals["cost_eur"]),
        "kwh_per_use_h": round(totals["kwh"] / Decimal(str(totals["used_h"])), 2)
        if totals["used_h"]
        else None,
    }
