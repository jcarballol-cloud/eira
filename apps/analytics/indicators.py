# SPDX-License-Identifier: EUPL-1.2
"""Indicadores básicos do concello. Todo se calcula ao voo a partir das reservas (sen datos persoais)."""

import datetime as dt
from collections import Counter, defaultdict

from django.db.models import Count, Sum
from django.utils import timezone
from django.utils.formats import number_format
from django.utils.translation import gettext as _

from apps.bookings.models import Booking
from apps.bookings.services import closures_overlapping, slot_starts
from apps.facilities.models import Facility
from apps.incidents.models import Incident

USED = [Booking.Status.CONFIRMED, Booking.Status.USED, Booking.Status.NO_SHOW]


def period(weeks=4, today=None):
    today = today or timezone.localdate()
    end = today
    start = end - dt.timedelta(weeks=weeks)
    return start, end


def _aware(day):
    return timezone.make_aware(dt.datetime.combine(day, dt.time.min))


def available_slots(facility, start, end):
    """Prazas-franxa ofertadas no período (descontando peches)."""
    total = 0
    day = start
    step = dt.timedelta(minutes=facility.slot_minutes)
    closures = list(closures_overlapping(facility, _aware(start), _aware(end)))
    while day < end:
        for s in slot_starts(facility, day):
            if not any(c.starts_at < s + step and c.ends_at > s for c in closures):
                total += facility.capacity
        day += dt.timedelta(days=1)
    return total


def occupancy_by_facility(tenant, start, end):
    facilities = Facility.objects.for_tenant(tenant).prefetch_related("opening_hours")
    counts = dict(
        Booking.objects.for_tenant(tenant)
        .filter(start__gte=_aware(start), start__lt=_aware(end), status__in=USED)
        .values_list("facility")
        .annotate(n=Count("id"))
    )
    no_shows = dict(
        Booking.objects.for_tenant(tenant)
        .filter(start__gte=_aware(start), start__lt=_aware(end), status=Booking.Status.NO_SHOW)
        .values_list("facility")
        .annotate(n=Count("id"))
    )
    rows = []
    for f in facilities:
        avail = available_slots(f, start, end)
        booked = counts.get(f.pk, 0)
        rows.append(
            {
                "facility": f.name,
                "facility_id": f.pk,
                "available": avail,
                "booked": booked,
                "pct": round(100 * booked / avail) if avail else 0,
                "no_shows": no_shows.get(f.pk, 0),
                "no_show_pct": round(100 * no_shows.get(f.pk, 0) / booked) if booked else 0,
            }
        )
    return sorted(rows, key=lambda r: -r["pct"])


def occupancy_heatmap(tenant, start, end):
    """Matriz día da semana × hora con reservas por franxa (todas as instalacións)."""
    counter = Counter()
    for s in (
        Booking.objects.for_tenant(tenant)
        .filter(start__gte=_aware(start), start__lt=_aware(end), status__in=USED)
        .values_list("start", flat=True)
    ):
        local = timezone.localtime(s)
        counter[(local.weekday(), local.hour)] += 1
    hours = sorted({h for _d, h in counter} | set(range(9, 22)))
    peak = max(counter.values(), default=0)
    matrix = []
    for h in hours:
        cells = []
        for d in range(7):
            v = counter.get((d, h), 0)
            level = 0 if not v else min(4, 1 + int(3 * v / peak)) if peak else 0
            cells.append({"value": v, "level": level})
        matrix.append({"hour": h, "cells": cells})
    return matrix


def underused(rows, threshold=20):
    return [r for r in rows if r["pct"] < threshold and r["available"]]


def incidents_summary(tenant, start, end):
    qs = Incident.objects.for_tenant(tenant).filter(
        created_at__gte=_aware(start), created_at__lt=_aware(end) + dt.timedelta(days=1)
    )
    by_status = dict(qs.values_list("status").annotate(n=Count("id")))
    by_category = dict(qs.values_list("category").annotate(n=Count("id")))
    resolved = qs.filter(resolved_at__isnull=False)
    durations = [(i.resolved_at - i.created_at).total_seconds() / 3600 for i in resolved]
    return {
        "total": qs.count(),
        "open": Incident.objects.for_tenant(tenant)
        .exclude(status__in=[Incident.Status.RESOLVED, Incident.Status.REJECTED])
        .count(),
        "by_status": [(label, by_status.get(value, 0)) for value, label in Incident.Status.choices],
        "by_category": [
            (label, by_category.get(value, 0))
            for value, label in Incident.Category.choices
            if by_category.get(value)
        ],
        "avg_hours": round(sum(durations) / len(durations), 1) if durations else None,
    }


