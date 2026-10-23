# SPDX-License-Identifier: EUPL-1.2
"""Escolas e actividades: oferta, inscrición (propia ou de menores con consentimento) e pagamento."""

import csv

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.analytics import observatory
from apps.integrations.registry import get_adapter
from apps.tenants.urlutils import module_required, neighbour_required, role_required, treverse

from . import services
from .models import Activity, Enrollment, Group


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
        try:
            e = services.enroll(group, request.user, dependent)
        except services.EnrollmentError as exc:
            messages.error(request, str(exc))
            return redirect(request.path)
        if e.status == Enrollment.Status.PENDING_PAYMENT:
            ref, url = get_adapter("payment").create(
                group.fee_cents,
                f"{group} · {e.participant_name}",
                treverse(request.tenant, "activities:payment_return", e.pk),
            )
            e.payment_reference = ref
            e.save(update_fields=["payment_reference"])
            return redirect(url)
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
    e = get_object_or_404(Enrollment, municipality=request.tenant, pk=pk, user=request.user)
    status = get_adapter("payment").status(e.payment_reference) if e.payment_reference else None
    if status and status.paid:
        services.mark_enrollment_paid(e, status.reference, status.amount_cents)
        messages.success(request, _("Pagamento recibido. Inscrición confirmada."))
    else:
        messages.error(request, _("O pagamento non se completou."))
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
    data = observatory.summary(request.tenant)
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
    return render(request, "activities/observatory.html", {"data": data, "nav": "activities"})


@role_required("admin", "region_admin")
def manage_groups(request):
    groups = Group.objects.for_tenant(request.tenant).select_related(
        "activity", "monitor", "facility"
    )
    return render(
        request,
        "activities/manage_groups.html",
        {"groups": groups, "nav": "manage", "sub": "activities"},
    )
