# SPDX-License-Identifier: EUPL-1.2
"""Escolas e actividades: oferta, inscrición (propia ou de menores con consentimento) e pagamento."""

import csv

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.accounts.models import audit
from apps.analytics import observatory
from apps.bookings.payments import start_online_payment
from apps.integrations.registry import get_adapter
from apps.tenants.urlutils import module_required, neighbour_required, role_required, treverse

from . import services
from .models import Activity, Enrollment, Group, PendingParticipant


@module_required("activities")
def activity_list(request):
    activities = (
        Activity.objects.for_tenant(request.tenant)
        .filter(is_published=True)
        .prefetch_related("groups__facility", "groups__enrollments")
    )
    return render(request, "activities/list.html", {"activities": activities, "nav": "activities"})


@module_required("activities")
@neighbour_required
def enroll(request, pk):
    group = get_object_or_404(
        Group.objects.select_related("activity", "facility"), municipality=request.tenant, pk=pk
    )
    household = getattr(request.user, "household", None)
    dependents = list(household.dependents.prefetch_related("consents")) if household else []
    if request.method == "POST":
        who = request.POST.get("participant", "self")
        dependent = None
        if who != "self":
            dependent = next((d for d in dependents if str(d.pk) == who), None)
            if dependent is None:
                messages.error(request, _("Escolle unha persoa válida."))
                return redirect(request.path)
        # v4: os apelidos do/a menor son obrigatorios ao inscribilo/a nunha escola (dato da
        # inscrición, como no padrón); para a propia persoa adulta son opcionais
        surnames = request.POST.get("surnames", "").strip()
        if dependent is not None and not surnames:
            messages.error(
                request,
                _("Indica os apelidos de %(n)s, como figuran no padrón.")
                % {"n": dependent.first_name},
            )
            return render(
                request,
                "activities/enroll.html",
                {
                    "group": group,
                    "dependents": dependents,
                    "nav": "activities",
                    "selected": who,
                    "surnames_error": True,
                },
                status=400,
            )
        try:
            e = services.enroll(group, request.user, dependent, surnames=surnames)
        except services.EnrollmentError as exc:
            messages.error(request, str(exc))
            return redirect(request.path)
        if e.status == Enrollment.Status.PENDING_PAYMENT:
            back = treverse(request.tenant, "activities:payment_return", e.pk)
            return redirect(
                start_online_payment(
                    enrollment=e, url_ok=back + "?resultado=ok", url_ko=back + "?resultado=ko"
                )
            )
        if e.status == Enrollment.Status.WAITLIST:
            messages.warning(
                request,
                _(
                    "O grupo está completo: quedas na lista de espera. Avisarémoste se queda unha praza."
                ),
            )
        else:
            messages.success(request, _("Inscrición confirmada."))
        return redirect(treverse(request.tenant, "activities:mine"))
    return render(
        request,
        "activities/enroll.html",
        {"group": group, "dependents": dependents, "nav": "activities"},
    )


@neighbour_required
def payment_return(request, pk):
    """Volta da pasarela: o estado xa o fixou a notificación asinada; aquí só se informa."""
    e = get_object_or_404(Enrollment, municipality=request.tenant, pk=pk, user=request.user)
    if e.status == Enrollment.Status.ACTIVE:
        messages.success(request, _("Pagamento recibido. Inscrición confirmada."))
    elif e.status == Enrollment.Status.PENDING_PAYMENT:
        messages.info(request, _("Agardando a confirmación do banco."))
    else:
        messages.error(request, _("O pagamento non se completou. Non se fixo ningún cargo."))
    return redirect(treverse(request.tenant, "activities:mine"))


@module_required("activities")
@neighbour_required
def mine(request):
    enrollments = (
        Enrollment.objects.for_tenant(request.tenant)
        .filter(user=request.user)
        .exclude(status=Enrollment.Status.CANCELLED)
        .select_related("group__activity", "dependent")
    )
    return render(
        request, "activities/mine.html", {"enrollments": enrollments, "nav": "activities"}
    )


@neighbour_required
@require_POST
def cancel(request, pk):
    e = get_object_or_404(Enrollment, municipality=request.tenant, pk=pk, user=request.user)
    services.cancel_enrollment(e, request.user)
    messages.success(request, _("Baixa tramitada."))
    return redirect(treverse(request.tenant, "activities:mine"))


