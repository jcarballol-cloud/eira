# SPDX-License-Identifier: EUPL-1.2
"""Modo tableta para monitores: grupos do día, asistencia con nomes grandes, escala de esforzo
pictográfica (OMNI 0–10 para infancia, Borg CR-10 para adultos), carga da sesión e probas físicas."""

import datetime as dt
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.tenants.urlutils import module_required, role_required, treverse

from . import services
from .models import Attendance, FitnessBattery, FitnessResult, Group, Session

# Etiquetas das escalas (texto curto para acompañar as caras; sen baremos clínicos)
OMNI = {
    0: gettext_lazy("Nada cansado"),
    2: gettext_lazy("Un pouco"),
    4: gettext_lazy("Algo cansado"),
    6: gettext_lazy("Cansado"),
    8: gettext_lazy("Moi cansado"),
    10: gettext_lazy("Esgotado"),
}
BORG = {
    0: gettext_lazy("Repouso"),
    1: gettext_lazy("Moi, moi doado"),
    2: gettext_lazy("Doado"),
    3: gettext_lazy("Moderado"),
    4: gettext_lazy("Algo duro"),
    5: gettext_lazy("Duro"),
    7: gettext_lazy("Moi duro"),
    10: gettext_lazy("Máximo"),
}


def scale_points(scale):
    labels = OMNI if scale == Group.RpeScale.OMNI else BORG
    points = []
    for v in range(0, 11):
        face = "happy" if v <= 3 else ("neutral" if v <= 6 else "tired")
        points.append({"value": v, "label": labels.get(v, ""), "face": face})
    return points


def _groups_for(request):
    qs = Group.objects.for_tenant(request.tenant).select_related("activity", "facility")
    if not (request.roles & {"admin", "region_admin"}):
        qs = qs.filter(monitor=request.user)
    return qs


@module_required("monitor")
@role_required("monitor")
def today(request):
    try:
        day = dt.date.fromisoformat(request.GET.get("dia", ""))
    except ValueError:
        day = timezone.localdate()
    sessions = services.sessions_for_day(_groups_for(request), day)
    return render(
        request,
        "monitor/today.html",
        {
            "sessions": sessions,
            "day": day,
            "nav": "monitor",
            "prev": day - dt.timedelta(days=1),
            "next": day + dt.timedelta(days=1),
        },
    )


def _session(request, pk):
    return get_object_or_404(
        Session.objects.select_related("group__activity"),
        pk=pk,
        municipality=request.tenant,
        group__in=_groups_for(request),
    )


@module_required("monitor")
@role_required("monitor")
def attendance(request, pk):
    session = _session(request, pk)
    enrollments = list(session.group.enrolled().select_related("dependent", "user"))
    if request.method == "POST":
        present = {e.pk for e in enrollments if request.POST.get(f"p{e.pk}") == "1"}
        services.record_attendance(session, present)
        return redirect(treverse(request.tenant, "monitor:effort", session.pk))
    marked = {a.enrollment_id for a in session.attendances.filter(present=True)}
    return render(
        request,
        "monitor/attendance.html",
        {
            "session": session,
            "enrollments": enrollments,
            "marked": marked,
            "nav": "monitor",
        },
    )


@module_required("monitor")
@role_required("monitor")
def effort(request, pk):
    session = _session(request, pk)
    present = list(
        session.attendances.filter(present=True).select_related(
            "enrollment__dependent", "enrollment__user"
        )
    )
    if request.method == "POST":
        values = {}
        for a in present:
            raw = request.POST.get(f"rpe{a.enrollment_id}")
            if raw and raw.isdigit():
                values[a.enrollment_id] = int(raw)
        services.record_rpe(session, values)
        s = services.session_load_summary(session)
        messages.success(
            request,
            _("Sesión pechada. Carga media: %(l)s (sRPE × minutos).") % {"l": s["avg_load"] or "—"},
        )
        return redirect(treverse(request.tenant, "monitor:today"))
    rows = [{"att": a, "allowed": services.can_record_effort(a.enrollment)} for a in present]
    return render(
        request,
        "monitor/effort.html",
        {
            "session": session,
            "rows": rows,
            "points": scale_points(session.group.rpe_scale),
            "nav": "monitor",
        },
    )


@module_required("monitor")
@role_required("monitor")
def fitness(request, pk):
    group = get_object_or_404(_groups_for(request), pk=pk)
    batteries = FitnessBattery.objects.for_tenant(request.tenant).prefetch_related("tests")
    battery = (
        batteries.filter(pk=request.GET.get("bateria") or request.POST.get("bateria")).first()
        or batteries.first()
    )
    enrollments = [
        e
        for e in group.enrolled().select_related("dependent", "user")
        if services.can_record_effort(e)
    ]
    if request.method == "POST" and battery:
        saved = 0
        for e in enrollments:
            for t in battery.tests.all():
                raw = (request.POST.get(f"v{e.pk}_{t.pk}") or "").replace(",", ".").strip()
                if not raw:
                    continue
                try:
                    value = Decimal(raw)
                except InvalidOperation:
                    continue
                FitnessResult.objects.create(
                    enrollment=e,
                    test=t,
                    date=timezone.localdate(),
                    value=value,
                    recorded_by=request.user,
                )
                saved += 1
        messages.success(request, _("Gardados %(n)s resultados.") % {"n": saved})
        return redirect(request.get_full_path())
    return render(
        request,
        "monitor/fitness.html",
        {
            "group": group,
            "battery": battery,
            "batteries": batteries,
            "enrollments": enrollments,
            "nav": "monitor",
        },
    )


__all__ = ["today", "attendance", "effort", "fitness", "Attendance"]
