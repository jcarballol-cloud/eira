# SPDX-License-Identifier: EUPL-1.2
"""Configuración do concello: regras, módulos, textos legais, persoal, empadroamento e alertas."""

import datetime as dt

from django import forms
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.accounts.models import Membership, ResidencyInvitation, Role, User, audit
from apps.bookings.services import apply_closure
from apps.facilities.models import Closure, Facility

from .models import DEFAULT_MODULES, Municipality
from .urlutils import role_required, treverse

ADMIN_ROLES = ("admin", "region_admin")

MODULE_LABELS = {
    "bookings": gettext_lazy("Reservas"),
    "access": gettext_lazy("Acceso por niveis"),
    "incidents": gettext_lazy("Incidencias"),
    "maintenance": gettext_lazy("Mantemento preventivo"),
    "activities": gettext_lazy("Escolas e actividades"),
    "monitor": gettext_lazy("Modo tableta para monitores"),
    "observatory": gettext_lazy("Observatorio anónimo"),
    "weather": gettext_lazy("Meteoroloxía"),
    "health": gettext_lazy("Saúde no dispositivo"),
    "ai_summary": gettext_lazy("Resumo semanal con IA autoaloxada"),
    "opendata": gettext_lazy("Datos abertos"),
}


class SettingsForm(forms.ModelForm):
    class Meta:
        model = Municipality
        fields = [
            "name",
            "accent_color",
            "contact_email",
            "contact_phone",
            "address",
            "cancellation_hours",
            "late_cancel_penalty_pct",
            "max_advance_days",
            "max_active_bookings",
            "no_show_grace_minutes",
            "privacy_text",
            "accessibility_statement",
            "legal_notice",
        ]
        widgets = {
            "accent_color": forms.TextInput(attrs={"type": "color"}),
            "privacy_text": forms.Textarea(attrs={"rows": 4}),
            "accessibility_statement": forms.Textarea(attrs={"rows": 4}),
            "legal_notice": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, label in MODULE_LABELS.items():
            self.fields[f"module_{key}"] = forms.BooleanField(
                label=label, required=False, initial=self.instance.module_enabled(key)
            )

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.modules = {k: bool(self.cleaned_data.get(f"module_{k}")) for k in DEFAULT_MODULES}
        if commit:
            obj.save()
        return obj


@role_required(*ADMIN_ROLES)
def settings_view(request):
    form = SettingsForm(request.POST or None, instance=request.tenant)
    if request.method == "POST" and form.is_valid():
        form.save()
        audit("tenant.settings", request.user, request.tenant)
        messages.success(request, _("Configuración gardada."))
        return redirect(treverse(request.tenant, "manage:settings"))
    module_fields = [form[f"module_{k}"] for k in MODULE_LABELS]
    base_fields = [form[f] for f in SettingsForm.Meta.fields]
    return render(
        request,
        "manage/settings.html",
        {
            "form": form,
            "module_fields": module_fields,
            "base_fields": base_fields,
            "nav": "manage",
            "sub": "settings",
        },
    )


class StaffForm(forms.Form):
    email = forms.EmailField(label=gettext_lazy("Correo"))
    role = forms.ChoiceField(label=gettext_lazy("Rol"), choices=Role.choices)


@role_required(*ADMIN_ROLES)
def staff(request):
    form = StaffForm(request.POST or None)
    if request.method == "POST":
        if request.POST.get("remove"):
            Membership.objects.filter(
                municipality=request.tenant, pk=request.POST["remove"]
            ).exclude(user=request.user).delete()
            messages.success(request, _("Rol retirado."))
            return redirect(treverse(request.tenant, "manage:staff"))
        if form.is_valid():
            user, _c = User.objects.get_or_create(email=form.cleaned_data["email"].lower())
            Membership.objects.get_or_create(
                user=user, municipality=request.tenant, role=form.cleaned_data["role"]
            )
            audit(
                "tenant.staff_add",
                request.user,
                request.tenant,
                user,
                role=form.cleaned_data["role"],
            )
            messages.success(request, _("Rol asignado."))
            return redirect(treverse(request.tenant, "manage:staff"))
    members = (
        Membership.objects.filter(municipality=request.tenant)
        .exclude(role=Role.CITIZEN)
        .select_related("user")
    )
    invitations = ResidencyInvitation.objects.filter(municipality=request.tenant).order_by(
        "-created_at"
    )[:20]
    return render(
        request,
        "manage/staff.html",
        {
            "form": form,
            "members": members,
            "invitations": invitations,
            "nav": "manage",
            "sub": "staff",
        },
    )


@role_required(*ADMIN_ROLES)
def issue_invitation(request):
    if request.method == "POST":
        inv = ResidencyInvitation.issue(request.tenant, note=request.POST.get("note", "")[:120])
        audit("residency.issue", request.user, request.tenant, inv)
        messages.success(request, _("Código de empadroamento xerado: %(c)s") % {"c": inv.code})
    return redirect(treverse(request.tenant, "manage:staff"))


@role_required(*ADMIN_ROLES)
def weather_alert(request):
    """Simula unha alerta meteorolóxica: pecha as instalacións descubertas e avisa ás reservas."""
    if request.method == "POST":
        hours = int(request.POST.get("hours", 6))
        start = timezone.now().replace(minute=0, second=0, microsecond=0)
        affected = 0
        for facility in Facility.objects.for_tenant(request.tenant).filter(
            indoor=False, is_published=True
        ):
            closure = Closure.objects.create(
                municipality=request.tenant,
                facility=facility,
                kind=Closure.Kind.WEATHER,
                reason=_("Aviso laranxa por vento e chuvia (simulado)"),
                starts_at=start,
                ends_at=start + dt.timedelta(hours=hours),
            )
            affected += len(apply_closure(closure, by=request.user))
        messages.warning(
            request,
            _("Alerta aplicada ás instalacións descubertas. %(n)s reservas canceladas e avisadas.")
            % {"n": affected},
        )
    return redirect(treverse(request.tenant, "manage:closures"))
