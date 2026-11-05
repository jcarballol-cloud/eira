# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · C: panel «Procedencia» do concello, «Mobilidade» da deputación e exportacións agregadas."""

from django.http import HttpResponse
from django.shortcuts import render

from apps.accounts.models import audit
from apps.facilities.models import FacilityKind
from apps.tenants.region import region_admin_required
from apps.tenants.urlutils import aggregate_view, role_required

from . import provenance

ROLES = ("admin", "region_admin", "dpo")


def _filter_context(filters):
    return {
        "filters": filters,
        "periods": provenance.PERIODS,
        "kinds": FacilityKind.choices,
        "threshold": provenance.threshold(),
    }


def _export(flows, fmt, name, actor, municipality=None):
    audit("provenance.export", actor, municipality, format=fmt)
    if fmt == "geojson":
        response = HttpResponse(provenance.geojson_text(flows), content_type="application/geo+json")
        response["Content-Disposition"] = f'attachment; filename="{name}.geojson"'
        return response
    response = HttpResponse("﻿" + provenance.csv_text(flows), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{name}.csv"'
    return response


@role_required(*ROLES)
@aggregate_view
def panel(request):
    filters = provenance.clean_filters(request.GET)
    flows = provenance.town_flows(request.tenant, filters["days"], filters["kind"])
    if request.GET.get("formato") in ("csv", "geojson"):
        return _export(flows, request.GET["formato"], "procedencia", request.user, request.tenant)
    map_data, facilities = provenance.town_map(request.tenant, flows)
    return render(
        request,
        "analytics/provenance.html",
        {
            **_filter_context(filters),
            "flows": flows,
            "map": map_data,
            "facilities": facilities,
            "nav": "manage",
            "sub": "provenance",
        },
    )


@region_admin_required
def region_panel(request):
    filters = provenance.clean_filters(request.GET)
    flows = provenance.region_flows(request.region, filters["days"], filters["kind"])
    if request.GET.get("formato") in ("csv", "geojson"):
        return _export(flows, request.GET["formato"], "mobilidade", request.user)
    return render(
        request,
        "region/mobility.html",
        {
            **_filter_context(filters),
            "region": request.region,
            "flows": flows,
            "map": provenance.region_map(request.region, flows),
            "nav": "region_mobility",
        },
    )
