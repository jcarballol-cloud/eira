# SPDX-License-Identifier: EUPL-1.2
"""Observatorio anónimo da actividade física nas escolas municipais.

Garantías:
- Só agregados por grupo de idade e semana; nunca nomes nin idades exactas.
- Umbral mínimo de agregación (EIRA_MIN_AGGREGATION, por defecto n ≥ 10): por debaixo,
  a cela suprímese e móstrase «<n» sen valor.
- Os microdatos para persoal autorizado usan seudónimos (HMAC) e banda de idade.
"""

import datetime as dt
from collections import defaultdict

from django.conf import settings
from django.utils import timezone

from apps.activities.models import Attendance

BANDS = [(6, 11, "6–11"), (12, 17, "12–17"), (18, 39, "18–39"), (40, 64, "40–64"), (65, 120, "65+")]
# Referencia OMS 2020 (minutos semanais de actividade moderada-vigorosa). Configurable.
WHO_DEFAULT = {"minor": 420, "adult": 150}


def band_for(age):
    if age is None:
        return None
    for lo, hi, label in BANDS:
        if lo <= age <= hi:
            return label
    return None


def who_reference(label):
    refs = getattr(settings, "EIRA_WHO_WEEKLY_MINUTES", WHO_DEFAULT)
    return refs["minor"] if label in ("6–11", "12–17") else refs["adult"]


def _rows(municipality, weeks):
    since = timezone.localdate() - dt.timedelta(weeks=weeks)
    qs = Attendance.objects.filter(
        session__municipality=municipality,
        session__date__gte=since,
        session__date__lte=timezone.localdate(),
    ).select_related("enrollment__dependent", "enrollment__user", "session")
    for a in qs:
        band = band_for(a.enrollment.participant_age)
        if band:
            yield a, band


def summary(municipality, weeks=6, k=None):
    k = k or settings.EIRA_MIN_AGGREGATION
    people = defaultdict(set)
    sessions = defaultdict(int)
    present = defaultdict(int)
    minutes = defaultdict(int)
    weekly = defaultdict(lambda: defaultdict(int))
    weekly_people = defaultdict(lambda: defaultdict(set))
    rpe = defaultdict(list)
    for a, band in _rows(municipality, weeks):
        pid = a.enrollment.pseudonym or a.enrollment_id
        people[band].add(pid)
        sessions[band] += 1
        if a.present:
            present[band] += 1
            minutes[band] += a.minutes or a.session.duration_minutes
            monday = a.session.date - dt.timedelta(days=a.session.date.weekday())
            weekly[band][monday] += a.minutes or a.session.duration_minutes
            weekly_people[band][monday].add(pid)
            if a.rpe is not None:
                rpe[band].append(a.rpe)
    rows = []
    for _lo, _hi, label in BANDS:
        n = len(people[label])
        suppressed = n < k
        weekly_avg = (minutes[label] / n / weeks) if n else 0
        ref = who_reference(label)
        rows.append(
            {
                "band": label,
                "n": n,
                "suppressed": suppressed,
                "attendance_pct": None
                if suppressed or not sessions[label]
                else round(100 * present[label] / sessions[label]),
                "weekly_minutes": None if suppressed else round(weekly_avg),
                "who_reference": ref,
                "who_pct": None if suppressed else round(100 * weekly_avg / ref),
                "avg_rpe": None
                if suppressed or not rpe[label]
                else round(sum(rpe[label]) / len(rpe[label]), 1),
                "trend": []
                if suppressed
                else [
                    {"week": w, "minutes": round(weekly[label][w] / len(weekly_people[label][w]))}
                    for w in sorted(weekly[label])
                    if len(weekly_people[label][w]) >= k
                ],
            }
        )
    return {"rows": rows, "k": k, "weeks": weeks}


def microdata(municipality, weeks=6, k=None):
    """Filas seudonimizadas (seudónimo, banda, semana, minutos, RPE) só das bandas con n ≥ k."""
    k = k or settings.EIRA_MIN_AGGREGATION
    allowed = {r["band"] for r in summary(municipality, weeks, k)["rows"] if not r["suppressed"]}
    out = defaultdict(lambda: {"minutes": 0, "rpe": []})
    for a, band in _rows(municipality, weeks):
        if band not in allowed or not a.present:
            continue
        monday = a.session.date - dt.timedelta(days=a.session.date.weekday())
        row = out[(a.enrollment.pseudonym, band, monday)]
        row["minutes"] += a.minutes or a.session.duration_minutes
        if a.rpe is not None:
            row["rpe"].append(a.rpe)
    return [
        {
            "pseudonym": p,
            "band": b,
            "week": w,
            "minutes": v["minutes"],
            "avg_rpe": round(sum(v["rpe"]) / len(v["rpe"]), 1) if v["rpe"] else "",
        }
        for (p, b, w), v in sorted(out.items(), key=lambda kv: (kv[0][2], kv[0][1], kv[0][0]))
    ]
