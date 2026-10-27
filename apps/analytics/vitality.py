# SPDX-License-Identifier: EUPL-1.2
"""v5 · Índice de vida activa (0–100) por instalación.

Combina datos que xa existen; non recolle nada novo. Fórmula, pesos e limiares en
docs/indice-vida-activa.md. Os compoñentes con datos de persoas só se calculan con n ≥ 10
(o mesmo umbral ca o observatorio); se non, quedan como «sen datos suficientes».

Compoñentes (0–100 cada un):
- occupancy: uso real rexistrado (reservas usadas, con entrada) fronte ás prazas ofertadas nas
  últimas 8 semanas. Un 60 % de uso real xa puntúa 100.
- diversity: diversidade de idades de quen usou a instalación (5 franxas, entropía de Shannon
  normalizada). Só agregados; nunca se garda nin se mostra quen.
- satisfaction: «Que tal foi?» dos últimos 90 días (ben = 100, regular = 50, mal = 0).
- accessibility: elementos de accesibilidade física declarados (de 7).
- maintenance: días desde a última supervisión (última orde pechada): ≤ 30 días = 100,
  baixa ata 0 aos 180; −20 se hai ordes atrasadas.
"""

import datetime as dt
import math

from django.db.models import Count
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

MIN_N = 10
WEEKS = 8
FULL_OCCUPANCY_PCT = 60
COMPONENTS = {
    "occupancy": _("Ocupación real"),
    "diversity": _("Diversidade de idades"),
    "satisfaction": _("Satisfacción"),
    "accessibility": _("Accesibilidade física"),
    "maintenance": _("Mantemento ao día"),
}
PEOPLE_COMPONENTS = ("occupancy", "diversity", "satisfaction")
DEFAULT_WEIGHTS = {
    "occupancy": 30,
    "diversity": 15,
    "satisfaction": 25,
    "accessibility": 15,
    "maintenance": 15,
}
AGE_BANDS = ((0, 17), (18, 34), (35, 54), (55, 64), (65, 200))


def weights_for(municipality):
    custom = municipality.vitality_weights or {}
    return {k: int(custom.get(k, v)) for k, v in DEFAULT_WEIGHTS.items()}


def _occupancy(facility, start, end):
    from apps.bookings.models import Booking

    from .indicators import available_slots

    used = Booking.objects.filter(
        facility=facility,
        start__gte=timezone.make_aware(dt.datetime.combine(start, dt.time.min)),
        start__lt=timezone.make_aware(dt.datetime.combine(end, dt.time.min)),
        status=Booking.Status.USED,
    ).count()
    if used < MIN_N:
        return None, used
    avail = available_slots(facility, start, end)
    if not avail:
        return None, used
    pct = 100 * used / avail
    return min(100, round(pct * 100 / FULL_OCCUPANCY_PCT)), used


def _diversity(facility, start, end):
    from apps.bookings.models import Booking

    year = timezone.localdate().year
    # Unha fila por persoa distinta (conta) co seu ano de nacemento; só se conta, non se garda
    ages = (
        Booking.objects.filter(
            facility=facility,
            status=Booking.Status.USED,
            start__date__gte=start,
            start__date__lt=end,
            user__birth_year__isnull=False,
        )
        .values("user", "user__birth_year")
        .distinct()
    )
    counts = [0] * len(AGE_BANDS)
    for row in ages:
        age = year - row["user__birth_year"]
        for i, (lo, hi) in enumerate(AGE_BANDS):
            if lo <= age <= hi:
                counts[i] += 1
                break
    people = sum(counts)
    if people < MIN_N:
        return None, people
    entropy = -sum((c / people) * math.log(c / people) for c in counts if c)
    return round(100 * entropy / math.log(len(AGE_BANDS))), people


def _satisfaction(facility, today):
    from apps.bookings.models import Rating
    from apps.bookings.ratings import SCORE_VALUE

    since = timezone.now() - dt.timedelta(days=90)
    rows = dict(
        Rating.objects.filter(facility=facility, created_at__gte=since)
        .values_list("score")
        .annotate(n=Count("id"))
    )
    n = sum(rows.values())
    if n < MIN_N:
        return None, n
    return round(sum(SCORE_VALUE[s] * c for s, c in rows.items()) / n), n


DETAIL_SCORE = {"yes": 1.0, "partial": 0.5, "no": 0.0}


def _accessibility(facility):
    """v1.2: accesibilidade detallada (si = 1, parcial = 0,5, non ou sen datos = 0) ÷ 7.

    Se a instalación aínda non ten ningún punto detallado, úsase a lista básica (v5)."""
    if facility.has_accessibility_detail():
        points = facility.accessibility_points()
        return round(100 * sum(DETAIL_SCORE.get(p["value"], 0) for p in points) / len(points))
    total = len(facility.ACCESSIBILITY)
    return round(100 * len(facility.accessibility_features()) / total)


def _maintenance(facility, today):
    from apps.maintenance.models import WorkOrder

    last = facility.last_supervision()
    if last is None:
        score = 0
    else:
        days = (today - timezone.localdate(last)).days
        score = 100 if days <= 30 else max(0, round(100 * (180 - days) / 150))
    overdue = (
        WorkOrder.objects.filter(facility=facility, due_date__lt=today)
        .exclude(status=WorkOrder.Status.DONE)
        .exists()
    )
    score = max(0, score - 20) if overdue else score
    # v1.1: unha zona de limpeza atrasada tamén resta (parte de «mantemento ao día»)
    from apps.maintenance.cleaning import overdue_zones

    if overdue_zones(facility.municipality, facility=facility):
        score = max(0, score - 10)
    return score


def facility_index(facility, today=None):
    """{"value": 0–100 | None, "components": {clave: {"value", "n", "weight", "label"}}}."""
    today = today or timezone.localdate()
    start = today - dt.timedelta(weeks=WEEKS)
    weights = weights_for(facility.municipality)
    occ, occ_n = _occupancy(facility, start, today)
    div, div_n = _diversity(facility, start, today)
    sat, sat_n = _satisfaction(facility, today)
    values = {
        "occupancy": (occ, occ_n),
        "diversity": (div, div_n),
        "satisfaction": (sat, sat_n),
        "accessibility": (_accessibility(facility), None),
        "maintenance": (_maintenance(facility, today), None),
    }
    components = {
        k: {"value": v, "n": n, "weight": weights[k], "label": COMPONENTS[k]}
        for k, (v, n) in values.items()
    }
    people_ok = sum(1 for k in PEOPLE_COMPONENTS if values[k][0] is not None)
    usable = {k: c for k, c in components.items() if c["value"] is not None and c["weight"]}
    total_w = sum(c["weight"] for c in usable.values())
    # Sen polo menos dous compoñentes con datos de persoas (n ≥ 10), non se dá cifra
    if people_ok < 2 or not total_w:
        return {"value": None, "components": components}
    value = round(sum(c["value"] * c["weight"] for c in usable.values()) / total_w)
    return {"value": value, "components": components}


def level(value):
    """Etiqueta curta para a icona: alta, media ou baixa."""
    if value is None:
        return "none"
    return "high" if value >= 67 else ("mid" if value >= 40 else "low")


def municipality_indices(municipality, today=None):
    from apps.facilities.models import Facility

    out = []
    for f in Facility.objects.for_tenant(municipality).filter(is_published=True).order_by("name"):
        idx = facility_index(f, today)
        out.append({"facility": f, "value": idx["value"], "level": level(idx["value"]), **idx})
    return out
