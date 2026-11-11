# SPDX-License-Identifier: EUPL-1.2
"""Configuración do concello: regras, módulos, textos legais, persoal, empadroamento e alertas."""

import datetime as dt

from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.accounts.models import (
    AuditLog,
    Eligibility,
    Membership,
    ResidencyInvitation,
    Role,
    TwoFactorDevice,
    User,
    audit,
)
from apps.bookings.services import apply_closure
from apps.facilities.models import Closure, Facility

from .models import DEFAULT_MODULES, Municipality, SupportAccess
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
    # v1.2
    "open_games": gettext_lazy("Partidas abertas (buscar xente)"),
    "cards": gettext_lazy("Carné municipal e abonos"),
}


# Orde pensada para a grella de dúas columnas: as seccións curtas van emparelladas (Identidade e
# Padrón; Contacto e Regras de reserva) e as de campos longos ocupan as dúas columnas.
SETTINGS_SECTIONS = [
    ("identidade", gettext_lazy("Identidade"), ["name", "accent_color"], False),
    ("padron", gettext_lazy("Padrón"), ["postcodes"], False),
    (
        "contacto",
        gettext_lazy("Contacto"),
        ["contact_email", "contact_phone", "address", "telegram_channel", "dpo_contact"],
        False,
    ),
    (
        "reservas",
        gettext_lazy("Regras de reserva"),
        [
            "max_advance_days",
            "max_active_bookings",
            "cancellation_hours",
            "late_cancel_penalty_pct",
            "no_show_grace_minutes",
            "low_demand_discount_pct",  # v1.3: a ordenanza modelo remite a el
        ],
        False,
    ),
    # v5: formas de pagamento e luz; rede de concellos e índice de vida activa
    (
        "pagamentos",
        gettext_lazy("Formas de pagamento"),
        ["pay_methods", "office_payment_hours"],
        False,
    ),
    (
        "luz",
        gettext_lazy("Suplemento de iluminación"),
        ["lighting_rule", "lighting_from", "lighting_until"],
        False,
    ),
    (
        "rede",
        gettext_lazy("Concellos próximos"),
        ["network_open", "network_max_active", "network_advance_days"],
        False,
    ),
    (
        "indice",
        gettext_lazy("Índice de vida activa"),
        ["w_occupancy", "w_diversity", "w_satisfaction", "w_accessibility", "w_maintenance"],
        False,
    ),
    # v1.2
    (
        "peche",
        gettext_lazy("Seguridade e peche"),
        [
            "police_phone",
            "close_reminder_minutes",
            "close_second_minutes",
            "close_escalate_minutes",
            "close_breach_enabled",
            "accident_retention_months",
        ],
        False,
    ),
    (
        "confirmacion",
        gettext_lazy("Confirmación e lista de espera"),
        [
            "confirm_release_enabled",
            "confirm_release_minutes",
            "waitlist_offer_minutes",
            "checkin_release_minutes",
        ],
        False,
    ),
    ("enquisas", gettext_lazy("Satisfacción (NPS)"), ["nps_after_use"], False),
    # v1.3 · C
    (
        "contas",
        gettext_lazy("Seguridade das contas e rexistro de auditoría"),
        ["require_2fa_admin", "audit_retention_months"],
        False,
    ),
    (
        "rendemento",
        gettext_lazy("Rendemento (estimación orientativa)"),
        ["energy_price_eur_kwh", "co2_kg_kwh"],
        False,
    ),
    ("mapa", gettext_lazy("Mapa"), ["tile_url", "tile_attribution", "tile_attribution_url"], True),
    (
        "legal",
        gettext_lazy("Textos legais"),
        ["privacy_text", "legal_notice"],
        True,
    ),
    # v1.5.1: declaración de accesibilidade (RD 1112/2018, art. 15)
    (
        "accesibilidade",
        gettext_lazy("Declaración de accesibilidade"),
        [
            "accessibility_unit",
            "accessibility_email",
            "accessibility_phone",
            "accessibility_complaint_url",
            "accessibility_reviewed_on",
            "accessibility_statement",
        ],
        True,
    ),
]


