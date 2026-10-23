# SPDX-License-Identifier: EUPL-1.2
from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.accounts.models import Membership, Role, User
from apps.tenants.urlutils import role_required, treverse

from . import services
from .models import Incident

ADMIN_ROLES = ("admin", "region_admin")


class WorkOrderFromIncidentForm(forms.Form):
    title = forms.CharField(label=gettext_lazy("Título da orde"), max_length=160)
    assigned_to = forms.ModelChoiceField(
        label=gettext_lazy("Asignar a"), queryset=User.objects.none(), required=False
    )
    due_date = forms.DateField(
        label=gettext_lazy("Data prevista"), widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        ids = Membership.objects.filter(municipality=tenant, role=Role.MAINTENANCE).values_list(
            "user_id", flat=True
        )
        self.fields["assigned_to"].queryset = User.objects.filter(pk__in=ids)
        self.fields["assigned_to"].empty_label = gettext_lazy("Sen asignar")


@role_required(*ADMIN_ROLES)
def incident_list(request):
    status = request.GET.get("estado", "")
    qs = Incident.objects.for_tenant(request.tenant).select_related("facility", "reporter")
    if status:
        qs = qs.filter(status=status)
    return render(
        request,
        "manage/incidents.html",
        {
            "incidents": qs[:200],
            "status": status,
            "statuses": Incident.Status.choices,
            "nav": "manage",
            "sub": "incidents",
        },
    )


@role_required(*ADMIN_ROLES)
def incident_detail(request, pk):
    incident = get_object_or_404(
        Incident.objects.select_related("facility", "reporter"), municipality=request.tenant, pk=pk
    )
    form = WorkOrderFromIncidentForm(
        request.POST if request.POST.get("action") == "order" else None,
        tenant=request.tenant,
        initial={
            "title": _("Incidencia #%(n)s: %(c)s")
            % {"n": incident.pk, "c": incident.get_category_display()},
            "due_date": timezone.localdate(),
        },
    )
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "validate" and incident.status == Incident.Status.RECEIVED:
            services.validate(incident, request.user)
            messages.success(request, _("Incidencia validada. Avisamos a quen informou."))
        elif action == "reject":
            services.reject(incident, request.user, request.POST.get("note", ""))
            messages.success(request, _("Incidencia descartada."))
        elif action == "resolve":
            services.resolve(incident, request.user, request.POST.get("note", ""))
            messages.success(request, _("Incidencia resolta. Avisamos a quen informou."))
        elif action == "order" and form.is_valid():
            order = services.create_work_order(
                incident,
                request.user,
                form.cleaned_data["assigned_to"],
                form.cleaned_data["due_date"],
                form.cleaned_data["title"],
            )
            messages.success(request, _("Creada a orde de traballo #%(n)s.") % {"n": order.pk})
        return redirect(treverse(request.tenant, "manage:incident_detail", incident.pk))
    return render(
        request,
        "manage/incident_detail.html",
        {
            "incident": incident,
            "form": form,
            "orders": incident.work_orders.all(),
            "nav": "manage",
            "sub": "incidents",
        },
    )
