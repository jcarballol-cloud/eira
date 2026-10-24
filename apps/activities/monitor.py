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
from django.views.decorators.http import require_POST

from apps.tenants.urlutils import module_required, role_required, treverse

from . import services
from .models import Attendance, FitnessBattery, FitnessResult, Group, PendingParticipant, Session

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
        # Cinco caras para a escala OMNI infantil: 0–1, 2–3, 4–5, 6–7, 8–10
        points.append(
            {"value": v, "label": labels.get(v, ""), "face": f"omni-{min(5, v // 2 + 1)}"}
        )
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
    auto_in = {a.enrollment_id for a in session.attendances.filter(present=True, auto_in=True)}
    return render(
        request,
        "monitor/attendance.html",
        {
            "session": session,
            "enrollments": enrollments,
            "marked": marked,
            "auto_in": auto_in,
            "no_photo": sum(1 for e in enrollments if not e.can_appear_in_photos),
            "pending": session.group.pending_participants.filter(
                status=PendingParticipant.Status.PENDING
            ),
            "nav": "monitor",
        },
    )


@module_required("monitor")
@role_required("monitor")
def add_pending(request, pk):
    """Alguén apareceu na pista e non está na lista: o monitor apúntao e o concello valídao."""
    session = _session(request, pk)
    if request.method == "POST":
        name = request.POST.get("first_name", "").strip()[:60]
        year = request.POST.get("birth_year", "").strip()
        if name:
            PendingParticipant.objects.create(
                municipality=request.tenant,
                group=session.group,
                first_name=name,
                birth_year=int(year) if year.isdigit() and 1900 < int(year) < 2100 else None,
                guardian_email=request.POST.get("guardian_email", "").strip().lower()[:254],
                added_by=request.user,
            )
            messages.success(
                request,
                _("%(n)s queda apuntado/a. O concello validará a inscrición.") % {"n": name},
            )
    target = "monitor:kiosk" if request.POST.get("next") == "kiosk" else "monitor:attendance"
    return redirect(treverse(request.tenant, target, session.pk))


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
        msg = (
            _("Sesión pechada. Carga media: %(l)s (sRPE × minutos).")
            if session.closed_at
            else _("Esforzo gardado. Carga media: %(l)s (sRPE × minutos).")
        )
        messages.success(request, msg % {"l": s["avg_load"] or "—"})
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


@module_required("monitor")
@role_required("monitor")
def kiosk(request, pk):
    """Rexistro na tableta: abecedario → nomes → entrada ou saída con RPE → grazas."""
    session = _session(request, pk)
    group = session.group
    return render(
        request,
        "monitor/kiosk.html",
        {
            "session": session,
            "data": {
                "session": session.pk,
                "group": f"{group.activity.name} · {group.name}",
                "scale": group.rpe_scale,
                "api": treverse(request.tenant, "monitor:kiosk_api", session.pk),
                "people": services.kiosk_people(session),
                "points": [
                    {"value": p["value"], "label": str(p["label"]), "face": p["face"]}
                    for p in scale_points(group.rpe_scale)
                ],
            },
            "pending": session.group.pending_participants.filter(
                status=PendingParticipant.Status.PENDING
            ),
            "nav": "monitor",
        },
    )


@module_required("monitor")
@role_required("monitor")
@require_POST
def kiosk_api(request, pk):
    """Recibe un lote de toques (a tableta acumúlaos se non hai rede) e devolve o estado."""
    import json

    from django.http import JsonResponse
    from django.utils.dateparse import parse_datetime

    session = _session(request, pk)
    try:
        events = json.loads(request.body or b"[]")
    except ValueError:
        return JsonResponse({"error": "json"}, status=400)
    if isinstance(events, dict):
        events = [events]
    enrolled = {e.pk: e for e in session.group.enrolled().select_related("dependent", "user")}
    done = []
    for ev in events[:500]:
        e = enrolled.get(int(ev.get("enrollment", 0) or 0))
        if e is None or ev.get("action") not in ("in", "out"):
            continue
        at = parse_datetime(ev.get("at") or "") or None
        done.append(services.kiosk_record(session, e, ev["action"], ev.get("value"), at=at))
    return JsonResponse({"ok": True, "applied": done})


@module_required("monitor")
@role_required("monitor")
def stats(request):
    """v4: estatísticas da monitora (só os seus grupos), últimas 8 semanas."""
    from apps.analytics.indicators import hbar

    from . import stats as st

    blocks = []
    for g in _groups_for(request).filter(monitor=request.user):
        data = st.group_stats(g)
        data["cid"] = f"g{g.pk}"
        data["att_chart"] = hbar(data["sessions"], "pct", "label", suffix=" %", scale="percent")
        data["rpe_chart"] = hbar(
            [r for r in data["sessions"] if r["rpe"] is not None], "rpe", "label", maximum=10
        )
        data["load_chart"] = hbar(data["weeks"], "load", "label")
        blocks.append(data)
    return render(
        request,
        "monitor/stats.html",
        {"blocks": blocks, "weeks": st.WEEKS, "streak": st.ABSENCE_STREAK, "nav": "monitor"},
    )
