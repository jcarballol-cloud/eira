# SPDX-License-Identifier: EUPL-1.2
"""Datos abertos: ocupación anonimizada (CSV) con metadatos DCAT-AP básicos (JSON-LD)."""

import csv
import datetime as dt
import json
from collections import Counter

from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Booking
from apps.tenants.urlutils import module_required

from .indicators import USED


def _rows(tenant, weeks=8):
    """Reservas agregadas por instalación, día e hora. Non hai ningún dato persoal."""
    since = timezone.now() - dt.timedelta(weeks=weeks)
    counter = Counter()
    for fid, fname, kind, start in (
        Booking.objects.for_tenant(tenant)
        .filter(start__gte=since, start__lt=timezone.now(), status__in=USED)
        .values_list("facility_id", "facility__name", "facility__kind", "start")
    ):
        local = timezone.localtime(start)
        counter[(fid, fname, kind, local.date().isoformat(), local.hour)] += 1
    return sorted(counter.items(), key=lambda kv: (kv[0][3], kv[0][4], kv[0][1]))


@module_required("opendata")
def index(request):
    return render(
        request,
        "analytics/open_data.html",
        {
            "dcat_url": reverse("open_data:dcat", args=[request.tenant.slug]),
            "csv_url": reverse("open_data:csv", args=[request.tenant.slug]),
        },
    )


@module_required("opendata")
def occupancy_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="ocupacion-{request.tenant.slug}.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["concello_ine", "instalacion_id", "instalacion", "tipo", "data", "hora", "reservas"]
    )
    for (fid, fname, kind, day, hour), n in _rows(request.tenant):
        writer.writerow([request.tenant.ine_code, fid, fname, kind, day, f"{hour:02d}:00", n])
    return response


@module_required("opendata")
def dcat(request):
    t = request.tenant
    base = request.build_absolute_uri("/")[:-1]
    csv_url = base + reverse("open_data:csv", args=[t.slug])
    data = {
        "@context": {
            "dcat": "http://www.w3.org/ns/dcat#",
            "dct": "http://purl.org/dc/terms/",
            "foaf": "http://xmlns.com/foaf/0.1/",
        },
        "@type": "dcat:Dataset",
        "@id": base + reverse("open_data:dcat", args=[t.slug]),
        "dct:title": {
            "@language": "gl",
            "@value": f"Ocupación das instalacións deportivas de {t.name}",
        },
        "dct:description": {
            "@language": "gl",
            "@value": "Número de reservas por instalación, día e hora. Datos agregados sen información persoal.",
        },
        "dct:publisher": {"@type": "foaf:Organization", "foaf:name": f"Concello de {t.name}"},
        "dct:license": "http://creativecommons.org/licenses/by/4.0/",
        "dct:accrualPeriodicity": "http://publications.europa.eu/resource/authority/frequency/DAILY",
        "dct:spatial": f"INE:{t.ine_code}" if t.ine_code else t.name,
        "dct:modified": timezone.now().date().isoformat(),
        "dcat:theme": "http://publications.europa.eu/resource/authority/data-theme/SOCI",
        "dcat:keyword": ["deporte", "instalacións municipais", "ocupación"],
        "dcat:distribution": [
            {
                "@type": "dcat:Distribution",
                "dcat:accessURL": csv_url,
                "dcat:downloadURL": csv_url,
                "dct:format": "http://publications.europa.eu/resource/authority/file-type/CSV",
                "dcat:mediaType": "text/csv",
            }
        ],
    }
    if not t.module_enabled("opendata"):
        raise Http404
    return HttpResponse(
        json.dumps(data, ensure_ascii=False, indent=2), content_type="application/ld+json"
    )
