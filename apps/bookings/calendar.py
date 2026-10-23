# SPDX-License-Identifier: EUPL-1.2
"""Axenda do concello en calendario (semana e mes), con filtro de instalacións e exportación .ics.

Eventos que se amosan, cada un co seu estado (cor e texto):
- reservas: «pagada», «reservada» (sen cobrar ou gratuíta) e «pendente de pago»;
- peches e bloqueos da instalación: «pechada»;
- sesións das escolas municipais: «actividade municipal» (calculadas cos días e a hora do grupo).
As canceladas, rexeitadas e caducadas non ocupan a axenda.
"""

import datetime as dt
from collections import Counter, defaultdict

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.activities.models import Group
from apps.facilities.models import Closure

from .models import Booking

STATES = {
    "paid": _("Pagada"),
    "reserved": _("Reservada"),
    "pending": _("Pendente de pago"),
    "closed": _("Pechada"),
    "activity": _("Actividade municipal"),
}
SHOWN = [
    Booking.Status.CONFIRMED,
    Booking.Status.USED,
    Booking.Status.NO_SHOW,
    Booking.Status.PENDING_PAYMENT,
]


def _aware(day, time=dt.time.min):
    return timezone.make_aware(dt.datetime.combine(day, time))


def booking_state(b):
    if b.status == Booking.Status.PENDING_PAYMENT:
        return "pending"
    if b.price_cents and b.paid_cents >= b.price_cents:
        return "paid"
    return "reserved"


def events(tenant, facilities, first_day, days):
    """Eventos entre `first_day` e `first_day + days` para as instalacións indicadas."""
    start, end = _aware(first_day), _aware(first_day + dt.timedelta(days=days))
    fac_ids = {f.pk for f in facilities}
    out = []
    for b in (
        Booking.objects.for_tenant(tenant)
        .filter(facility_id__in=fac_ids, start__lt=end, end__gt=start, status__in=SHOWN)
        .select_related("facility", "user")
        .order_by("start")
    ):
        out.append(
            {
                "kind": "booking",
                "state": booking_state(b),
                "start": timezone.localtime(b.start),
                "end": timezone.localtime(b.end),
                "facility": b.facility,
                "title": b.holder_label or b.reference,
                "obj": b,
            }
        )
    for c in (
        Closure.objects.for_tenant(tenant)
        .filter(starts_at__lt=end, ends_at__gt=start)
        .select_related("facility")
    ):
        targets = [c.facility] if c.facility_id else list(facilities)
        for f in targets:
            if f.pk in fac_ids:
                out.append(
                    {
                        "kind": "closure",
                        "state": "closed",
                        "start": max(timezone.localtime(c.starts_at), timezone.localtime(start)),
                        "end": min(timezone.localtime(c.ends_at), timezone.localtime(end)),
                        "facility": f,
                        "title": c.reason,
                        "obj": c,
                    }
                )
    for g in (
        Group.objects.for_tenant(tenant)
        .filter(facility_id__in=fac_ids)
        .select_related("activity", "facility")
    ):
        weekdays = set(g.weekday_list())
        for i in range(days):
            day = first_day + dt.timedelta(days=i)
            if day.weekday() in weekdays:
                s = timezone.localtime(_aware(day, g.start_time))
                out.append(
                    {
                        "kind": "activity",
                        "state": "activity",
                        "start": s,
                        "end": s + dt.timedelta(minutes=g.duration_minutes),
                        "facility": g.facility,
                        "title": f"{g.activity.name} · {g.name}",
                        "obj": g,
                    }
                )
    out.sort(key=lambda e: (e["start"], e["facility"].name))
    return out


def _grouped(cell):
    """Nunha cela, as reservas da mesma instalación, hora e estado van nunha soa ficha con contador
    (instalacións compartidas: ximnasio, piscina)."""
    out, seen = [], {}
    for e in cell:
        if e["kind"] != "booking":
            out.append(e)
            continue
        key = (e["facility"].pk, e["start"], e["state"])
        if key in seen:
            seen[key]["count"] += 1
            continue
        item = {**e, "count": 1}
        seen[key] = item
        out.append(item)
    return out


def week_grid(evts, monday):
    """Columnas: os 7 días; filas: horas (da primeira á última con eventos)."""
    days = [monday + dt.timedelta(days=i) for i in range(7)]
    by_cell = defaultdict(list)
    for e in evts:
        by_cell[(e["start"].date(), e["start"].hour)].append(e)
    hours = sorted({h for (_d, h) in by_cell}) or list(range(9, 22))
    hours = list(range(min(hours), max(hours) + 1))
    rows = [
        {
            "hour": h,
            "cells": [{"day": d, "events": _grouped(by_cell.get((d, h), []))} for d in days],
        }
        for h in hours
    ]
    return {"days": days, "rows": rows}


def month_grid(evts, first_day):
    """Semanas (luns–domingo) do mes; cada día co reconto de eventos por estado."""
    month = first_day.month
    start = first_day - dt.timedelta(days=first_day.weekday())
    counts = defaultdict(Counter)
    for e in evts:
        counts[e["start"].date()][e["state"]] += 1
    weeks = []
    day = start
    while True:
        week = []
        for _i in range(7):
            c = counts.get(day, Counter())
            week.append(
                {
                    "day": day,
                    "in_month": day.month == month,
                    "counts": [(k, STATES[k], c[k]) for k in STATES if c[k]],
                    "total": sum(c.values()),
                }
            )
            day += dt.timedelta(days=1)
        weeks.append({"monday": week[0]["day"], "days": week})
        if day.month != month and day > first_day:
            break
    return weeks


def ics(evts, name):
    """Calendario .ics dos eventos filtrados (sen datos persoais: instalación, estado e referencia)."""

    def fmt(d):
        return d.astimezone(dt.UTC).strftime("%Y%m%dT%H%M%SZ")

    def esc(text):
        return (
            str(text)
            .replace("\\", "\\\\")
            .replace(";", r"\;")
            .replace(",", r"\,")
            .replace("\n", r"\n")
        )

    now = fmt(timezone.now())
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Eira//Axenda do concello//GL",
        f"X-WR-CALNAME:{esc(name)}",
    ]
    for i, e in enumerate(evts):
        ref = (
            getattr(e["obj"], "reference", "")
            or f"{e['kind']}-{getattr(e['obj'], 'pk', i)}-{e['start']:%Y%m%d%H%M}"
        )
        summary = f"{e['facility'].name} · {STATES[e['state']]}"
        if e["kind"] != "booking":
            summary += f" · {e['title']}"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{esc(ref)}@eira",
            f"DTSTAMP:{now}",
            f"DTSTART:{fmt(e['start'])}",
            f"DTEND:{fmt(e['end'])}",
            f"SUMMARY:{esc(summary)}",
            f"LOCATION:{esc(e['facility'].name)}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