class SettingsForm(forms.ModelForm):
    class Meta:
        model = Municipality
        fields = [
            "name",
            "accent_color",
            "contact_email",
            "contact_phone",
            "address",
            "telegram_channel",
            "cancellation_hours",
            "late_cancel_penalty_pct",
            "max_advance_days",
            "max_active_bookings",
            "no_show_grace_minutes",
            "postcodes",
            "tile_url",
            "tile_attribution",
            "tile_attribution_url",
            "dpo_contact",
            "privacy_text",
            "accessibility_statement",
            "accessibility_unit",  # v1.5.1
            "accessibility_email",
            "accessibility_phone",
            "accessibility_complaint_url",
            "accessibility_reviewed_on",
            "legal_notice",
            "office_payment_hours",
            "lighting_rule",
            "lighting_from",
            "lighting_until",
            "network_open",
            "network_max_active",
            "network_advance_days",
            # v1.2
            "police_phone",
            "close_reminder_minutes",
            "close_second_minutes",
            "close_escalate_minutes",
            "close_breach_enabled",
            "accident_retention_months",
            "confirm_release_enabled",
            "confirm_release_minutes",
            "waitlist_offer_minutes",
            "checkin_release_minutes",
            "nps_after_use",
            "energy_price_eur_kwh",
            "co2_kg_kwh",
            "require_2fa_admin",  # v1.3
            "low_demand_discount_pct",  # v1.3
            "audit_retention_months",  # v1.4
            "accreditation_review_months",  # v1.5 · E
            "latitude",  # v1.5 · C
            "longitude",
        ]
        widgets = {
            "lighting_from": forms.TimeInput(attrs={"type": "time"}),
            "lighting_until": forms.TimeInput(attrs={"type": "time"}),
            "accent_color": forms.TextInput(attrs={"type": "color"}),
            "privacy_text": forms.Textarea(attrs={"rows": 4}),
            "accessibility_statement": forms.Textarea(attrs={"rows": 4}),
            "accessibility_reviewed_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "legal_notice": forms.Textarea(attrs={"rows": 3}),
            # Correo e enderezo xuntos: nunha caixa dunha liña cortábase
            "dpo_contact": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.analytics.vitality import COMPONENTS, weights_for

        from .models import PaymentMethod

        self.fields["pay_methods"] = forms.MultipleChoiceField(
            label=gettext_lazy("Formas de pagamento admitidas"),
            choices=PaymentMethod.choices,
            widget=forms.CheckboxSelectMultiple,
            initial=self.instance.payment_method_list(),
            help_text=gettext_lazy(
                "Cada instalación pode restrinxilas. O aprazado só se activa aquí (por defecto, non)."
            ),
        )
        weights = weights_for(self.instance)
        for key, label in COMPONENTS.items():
            self.fields[f"w_{key}"] = forms.IntegerField(
                label=label, min_value=0, max_value=100, initial=weights[key]
            )
        self.fields["w_occupancy"].help_text = gettext_lazy(
            "Pesos relativos (0–100). Ver docs/indice-vida-activa.md."
        )
        for key, label in MODULE_LABELS.items():
            self.fields[f"module_{key}"] = forms.BooleanField(
                label=label, required=False, initial=self.instance.module_enabled(key)
            )
        # v5: campos novos con valor por defecto; se non veñen no formulario, mantense o que había
        for name in self.V5_KEEP + ("pay_methods",) + tuple(f"w_{k}" for k in COMPONENTS):
            self.fields[name].required = False

    V5_KEEP = (
        "office_payment_hours",
        "lighting_rule",
        "lighting_from",
        "lighting_until",
        "network_max_active",
        # v1.2: se non veñen no formulario, mantense o que había
        "close_reminder_minutes",
        "close_second_minutes",
        "close_escalate_minutes",
        "accident_retention_months",
        "confirm_release_minutes",
        "waitlist_offer_minutes",
        "checkin_release_minutes",
        "energy_price_eur_kwh",
        "co2_kg_kwh",
        "low_demand_discount_pct",  # v1.3
        "audit_retention_months",  # v1.4
        "accreditation_review_months",  # v1.5 · E
        "latitude",
        "longitude",
    )

    def clean(self):
        data = super().clean()
        for name in self.V5_KEEP:
            if data.get(name) in (None, ""):
                data[name] = getattr(self.instance, name)
        return data

    def save(self, commit=True):
        from apps.analytics.vitality import COMPONENTS, weights_for

        obj = super().save(commit=False)
        obj.modules = {k: bool(self.cleaned_data.get(f"module_{k}")) for k in DEFAULT_MODULES}
        if "pay_methods" in self.data or self.cleaned_data.get("pay_methods"):
            obj.payment_methods = list(self.cleaned_data.get("pay_methods") or ["tpv"])
        current = weights_for(self.instance)
        obj.vitality_weights = {
            k: current[k]
            if self.cleaned_data.get(f"w_{k}") is None
            else self.cleaned_data[f"w_{k}"]
            for k in COMPONENTS
        }
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
    # v4: formulario por seccións, en grella
    sections = [
        {"id": sid, "title": title, "fields": [form[f] for f in names], "wide": wide}
        for sid, title, names, wide in SETTINGS_SECTIONS
    ]
    return render(
        request,
        "manage/settings.html",
        {
            "form": form,
            "module_fields": module_fields,
            "sections": sections,
            "nav": "manage",
            "sub": "settings",
        },
    )


class StaffForm(forms.Form):
    email = forms.EmailField(label=gettext_lazy("Correo"))
    role = forms.ChoiceField(label=gettext_lazy("Rol"), choices=Role.choices)
    # v1.1: persoal de limpeza dunha empresa contratada
    company = forms.CharField(
        label=gettext_lazy("Empresa (opcional)"),
        required=False,
        max_length=120,
        help_text=gettext_lazy(
            "Só se a persoa traballa para unha empresa contratada (p. ex. a de limpeza)."
        ),
    )
    # v1.5 · E: voluntariado con rol de monitora (a acreditación con menores é a mesma)
    is_volunteer = forms.BooleanField(
        label=gettext_lazy("Persoa voluntaria"),
        required=False,
        help_text=gettext_lazy(
            "Marca esta casiña se é unha persoa voluntaria con rol de monitora."
        ),
    )


class EligibilityForm(forms.Form):
    email = forms.EmailField(label=gettext_lazy("Correo da persoa"))
    kind = forms.ChoiceField(label=gettext_lazy("Colectivo"), choices=Eligibility.Kind.choices)
    expires_on = forms.DateField(
        label=gettext_lazy("Válido ata"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )


@role_required(*ADMIN_ROLES)
def staff(request):
    form = StaffForm(request.POST if request.POST.get("action") != "eligibility" else None)
    elig_form = EligibilityForm(
        request.POST if request.POST.get("action") == "eligibility" else None, prefix="elig"
    )
    if request.method == "POST" and request.POST.get("action") in (
        "support_grant",
        "support_revoke",
    ):
        return _support_access(request)
    if request.method == "POST" and request.POST.get("action") == "eligibility":
        if elig_form.is_valid():
            d = elig_form.cleaned_data
            user = User.objects.filter(email=d["email"].lower()).first()
            if user is None:
                elig_form.add_error("email", _("Non hai ningunha conta con ese correo."))
            else:
                Eligibility.objects.create(
                    user=user,
                    municipality=request.tenant,
                    kind=d["kind"],
                    expires_on=d["expires_on"],
                    validated_by=request.user,
                )
                audit("eligibility.validate", request.user, request.tenant, user, kind=d["kind"])
                messages.success(
                    request, _("Tarifa reducida validada para %(e)s.") % {"e": user.email}
                )
                return redirect(treverse(request.tenant, "manage:staff"))
    elif request.method == "POST":
        if request.POST.get("reset_2fa"):
            # v1.3 · C: quen perdeu o móbil e os códigos de recuperación
            from apps.accounts import twofactor

            target = get_object_or_404(
                User.objects.filter(memberships__municipality=request.tenant).distinct(),
                pk=request.POST["reset_2fa"],
            )
            try:
                twofactor.reset_for(target, request.user, request.tenant)
            except twofactor.TwoFactorError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(
                    request,
                    _("Dobre factor restablecido. %(e)s pode activalo de novo ao entrar.")
                    % {"e": target.email},
                )
            return redirect(treverse(request.tenant, "manage:staff"))
        if request.POST.get("remove"):
            removed = (
                Membership.objects.filter(municipality=request.tenant, pk=request.POST["remove"])
                .exclude(user=request.user)
                .select_related("user")
                .first()
            )
            if removed is not None:
                removed.delete()
                # v1.3 · C: a retirada de permisos tamén queda no rexistro de auditoría
                audit(
                    "tenant.staff_remove",
                    request.user,
                    request.tenant,
                    removed.user,
                    role=removed.role,
                )
            messages.success(request, _("Rol retirado."))
            return redirect(treverse(request.tenant, "manage:staff"))
        if form.is_valid():
            user, _c = User.objects.get_or_create(email=form.cleaned_data["email"].lower())
            membership, _c = Membership.objects.get_or_create(
                user=user, municipality=request.tenant, role=form.cleaned_data["role"]
            )
            if form.cleaned_data.get("company") != membership.company:
                membership.company = form.cleaned_data.get("company", "")
                membership.save(update_fields=["company"])
            if form.cleaned_data.get("is_volunteer") != membership.is_volunteer:
                membership.is_volunteer = form.cleaned_data["is_volunteer"]
                membership.save(update_fields=["is_volunteer"])
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
            "elig_form": elig_form,
            "eligibilities": Eligibility.objects.filter(municipality=request.tenant).select_related(
                "user"
            )[:30],
            "form": form,
            "members": members,
            # v1.3 · C
            "two_factor_users": set(
                TwoFactorDevice.objects.filter(
                    user__in=members.values("user"), confirmed_at__isnull=False
                ).values_list("user_id", flat=True)
            ),
            "management_roles": ("admin", "dpo"),
            "invitations": invitations,
            "support_active": SupportAccess.active_for(
                request.tenant, [request.tenant.region_id] if request.tenant.region_id else []
            ),
            "support_history": SupportAccess.objects.filter(municipality=request.tenant)[:10],
            "support_uses": AuditLog.objects.filter(
                municipality=request.tenant, action="support.view"
            ).select_related("actor")[:15],
            "nav": "manage",
            "sub": "staff",
        },
    )


