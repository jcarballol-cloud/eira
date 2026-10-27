# SPDX-License-Identifier: EUPL-1.2
import datetime as dt

from django import forms
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.bookings.services import week_grid
from apps.tenants.models import tile_settings
from apps.tenants.urlutils import treverse

from .models import Facility, FacilityKind, Parish


class FilterForm(forms.Form):
    q = forms.CharField(label=_("Buscar"), required=False)
    kind = forms.ChoiceField(label=_("Tipo"), required=False)
    parish = forms.ChoiceField(label=_("Parroquia"), required=False)
    accessible = forms.BooleanField(label=_("Acceso sen chanzos"), required=False)
    lighting = forms.BooleanField(label=_("Con iluminación"), required=False)
    indoor = forms.BooleanField(label=_("Cuberta"), required=False)
    # v1.2 · C
    full_access = forms.BooleanField(label=_("Accesible"), required=False)
    bikes = forms.BooleanField(label=_("Con aparcabicis"), required=False)
    aed = forms.BooleanField(label=_("Con DESA"), required=False)

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kind"].choices = [("", _("Todos"))] + list(FacilityKind.choices)
        self.fields["parish"].choices = [("", _("Todas"))] + [
            (str(p.pk), p.name) for p in Parish.objects.for_tenant(tenant)
        ]


def home(request):
    tenant = request.tenant
    form = FilterForm(request.GET or None, tenant=tenant)
    qs = (
        Facility.objects.for_tenant(tenant)
        .filter(is_published=True)
        .select_related("parish")
        .prefetch_related("tariffs")
    )
    if form.is_valid():
        d = form.cleaned_data
        if d["q"]:
            qs = qs.filter(name__icontains=d["q"])
        if d["kind"]:
            qs = qs.filter(kind=d["kind"])
        if d["parish"]:
            qs = qs.filter(parish_id=d["parish"])
        if d["accessible"]:
            qs = qs.filter(step_free=True)
        if d["lighting"]:
            qs = qs.filter(lighting=True)
        if d["indoor"]:
            qs = qs.filter(indoor=True)
        # v1.2 · C: «accesible» = itinerario desde o exterior e corredores/portas con «si»
        if d["full_access"]:
            qs = qs.filter(
                accessibility_detail__route__value="yes", accessibility_detail__widths__value="yes"
            )
        if d["bikes"]:
            qs = qs.filter(bike_parking_spaces__gt=0)
        if d["aed"]:
            qs = qs.filter(aed_on_site=True)
    facilities = list(qs)
    tiles = tile_settings(tenant)
    # v5: selector de concello (o propio e os da rede abertos)
    from apps.tenants.network import switcher

    towns = switcher(request.user, tenant)
    # v4: filtros activos (sen contar a busca, que se ve no campo) con ligazón para quitar cada un
    active = []
    if form.is_valid():
        d = form.cleaned_data
        for name in (
            "kind",
            "parish",
            "accessible",
            "lighting",
            "indoor",
            "full_access",
            "bikes",
            "aed",
        ):
            if d.get(name):
                field = form.fields[name]
                label = (
                    dict(field.choices).get(d[name], d[name])
                    if isinstance(field, forms.ChoiceField)
                    else field.label
                )
                rest = request.GET.copy()
                rest.pop(name, None)
                active.append({"name": name, "label": label, "remove": "?" + rest.urlencode()})
    geo = {
        "type": "FeatureCollection",
        "tiles": tiles["url"],
        "attribution": tiles["attribution"],
        "attribution_url": tiles["attribution_url"],
        "icon": static("vendor/leaflet/images/marker-icon.png"),
        "icon2x": static("vendor/leaflet/images/marker-icon-2x.png"),
        "shadow": static("vendor/leaflet/images/marker-shadow.png"),
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(f.longitude), float(f.latitude)],
                },
                "properties": {
                    "name": f.name,
                    "kind": str(f.get_kind_display()),
                    "parish": f.parish.name if f.parish else "",
                    "url": treverse(tenant, "facilities:detail", f.pk),
                },
            }
            for f in facilities
            if f.latitude is not None and f.longitude is not None
        ],
    }
    return render(
        request,
        "facilities/home.html",
        {
            "form": form,
            "facilities": facilities,
            "geo": geo,
            "nav": "facilities",
            "view": request.GET.get("vista", "lista"),
            "active": active,
            "towns": towns if len(towns) > 1 else [],
        },
    )


def _monday(day):
    return day - dt.timedelta(days=day.weekday())


def detail(request, pk):
    tenant = request.tenant
    facility = get_object_or_404(
        Facility.objects.select_related("parish").prefetch_related("opening_hours", "tariffs"),
        municipality=tenant,
        pk=pk,
        is_published=True,
    )
    today = timezone.localdate()
    try:
        week = dt.date.fromisoformat(request.GET.get("semana", ""))
    except ValueError:
        week = today
    monday = _monday(max(week, _monday(today)))
    grid = week_grid(facility, monday, request.user)
    max_monday = _monday(today + dt.timedelta(days=tenant.max_advance_days))
    ctx = {
        "facility": facility,
        "grid": grid,
        "monday": monday,
        "nav": "facilities",
        "prev_week": monday - dt.timedelta(days=7) if monday > _monday(today) else None,
        "next_week": monday + dt.timedelta(days=7) if monday < max_monday else None,
        "rules": facility.current_rules(),
        "tariffs": facility.tariffs.all(),
        "hours": facility.opening_hours.all(),
    }
    if not request.headers.get("HX-Request"):
        # v5: índice de vida activa, última supervisión e revisión de seguridade
        from apps.analytics.vitality import facility_index, level

        idx = facility_index(facility)
        ctx.update(
            {
                "vitality": idx,
                "vitality_level": level(idx["value"]),
                "last_supervision": facility.last_supervision(),
                "last_cleaning": facility.last_cleaning(),  # v1.1
                "safety_review": facility.safety_review(),
            }
        )
    template = (
        "facilities/_week.html" if request.headers.get("HX-Request") else "facilities/detail.html"
    )
    return render(request, template, ctx)
