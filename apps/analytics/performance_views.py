# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · D: panel «Rendemento» de cada instalación, inventario de equipos e lecturas reais."""

from django import forms
from django.contrib import messages
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.accounts.models import audit
from apps.facilities.models import EnergyReading, Equipment, Facility
from apps.tenants.urlutils import aggregate_view, role_required, treverse

from . import performance

EquipmentFormSet = inlineformset_factory(
    Facility,
    Equipment,
    fields=["kind", "name", "power_kw", "mode", "use_factor"],
    extra=1,
    can_delete=True,
)


class ReadingForm(forms.ModelForm):
    class Meta:
        model = EnergyReading
        fields = ["period_start", "period_end", "kwh", "cost_cents"]
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "period_end": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def clean(self):
        data = super().clean()
        if (
            data.get("period_start")
            and data.get("period_end")
            and data["period_end"] < data["period_start"]
        ):
            self.add_error("period_end", _("A data final ten que ser posterior á inicial."))
        return data


def _chart(rows, key, label_fmt="%m/%y", unit=" %", top=None):
    values = [float(r[key] or 0) for r in rows]
    top = top or max(values + [1])
    return {
        "bars": [
            {
                "label": r["month"].strftime(label_fmt),
                "pct": round(100 * v / top) if top else 0,
                "display": f"{r[key]}{unit}",
            }
            for r, v in zip(rows, values, strict=True)
        ],
        "scale": "abs" if unit == " %" else "max",
        "top_display": f"{round(top)}{unit}",
    }


@role_required("admin", "region_admin")
@aggregate_view
def facility_performance(request, pk):
    facility = get_object_or_404(
        Facility.objects.prefetch_related("energy_equipment"), municipality=request.tenant, pk=pk
    )
    can_edit = "admin" in request.roles
    formset = EquipmentFormSet(
        request.POST if request.POST.get("accion") == "equipos" else None,
        instance=facility,
        prefix="eq",
    )
    reading_form = ReadingForm(request.POST if request.POST.get("accion") == "lectura" else None)
    if request.method == "POST" and can_edit:
        if request.POST.get("accion") == "equipos" and formset.is_valid():
            formset.save()
            audit("facility.equipment", request.user, request.tenant, facility)
            messages.success(request, _("Inventario de equipos gardado."))
            return redirect(
                treverse(request.tenant, "manage:facility_performance", facility.pk) + "#equipos"
            )
        if request.POST.get("accion") == "lectura" and reading_form.is_valid():
            reading = reading_form.save(commit=False)
            reading.facility = facility
            reading.save()
            audit("facility.energy_reading", request.user, request.tenant, facility)
            messages.success(request, _("Lectura gardada."))
            return redirect(
                treverse(request.tenant, "manage:facility_performance", facility.pk) + "#lecturas"
            )
    panel = performance.facility_panel(facility)
    trend = panel["trend"]
    return render(
        request,
        "manage/facility_performance.html",
        {
            "facility": facility,
            "p": panel,
            "occ_chart": _chart(trend, "occupancy_pct", top=100),
            "use_chart": _chart(trend, "real_use_pct", top=100),
            "kwh_chart": _chart(trend, "kwh", unit=" kWh"),
            "formset": formset,
            "reading_form": reading_form,
            "can_edit": can_edit,
            "nav": "manage",
            "sub": "facilities",
            "tab": "performance",
            "themable": True,
        },
    )


@role_required("admin", "region_admin")
@aggregate_view
def overview(request):
    """Rendemento de todas as instalacións do concello (últimos 30 días)."""
    import datetime as dt

    from django.utils import timezone

    today = timezone.localdate()
    rows = []
    for f in Facility.objects.for_tenant(request.tenant).prefetch_related("energy_equipment"):
        rows.append(
            {
                "f": f,
                "s": performance.period_stats(
                    f, today - dt.timedelta(days=29), today + dt.timedelta(days=1)
                ),
            }
        )
    return render(
        request,
        "manage/performance.html",
        {"rows": rows, "nav": "manage", "sub": "performance", "themable": True},
    )
