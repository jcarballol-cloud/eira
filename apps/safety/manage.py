# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · Xestión: alertas, persoas responsables, protocolo, peches sen confirmar e rexistro de
accidentes (este último só para a administración do concello e o DPD)."""

from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST

from apps.accounts.breaches import breach_access
from apps.accounts.models import audit
from apps.facilities.models import Facility
from apps.tenants.urlutils import role_required, treverse

from . import services
from .models import (
    PROTOCOL_STEPS,
    AccidentProtocol,
    AccidentReport,
    Alert,
    ClosingEscalation,
    PoliceContact,
    ResponsibleContact,
)

ADMIN = ("admin",)


class ContactForm(forms.ModelForm):
    class Meta:
        model = ResponsibleContact
        fields = [
            "order",
            "name",
            "role_label",
            "phone",
            "email",
            "from_time",
            "until_time",
            "active",
        ]
        widgets = {
            "from_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "until_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }


@role_required(*ADMIN)
def safety_home(request):
    t = request.tenant
    if request.method == "POST" and request.POST.get("accion") == "recibida":
        alert = get_object_or_404(Alert, municipality=t, pk=request.POST.get("alerta"))
        services.acknowledge(alert, request.user)
        messages.success(request, _("Alerta marcada como atendida."))
        return redirect(treverse(t, "manage:safety"))
    form = ContactForm(request.POST or None, prefix="c")
    if request.method == "POST" and request.POST.get("accion") == "contacto" and form.is_valid():
        contact = form.save(commit=False)
        contact.municipality = t
        contact.save()
        audit("safety.contact_add", request.user, t, contact)
        messages.success(request, _("Persoa responsable engadida."))
        return redirect(treverse(t, "manage:safety") + "#responsables")
    return render(
        request,
        "manage/safety.html",
        {
            "alerts": Alert.objects.filter(municipality=t).select_related("facility")[:20],
            "contacts": ResponsibleContact.objects.filter(municipality=t),
            "on_duty": services.on_duty(t),
            "form": form,
            "escalations": ClosingEscalation.objects.filter(municipality=t)
            .select_related("booking__facility", "contact")
            .order_by("-pk")[:15],
            "police": PoliceContact.objects.filter(municipality=t).select_related(
                "escalation__booking__facility", "by_contact"
            )[:10],
            "nav": "manage",
            "sub": "safety",
        },
    )


@role_required(*ADMIN)
@require_POST
def contact_delete(request, pk):
    contact = get_object_or_404(ResponsibleContact, municipality=request.tenant, pk=pk)
    audit("safety.contact_delete", request.user, request.tenant, contact)
    contact.delete()
    messages.success(request, _("Persoa responsable eliminada."))
    return redirect(treverse(request.tenant, "manage:safety") + "#responsables")


class ProtocolForm(forms.ModelForm):
    class Meta:
        model = AccidentProtocol
        fields = list(PROTOCOL_STEPS)
        widgets = {k: forms.Textarea(attrs={"rows": 2}) for k in PROTOCOL_STEPS}


@role_required(*ADMIN)
def protocol_edit(request):
    t = request.tenant
    facility = None
    if request.GET.get("instalacion", "").isdigit():
        facility = get_object_or_404(Facility.objects.for_tenant(t), pk=request.GET["instalacion"])
    instance = AccidentProtocol.objects.filter(municipality=t, facility=facility).first()
    if instance is None:
        base = services.protocol_for(t, None)  # a instalación parte do protocolo do concello
        instance = AccidentProtocol(
            municipality=t, facility=facility, **{k: getattr(base, k) for k in PROTOCOL_STEPS}
        )
    form = ProtocolForm(request.POST or None, instance=instance)
    if request.method == "POST":
        if request.POST.get("accion") == "restablecer" and instance.pk:
            instance.delete()
            messages.success(request, _("Protocolo restablecido."))
            return redirect(request.get_full_path())
        if form.is_valid():
            form.save()
            audit("safety.protocol", request.user, t, form.instance)
            messages.success(request, _("Protocolo gardado."))
            return redirect(request.get_full_path())
    return render(
        request,
        "manage/safety_protocol.html",
        {
            "form": form,
            "facility": facility,
            "own": instance.pk is not None,
            "facilities": Facility.objects.for_tenant(t),
            "nav": "manage",
            "sub": "safety",
        },
    )


@role_required(*ADMIN, "maintenance")
def escalation_detail(request, pk):
    esc = get_object_or_404(ClosingEscalation, municipality=request.tenant, pk=pk)
    return redirect(treverse(request.tenant, "safety:closing", esc.token))


class CloseAccidentForm(forms.Form):
    facility_related = forms.TypedChoiceField(
        label=gettext_lazy("A instalación tivo que ver?"),
        choices=[
            ("", gettext_lazy("Sen saber")),
            ("1", gettext_lazy("Si")),
            ("0", gettext_lazy("Non")),
        ],
        coerce=lambda v: v == "1",
        empty_value=None,
        required=False,
    )


@breach_access
def accidents(request):
    t = request.tenant
    if request.method == "POST":
        report = get_object_or_404(AccidentReport, municipality=t, pk=request.POST.get("accidente"))
        form = CloseAccidentForm(request.POST)
        if form.is_valid():
            services.close_accident(report, request.user, form.cleaned_data["facility_related"])
            messages.success(request, _("Accidente pechado no rexistro."))
        return redirect(treverse(t, "manage:accidents"))
    reports = AccidentReport.objects.filter(municipality=t).select_related("facility", "alert")
    return render(
        request,
        "manage/accidents.html",
        {
            "reports": reports,
            "open_count": reports.filter(closed_at__isnull=True).count(),
            "close_form": CloseAccidentForm(),
            "retention": t.accident_retention_months,
            "now": timezone.now(),
            "nav": "manage",
            "sub": "accidents",
        },
    )
