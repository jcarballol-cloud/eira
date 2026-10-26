# SPDX-License-Identifier: EUPL-1.2
"""v1.1 · Vistas do rexistro de limpeza: QR da zona (app móbil), páxina do concello e exportación."""

import datetime as dt

from django import forms
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.facilities.models import Facility
from apps.tenants.uploads import clean_image
from apps.tenants.urlutils import role_required, treverse

from . import cleaning
from .models import CleaningLog, CleaningZone

ADMIN_ROLES = ("admin", "region_admin")
# Quen pode rexistrar unha limpeza ao escanear o QR
CLEANERS = {"cleaning", "maintenance", "admin"}


class ZoneLogForm(forms.Form):
    notes = forms.CharField(
        label=gettext_lazy("Observacións (opcional)"),
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    photo = forms.ImageField(
        label=gettext_lazy("Foto (opcional)"),
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": "image/*", "capture": "environment"}),
    )

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        return clean_image(photo) if photo else None


def cleaning_zone(request, token):
    """QR pegado na zona. Persoal: checklist e rexistro. Resto: só a última limpeza (pública)."""
    zone = get_object_or_404(
        CleaningZone.objects.select_related("facility"),
        municipality=request.tenant,
        token=token,
    )
    can_log = bool(request.roles & CLEANERS)
    status = cleaning.zone_status(zone)
    if not can_log:
        if request.method == "POST":
            if request.headers.get("X-Eira-Sync") == "1":
                return HttpResponse(status=403)
            raise Http404
        return render(request, "maintenance/cleaning_zone_public.html", {"zone": zone, **status})
    items = zone.checklist_items()
    synced = request.headers.get("X-Eira-Sync") == "1"
    form = ZoneLogForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            done = {int(i) for i in request.POST.getlist("done") if i.isdigit()}
            cleaning.record(
                facility=zone.facility,
                user=request.user,
                zone=zone,
                done_labels=[label for i, label in enumerate(items) if i in done],
                all_labels=items,
                notes=form.cleaned_data["notes"],
                photo=form.cleaned_data.get("photo"),
                at=cleaning.parse_queued_at(request.POST.get("_queued_at")),
            )
            if synced:
                return HttpResponse(status=204)
            messages.success(request, _("Limpeza rexistrada. Grazas!"))
            return redirect(treverse(request.tenant, "maintenance:my_orders"))
        if synced:
            return HttpResponse(status=409)
    recent = zone.logs.order_by("-done_at")[:5]
    return render(
        request,
        "maintenance/cleaning_zone.html",
        {"zone": zone, "items": items, "form": form, "recent": recent, "nav": "operator", **status},
    )


# ---------------------------------------------------------------------------
# Concello
class ZoneForm(forms.ModelForm):
    class Meta:
        model = CleaningZone
        fields = ["facility", "name", "kind", "max_hours"]

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["facility"].queryset = Facility.objects.filter(municipality=tenant)


class ExportForm(forms.Form):
    facility = forms.ModelChoiceField(
        label=gettext_lazy("Instalación"), queryset=None, required=False
    )
    start = forms.DateField(
        label=gettext_lazy("Desde"), widget=forms.DateInput(attrs={"type": "date"})
    )
    end = forms.DateField(label=gettext_lazy("Ata"), widget=forms.DateInput(attrs={"type": "date"}))
    fmt = forms.ChoiceField(
        label=gettext_lazy("Formato"),
        choices=[("csv", "CSV"), ("ods", "ODS"), ("pdf", "PDF")],
        initial="pdf",
    )

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["facility"].queryset = Facility.objects.filter(municipality=tenant)
        self.fields["facility"].empty_label = gettext_lazy("Todas")

    def clean(self):
        d = super().clean()
        if d.get("start") and d.get("end") and d["start"] > d["end"]:
            raise forms.ValidationError(_("A data de inicio ten que ser anterior á de fin."))
        if d.get("start") and d.get("end") and (d["end"] - d["start"]).days > 400:
            raise forms.ValidationError(_("Exporta como moito un ano de cada vez."))
        return d


@role_required(*ADMIN_ROLES)
def manage_cleaning(request):
    tenant = request.tenant
    cleaning.check_overdue(tenant)
    zone_form = ZoneForm(
        request.POST if request.POST.get("action") == "zone" else None, tenant=tenant
    )
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "zone" and zone_form.is_valid():
            zone = zone_form.save(commit=False)
            zone.municipality = tenant
            zone.save()
            messages.success(request, _("Zona creada. Imprime o seu QR e pégao na parede."))
            return redirect(treverse(tenant, "manage:cleaning"))
        if action == "template":
            facility = get_object_or_404(Facility, municipality=tenant, pk=request.POST.get("f"))
            n = cleaning.apply_template(facility)
            messages.success(
                request,
                _("Aplicado o modelo de limpeza a %(f)s: %(n)s zonas novas.")
                % {"f": facility.name, "n": n},
            )
            return redirect(treverse(tenant, "manage:cleaning"))
        if action == "toggle":
            zone = get_object_or_404(CleaningZone, municipality=tenant, pk=request.POST.get("z"))
            zone.active = not zone.active
            zone.save(update_fields=["active"])
            messages.success(request, _("Zona actualizada."))
            return redirect(treverse(tenant, "manage:cleaning"))
    now = timezone.now()
    zones = (
        CleaningZone.objects.for_tenant(tenant)
        .select_related("facility")
        .prefetch_related("tasks")
        .order_by("facility__name", "name")
    )
    by_facility = {}
    for z in zones:
        by_facility.setdefault(z.facility, []).append(cleaning.zone_status(z, now))
    today = timezone.localdate()
    export_form = ExportForm(
        tenant=tenant, prefix="x", initial={"start": today - dt.timedelta(days=30), "end": today}
    )
    from apps.accounts.models import Membership, Role

    return render(
        request,
        "manage/cleaning.html",
        {
            "by_facility": by_facility,
            "overdue": [r for rows in by_facility.values() for r in rows if r["overdue"]],
            "logs": CleaningLog.objects.for_tenant(tenant).select_related("facility", "zone")[:20],
            "staff": Membership.objects.filter(municipality=tenant, role=Role.CLEANING)
            .select_related("user")
            .order_by("company"),
            "zone_form": zone_form,
            "export_form": export_form,
            "facilities_without": Facility.objects.filter(municipality=tenant)
            .exclude(cleaning_zones__isnull=False)
            .order_by("name"),
            "nav": "manage",
            "sub": "cleaning",
        },
    )


@role_required(*ADMIN_ROLES)
def cleaning_export(request):
    from apps.analytics.views import _csv

    form = ExportForm(request.GET or None, tenant=request.tenant, prefix="x")
    if not form.is_valid():
        messages.error(
            request, " ".join(str(e) for errs in form.errors.values() for e in errs) or _("Erro")
        )
        return redirect(treverse(request.tenant, "manage:cleaning"))
    d = form.cleaned_data
    name = f"rexistro-limpeza-{d['start']:%Y%m%d}-{d['end']:%Y%m%d}"
    if d["fmt"] == "pdf":
        response = HttpResponse(
            cleaning.export_pdf(request.tenant, d["start"], d["end"], d["facility"]),
            content_type="application/pdf",
        )
        response["Content-Disposition"] = f'attachment; filename="{name}.pdf"'
        return response
    rows = cleaning.export_rows(request.tenant, d["start"], d["end"], d["facility"])
    return _csv(f"{name}.csv", cleaning.EXPORT_HEADER, rows, ods=d["fmt"] == "ods")


@role_required(*ADMIN_ROLES)
def zone_qr(request, pk):
    from apps.access.views import qr_svg

    zone = get_object_or_404(
        CleaningZone.objects.select_related("facility"), municipality=request.tenant, pk=pk
    )
    url = request.build_absolute_uri(
        treverse(request.tenant, "maintenance:cleaning_zone", zone.token)
    )
    return render(
        request,
        "manage/cleaning_qr.html",
        {"zone": zone, "url": url, "svg": qr_svg(url), "nav": "manage", "sub": "cleaning"},
    )