def _support_access(request):
    """O concello autoriza (24 h) ou revoga o acceso de soporte da deputación aos datos persoais."""
    tenant = request.tenant
    back = redirect(treverse(tenant, "manage:staff") + "#soporte")
    if not tenant.region_id:
        messages.error(request, _("Este concello non pertence a ningunha deputación."))
        return back
    if request.POST["action"] == "support_grant":
        reason = (request.POST.get("reason") or "").strip()[:200]
        if not reason:
            messages.error(request, _("Indica o motivo do acceso de soporte."))
            return back
        now = timezone.now()
        access = SupportAccess.objects.create(
            municipality=tenant,
            region_id=tenant.region_id,
            reason=reason,
            granted_by=request.user,
            granted_at=now,
            expires_at=now + SupportAccess.DURATION,
        )
        audit("support.grant", request.user, tenant, access, reason=reason)
        messages.success(
            request,
            _("Acceso de soporte autorizado ata o %(d)s.")
            % {"d": timezone.localtime(access.expires_at).strftime("%d/%m %H:%M")},
        )
    else:
        n = SupportAccess.objects.filter(
            municipality=tenant, revoked_at__isnull=True, expires_at__gt=timezone.now()
        ).update(revoked_at=timezone.now())
        audit("support.revoke", request.user, tenant, tenant, count=n)
        messages.success(request, _("Acceso de soporte retirado."))
    return back


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
