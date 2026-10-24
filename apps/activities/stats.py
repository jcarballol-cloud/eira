# SPDX-License-Identifier: EUPL-1.2
"""v4: estatísticas da monitora, só dos seus grupos e das últimas semanas.

Asistencia por sesión e media do grupo, ausencias seguidas (3 ou máis), esforzo medio (RPE) por
sesión e carga semanal (sRPE × minutos, Foster) e resultados agregados das probas físicas.
Os nomes móstranse só con nome + primeiro apelido, como na tableta (minimización)."""

import datetime as dt
from collections import defaultdict
from statistics import mean

from django.utils import timezone

from .models import Attendance, FitnessResult, Session
from .names import first_surname_label

WEEKS = 8
ABSENCE_STREAK = 3


def _label(enrollment):
    return f"{enrollment.participant_name} {first_surname_label(enrollment.surnames or '')}".strip()


def absence_streaks(sessions, marks, enrollments, threshold=ABSENCE_STREAK):
    """Persoas que faltaron ás últimas `threshold` sesións (ou máis) seguidas, xa rexistradas.
    `marks`: {(session_id, enrollment_id): present}. Só contan as sesións con asistencia pasada."""
    out = []
    recorded = [s for s in sessions if any(k[0] == s.pk for k in marks)]
    for e in enrollments:
        streak = 0
        for s in reversed(recorded):
            if marks.get((s.pk, e.pk)):
                break
            streak += 1
        if streak >= threshold:
            out.append({"label": _label(e), "streak": streak})
    return sorted(out, key=lambda r: (-r["streak"], r["label"]))


def group_stats(group, today=None, weeks=WEEKS):
    today = today or timezone.localdate()
    since = today - dt.timedelta(weeks=weeks)
    sessions = list(
        Session.objects.filter(group=group, date__gte=since, date__lte=today).order_by(
            "date", "start_time"
        )
    )
    atts = list(
        Attendance.objects.filter(session__in=sessions).select_related("session", "enrollment")
    )
    by_session = defaultdict(list)
    for a in atts:
        by_session[a.session_id].append(a)
    enrollments = list(group.enrolled())

    rows = []
    for s in sessions:
        lst = by_session.get(s.pk, [])
        if not lst:
            continue  # sesión sen rexistro (hoxe aínda non empezada, ou non se pasou lista)
        present = [a for a in lst if a.present]
        rpes = [a.rpe for a in present if a.rpe is not None]
        rows.append(
            {
                "date": s.date,
                "label": s.date.strftime("%d/%m"),
                "present": len(present),
                "total": len(lst),
                "pct": round(100 * len(present) / len(lst)) if lst else 0,
                "rpe": round(mean(rpes), 1) if rpes else None,
            }
        )

    # Carga semanal: media por participante da suma de sRPE × minutos de cada semana
    weekly = defaultdict(lambda: defaultdict(int))
    for a in atts:
        if a.session_load is not None:
            monday = a.session.date - dt.timedelta(days=a.session.date.weekday())
            weekly[monday][a.enrollment_id] += a.session_load
    week_rows = [
        {
            "week": monday,
            "label": monday.strftime("%d/%m"),
            "load": round(mean(per.values())),
            "people": len(per),
        }
        for monday, per in sorted(weekly.items())
    ]

    marks = {(a.session_id, a.enrollment_id): a.present for a in atts}
    return {
        "group": group,
        "sessions": rows,
        "avg_pct": round(mean(r["pct"] for r in rows)) if rows else None,
        "avg_rpe": round(mean(r["rpe"] for r in rows if r["rpe"] is not None), 1)
        if any(r["rpe"] is not None for r in rows)
        else None,
        "absences": absence_streaks(sessions, marks, enrollments),
        "weeks": week_rows,
        "fitness": fitness_summary(group),
    }


def fitness_summary(group):
    """Resultados agregados das probas físicas do grupo (último valor de cada persoa por proba)."""
    latest = {}
    for r in (
        FitnessResult.objects.filter(enrollment__group=group)
        .select_related("test")
        .order_by("date")
    ):
        latest[(r.test_id, r.enrollment_id)] = r
    per_test = defaultdict(list)
    for (_t, _e), r in latest.items():
        per_test[r.test].append(float(r.value))
    return [
        {
            "test": t.name,
            "unit": t.unit,
            "n": len(vals),
            "mean": round(mean(vals), 1),
            "min": round(min(vals), 1),
            "max": round(max(vals), 1),
        }
        for t, vals in sorted(per_test.items(), key=lambda kv: (kv[0].order, kv[0].name))
    ]
