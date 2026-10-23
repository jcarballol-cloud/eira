# SPDX-License-Identifier: EUPL-1.2
"""Xestión municipal de instalacións: alta asistida con plantillas, horarios, peches, tarifas e normas."""

from django import forms
from django.contrib import messages
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.accounts.models import audit
from apps.bookings.services import apply_closure
from apps.tenants.uploads import clean_image
from apps.tenants.urlutils import role_required, treverse

from .catalog import TEMPLATES, apply_template, ensure_lock, template_choices
from .models import Closure, Facility, OpeningHours, Parish, RulesVersion, Tariff

ADMIN_ROLES = ("admin", "region_admin")


class FacilityForm(forms.ModelForm):
    class Meta:
        model = Facility
        fields = [
            "name", "kind", "parish", "description", "address", "latitude", "longitude", "photo", "photo_alt",
            "indoor", "lighting", "capacity", "slot_minutes", "access_level",
            "key_holder_name", "key_holder_place", "key_holder_hours", "key_holder_phone", "key_holder_email",
            "step_free", "adapted_toilet", "adapted_changing", "accessible_parking", "accessibility_notes",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "accessibility_notes": forms.Textarea(attrs={"rows": 2}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parish"].queryset = Parish.objects.for_tenant(tenant)

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and hasattr(photo, "content_type"):
            return clean_image(photo)
        return photo

    def clean(self):
        data = super().clean()
        if data.get("access_level") == 1 and not data.get("key_holder_name"):
            self.add_error("key_holder_name", _("Indica quen custodia a chave (nivel 1)."))
        if data.get("photo") and not data.get("photo_alt"):
            self.add_error("photo_alt", _("Describe a foto para as persoas que non a ven."))
        return data


@role_required(*ADMIN_ROLES)
def facility_list(request):
    facilities = Facility.objects.for_tenant(request.tenant).select_related("parish")
    return render(request, "manage/facilities.html", {"facilities": facilities, "nav": "manage", "sub": "facilities"})


@role_required(*ADMIN_ROLES)
def facility_new(request):
    """Paso 1: escoller plantilla. Paso 2: datos (precargados). Paso 3: revisar e publicar."""
    key = request.GET.get("plantilla") or request.POST.get("plantilla")
    if key not in TEMPLATES:
        return render(request, "manage/facility_new_step1.html", {
            "templates": TEMPLATES, "choices": template_choices(), "nav": "manage", "sub": "facilities",
        })
    t = TEMPLATES[key]
    initial = {k: t[k] for k in ("kind", "capacity", "slot_minutes", "indoor", "lighting", "access_level")}
    initial["description"] = t["description"]
    form = FacilityForm(request.POST or None, request.FILES or None, tenant=request.tenant, initial=initial)
    if request.method == "POST" and form.is_valid():
        facility = form.save(commit=False)
        facility.municipality = request.tenant
        facility.is_published = False
        facility.save()
        apply_template(facility, key, request.user)
        audit("facility.create", request.user, request.tenant, facility, template=key)
        return redirect(treverse(request.tenant, "manage:facility_review", facility.pk))
    return render(request, "manage/facility_new_step2.html", {
        "form": form, "template_key": key, "template": t, "nav": "manage", "sub": "facilities",
    })


@role_required(*ADMIN_ROLES)
def facility_review(request, pk):
    facility = get_object_or_404(Facility, municipality=request.tenant, pk=pk)
    if request.method == "POST":
        facility.is_published = True
        facility.save(update_fields=["is_published"])
        audit("facility.publish", request.user, request.tenant, facility)
        messages.success(request, _("Instalación publicada. Xa se pode reservar."))
        return redirect(treverse(request.tenant, "manage:facility_edit", facility.pk))
    return render(request, "manage/facility_new_step3.html", {
        "facility": facility, "plans": facility.maintenance_plans.prefetch_related("tasks"),
        "nav": "manage", "sub": "facilities",
    })


@role_required(*ADMIN_ROLES)
def facility_edit(request, pk):
    facility = get_object_or_404(Facility, municipality=request.tenant, pk=pk)
    form = FacilityForm(request.POST or None, request.FILES or None, instance=facility, tenant=request.tenant)
    if request.method == "POST" and form.is_valid():
        form.save()
        ensure_lock(facility)
        audit("facility.update", request.user, request.tenant, facility)
        messages.success(request, _("Cambios gardados."))
        return redirect(treverse(request.tenant, "manage:facility_edit", facility.pk))
    return render(request, "manage/facility_edit.html", {
        "facility": facility, "form": form, "nav": "manage", "sub": "facilities", "tab": "data",
    })


HoursFormSet = inlineformset_factory(
    Facility, OpeningHours, fields=["weekday", "opens", "closes", "season_start", "season_end"], extra=2,
    can_delete=True,
    widgets={"opens": forms.TimeInput(attrs={"type": "time"}), "closes": forms.TimeInput(attrs={"type": "time"}),
             "season_start": forms.DateInput(attrs={"type": "date"}), "season_end": forms.DateInput(attrs={"type": "date"})},
)


@role_required(*ADMIN_ROLES)
def facility_hours(request, pk):
    facility = get_object_or_404(Facility, municipality=request.tenant, pk=pk)
    formset = HoursFormSet(request.POST or None, instance=facility)
    if request.method == "POST" and formset.is_valid():
        formset.save()
        audit("facility.hours", request.user, request.tenant, facility)
        messages.success(request, _("Horario gardado."))
        return redirect(treverse(request.tenant, "manage:facility_hours", facility.pk))
    return render(request, "manage/facility_hours.html", {
        "facility": facility, "formset": formset, "nav": "manage", "sub": "facilities", "tab": "hours",
    })


class TariffForm(forms.Form):
    def __init__(self, *args, facility=None, **kwargs):
        super().__init__(*args, **kwargs)
        current = {t.audience: t.price_cents for t in facility.tariffs.all()}
        for value, label in Tariff.Audience.choices:
            cents = current.get(value)
            self.fields[value] = forms.DecimalField(
                label=label, required=value == Tariff.Audience.RESIDENT, min_value=0, max_digits=7, decimal_places=2,
                initial=(cents / 100 if cents is not None else None),
                help_text=gettext_lazy("Euros por franxa. Baleiro = non aplica."),
            )


@role_required(*ADMIN_ROLES)
def facility_tariffs(request, pk):
    facility = get_object_or_404(Facility, municipality=request.tenant, pk=pk)
    form = TariffForm(request.POST or None, facility=facility)
    if request.method == "POST" and form.is_valid():
        for audience, value in form.cleaned_data.items():
            if value is None:
                Tariff.objects.filter(facility=facility, audience=audience).delete()
            else:
                Tariff.objects.update_or_create(facility=facility, audience=audience,
                                                defaults={"price_cents": int(value * 100)})
        audit("facility.tariffs", request.user, request.tenant, facility)
        messages.success(request, _("Tarifas gardadas."))
        return redirect(treverse(request.tenant, "manage:facility_tariffs", facility.pk))
    return render(request, "manage/facility_tariffs.html", {
        "facility": facility, "form": form, "nav": "manage", "sub": "facilities", "tab": "tariffs",
    })


class RulesForm(forms.Form):
    text = forms.CharField(label=gettext_lazy("Normas, dereitos e deberes (unha por liña)"),
                           widget=forms.Textarea(attrs={"rows": 10}))


@role_required(*ADMIN_ROLES)
def facility_rules(request, pk):
    facility = get_object_or_404(Facility, municipality=request.tenant, pk=pk)
    current = facility.current_rules()
    form = RulesForm(request.POST or None, initial={"text": current.text if current else ""})
    if request.method == "POST" and form.is_valid():
        version = RulesVersion.publish(facility, form.cleaned_data["text"], request.user)
        audit("facility.rules", request.user, request.tenant, facility, version=version.version)
        messages.success(request, _("Publicada a versión %(v)s das normas. As reservas novas aceptarán esta versión.") % {"v": version.version})
        return redirect(treverse(request.tenant, "manage:facility_rules", facility.pk))
    return render(request, "manage/facility_rules.html", {
        "facility": facility, "form": form, "versions": facility.rules_versions.all(), "nav": "manage",
        "sub": "facilities", "tab": "rules",
    })


class ClosureForm(forms.ModelForm):
    class Meta:
        model = Closure
        fields = ["facility", "kind", "reason", "starts_at", "ends_at"]
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }
        help_texts = {"facility": gettext_lazy("Baleiro = todas as instalacións do concello (p. ex. festivo).")}

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["facility"].queryset = Facility.objects.for_tenant(tenant)
        self.fields["facility"].required = False
        self.fields["facility"].empty_label = gettext_lazy("Todas as instalacións")

    def clean(self):
        data = super().clean()
        if data.get("starts_at") and data.get("ends_at") and data["ends_at"] <= data["starts_at"]:
            self.add_error("ends_at", _("O fin debe ser posterior ao inicio."))
        return data


@role_required(*ADMIN_ROLES)
def closures(request):
    form = ClosureForm(request.POST or None, tenant=request.tenant)
    if request.method == "POST" and form.is_valid():
        closure = form.save(commit=False)
        closure.municipality = request.tenant
        closure.save()
        affected = apply_closure(closure, by=request.user)
        messages.success(request, _("Peche gardado. %(n)s reservas afectadas foron canceladas, reembolsadas e avisadas.") % {"n": len(affected)})
        return redirect(treverse(request.tenant, "manage:closures"))
    items = Closure.objects.for_tenant(request.tenant).select_related("facility").order_by("-starts_at")[:100]
    return render(request, "manage/closures.html", {"form": form, "closures": items, "nav": "manage", "sub": "closures"})


@role_required(*ADMIN_ROLES)
def closure_delete(request, pk):
    closure = get_object_or_404(Closure, municipality=request.tenant, pk=pk)
    if request.method == "POST":
        audit("closure.delete", request.user, request.tenant, closure)
        closure.delete()
        messages.success(request, _("Peche eliminado."))
    return redirect(treverse(request.tenant, "manage:closures"))