@module_required("observatory")
def observatory_view(request):
    from apps.analytics.indicators import hbar
    from apps.analytics.views import _csv

    weeks = int(request.GET["semanas"]) if request.GET.get("semanas") in ("6", "12", "26") else 6
    activities = Activity.objects.for_tenant(request.tenant).order_by("name")
    activity = activities.filter(pk=request.GET.get("actividade") or 0).first()
    data = observatory.summary(request.tenant, weeks=weeks, activity=activity)
    fmt = request.GET.get("csv") or request.GET.get("ods")
    if fmt == "agregados":
        k = data["k"]
        return _csv(
            "observatorio-agregados.csv",
            [
                "banda_idade",
                "persoas",
                "asistencia_pct",
                "minutos_semana",
                "referencia_oms",
                "pct_oms",
                "rpe_medio",
            ],
            [
                [r["band"], f"<{k}", "", "", r["who_reference"], "", ""]
                if r["suppressed"]
                else [
                    r["band"],
                    r["n"],
                    r["attendance_pct"],
                    r["weekly_minutes"],
                    r["who_reference"],
                    r["who_pct"],
                    r["avg_rpe"] or "",
                ]
                for r in data["rows"]
            ],
            ods=bool(request.GET.get("ods")),
        )
    if request.GET.get("csv") == "micro":
        if not request.user.is_authenticated or not (request.roles & {"admin", "region_admin"}):
            return HttpResponse(status=403)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="observatorio-seudonimizado.csv"'
        w = csv.writer(response)
        w.writerow(["seudonimo", "banda_idade", "semana", "minutos", "rpe_medio"])
        for r in observatory.microdata(request.tenant):
            w.writerow([r["pseudonym"], r["band"], r["week"], r["minutes"], r["avg_rpe"]])
        return response
    shown = [r for r in data["rows"] if not r["suppressed"]]
    return render(
        request,
        "activities/observatory.html",
        {
            "data": data,
            "weeks": weeks,
            "activities": activities,
            "activity": activity,
            "who_chart": hbar(shown, "who_pct", "band", suffix=" %", scale="percent"),
            "att_chart": hbar(shown, "attendance_pct", "band", suffix=" %", scale="percent"),
            "line": observatory.line_chart(data["rows"]),
            "query": f"semanas={weeks}" + (f"&actividade={activity.pk}" if activity else ""),
            "nav": "activities",
            "sub": "observatory",
        },
    )


@role_required("admin", "region_admin")
def manage_groups(request):
    groups = Group.objects.for_tenant(request.tenant).select_related(
        "activity", "monitor", "facility"
    )
    return render(
        request,
        "activities/manage_groups.html",
        {
            "groups": groups,
            "pending": PendingParticipant.objects.for_tenant(request.tenant)
            .filter(status=PendingParticipant.Status.PENDING)
            .select_related("group__activity", "added_by"),
            "nav": "manage",
            "sub": "activities",
        },
    )


@role_required("admin", "region_admin")
@require_POST
def pending_resolve(request, pk):
    """O concello valida (ou descarta) unha persoa que o monitor apuntou na pista."""
    pending = get_object_or_404(
        PendingParticipant.objects.select_related("group"),
        municipality=request.tenant,
        pk=pk,
        status=PendingParticipant.Status.PENDING,
    )
    back = redirect(treverse(request.tenant, "manage:activities"))
    if request.POST.get("action") != "validate":
        pending.status = PendingParticipant.Status.REJECTED
        pending.resolved_at = timezone.now()
        pending.save(update_fields=["status", "resolved_at"])
        messages.success(request, _("Descartamos a %(n)s.") % {"n": pending.first_name})
        return back
    email = (request.POST.get("guardian_email") or pending.guardian_email).strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, _("Indica un correo válido da familia ou da persoa."))
        return back
    minor = pending.birth_year and timezone.localdate().year - pending.birth_year < 18
    if minor and request.POST.get("paper_consent") != "1":
        messages.error(
            request, _("Para un menor fai falta a autorización da familia (papel ou mostrador).")
        )
        return back
    try:
        enrollment = services.validate_pending(
            pending, email, request.user, surnames=request.POST.get("surnames", "")
        )
    except services.EnrollmentError as exc:
        messages.error(request, str(exc))
        return back
    get_adapter("mail").send(
        email,
        _("Inscrición en %(g)s") % {"g": pending.group},
        _(
            "%(n)s xa ten inscrición en %(g)s. Entra na app co teu correo para ver os horarios "
            "e revisar os consentimentos."
        )
        % {"n": pending.first_name, "g": pending.group},
    )
    messages.success(
        request,
        _("Inscrición feita: %(n)s (%(s)s).")
        % {"n": pending.first_name, "s": enrollment.get_status_display()},
    )
    return back


@role_required("admin", "region_admin")
def manage_group(request, pk):
    """Ficha do grupo para o concello: participantes, consentimentos de imaxe e esforzo."""
    group = get_object_or_404(
        Group.objects.for_tenant(request.tenant).select_related("activity", "monitor", "facility"),
        pk=pk,
    )
    rows = []
    for e in group.enrollments.exclude(status=Enrollment.Status.CANCELLED).select_related(
        "dependent__household__responsible", "user"
    ):
        rows.append(
            {
                "e": e,
                "photo": e.can_appear_in_photos,
                "performance": e.dependent.has_consent("performance") if e.dependent else True,
                "minor": bool(e.dependent),
            }
        )
    if request.method == "POST" and request.POST.get("action") == "surnames":
        e = get_object_or_404(group.enrollments, pk=request.POST.get("enrollment"))
        e.surnames = request.POST.get("surnames", "").strip()[:80]
        e.save(update_fields=["surnames"])
        audit("enrollment.surnames", request.user, request.tenant, e)
        messages.success(request, _("Apelidos gardados."))
        return redirect(treverse(request.tenant, "manage:group", group.pk))
    no_photo = sum(1 for r in rows if not r["photo"])
    only = request.GET.get("sen_fotos") == "1"
    return render(
        request,
        "activities/manage_group.html",
        {
            "group": group,
            "rows": [r for r in rows if not r["photo"]] if only else rows,
            "total": len(rows),
            "no_photo": no_photo,
            "only": only,
            "nav": "manage",
            "sub": "activities",
        },
    )