def revenue_by_week(tenant, start, end):
    rows = defaultdict(lambda: {"paid": 0, "refunded": 0})
    for created, paid, refunded in (
        Booking.objects.for_tenant(tenant)
        .filter(created_at__gte=_aware(start), created_at__lt=_aware(end) + dt.timedelta(days=1))
        .values_list("created_at", "paid_cents", "refunded_cents")
    ):
        local = timezone.localtime(created).date()
        monday = local - dt.timedelta(days=local.weekday())
        rows[monday]["paid"] += paid
        rows[monday]["refunded"] += refunded
    return [
        {"week": k, "paid": v["paid"], "refunded": v["refunded"], "net": v["paid"] - v["refunded"]}
        for k, v in sorted(rows.items())
    ]


def summary(tenant, weeks=4, today=None):
    start, end = period(weeks, today)
    occ = occupancy_by_facility(tenant, start, end)
    booked = sum(r["booked"] for r in occ)
    avail = sum(r["available"] for r in occ)
    revenue = (
        Booking.objects.for_tenant(tenant)
        .filter(created_at__gte=_aware(start), created_at__lt=_aware(end) + dt.timedelta(days=1))
        .aggregate(p=Sum("paid_cents"), r=Sum("refunded_cents"))
    )
    return {
        "start": start,
        "end": end,
        "occupancy": occ,
        "booked": booked,
        "available": avail,
        "occupancy_pct": round(100 * booked / avail) if avail else 0,
        "no_shows": sum(r["no_shows"] for r in occ),
        "no_show_pct": round(100 * sum(r["no_shows"] for r in occ) / booked) if booked else 0,
        "underused": underused(occ),
        "incidents": incidents_summary(tenant, start, end),
        "revenue_cents": (revenue["p"] or 0) - (revenue["r"] or 0),
        "revenue_weeks": revenue_by_week(tenant, start, end),
        "heatmap": occupancy_heatmap(tenant, start, end),
    }


PERCENT = "percent"  # porcentaxes: sempre de 0 a 100
SERIES_MAX = "max"  # valores absolutos: relativos ao máximo da serie (indícase visiblemente)


def hbar(items, value_key, label_key, suffix="", scale=SERIES_MAX, maximum=None):
    """Datos dun gráfico de barras horizontal en HTML (escala co texto; sen JS nin estilos en liña).

    v4: a escala xa non é sempre o máximo da serie (iso facía que 23 % enchese a barra):
    - scale="percent": 0–100, o ancho é o propio valor;
    - maximum=N: escala fixa 0–N (p. ex. satisfacción 0–100);
    - por defecto, o máximo da serie, e o gráfico di cal é ese máximo.
    """
    values = [max(i[value_key] or 0, 0) for i in items]
    if scale == PERCENT:
        top = 100
    elif maximum is not None:
        top = maximum
    else:
        top = max(values, default=0) or 1
    bars = [
        {
            "label": item[label_key],
            "value": item[value_key],
            "pct": min(100, 100 * v / top),
            "display": f"{number_format(item[value_key])}{suffix}",
        }
        for item, v in zip(items, values, strict=True)
    ]
    chart = {
        "bars": bars,
        "scale": PERCENT if scale == PERCENT else ("fixed" if maximum is not None else SERIES_MAX),
    }
    # «/100» non se repite na escala («de 0 a 100», non «de 0 a 100/100»)
    chart["top_display"] = f"{number_format(top)}{'' if suffix.startswith('/') else suffix}"
    return chart


def ai_aggregates(tenant):
    """Agregados (sen datos persoais) para o resumo semanal do asistente IA."""
    s = summary(tenant, weeks=1)
    top = s["occupancy"][0]["facility"] if s["occupancy"] and s["occupancy"][0]["booked"] else None
    return {
        "bookings": s["booked"],
        "occupancy_pct": s["occupancy_pct"],
        "no_shows": s["no_shows"],
        "top_facility": top,
        "underused": [r["facility"] for r in s["underused"]][:3],
        "open_incidents": s["incidents"]["open"],
        "period": f"{s['start']}/{s['end']}",
        "label": _("semana"),
    }
