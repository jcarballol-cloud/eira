# SPDX-License-Identifier: EUPL-1.2
import csv

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _

from apps.tenants.urlutils import role_required

from . import indicators

ADMIN_ROLES = ("admin", "region_admin")


def _csv(filename, header, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")  # BOM para que as follas de cálculo detecten UTF-8
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response


@role_required(*ADMIN_ROLES)
def dashboard(request):
    weeks = 8 if request.GET.get("semanas") == "8" else 4
    s = indicators.summary(request.tenant, weeks)
    fmt = request.GET.get("csv")
    if fmt == "ocupacion":
        return _csv(
            "ocupacion.csv",
            ["instalacion", "prazas_ofertadas", "reservas", "ocupacion_pct", "non_presentadas"],
            [
                [r["facility"], r["available"], r["booked"], r["pct"], r["no_shows"]]
                for r in s["occupancy"]
            ],
        )
    if fmt == "franxas":
        days = ["luns", "martes", "mercores", "xoves", "venres", "sabado", "domingo"]
        return _csv(
            "ocupacion-franxas.csv",
            ["hora", *days],
            [
                [f"{row['hour']:02d}:00", *[c["value"] for c in row["cells"]]]
                for row in s["heatmap"]
            ],
        )
    if fmt == "ingresos":
        return _csv(
            "ingresos.csv",
            ["semana", "cobrado_eur", "devolto_eur", "neto_eur"],
            [
                [r["week"], r["paid"] / 100, r["refunded"] / 100, r["net"] / 100]
                for r in s["revenue_weeks"]
            ],
        )
    if fmt == "incidencias":
        return _csv(
            "incidencias.csv",
            ["estado", "total"],
            [[str(k), v] for k, v in s["incidents"]["by_status"]],
        )
    occ_chart = indicators.hbar(s["occupancy"], "pct", "facility", suffix=" %")
    ns_chart = indicators.hbar(
        [r for r in s["occupancy"] if r["booked"]], "no_show_pct", "facility", suffix=" %"
    )
    rev_items = [
        {"label": r["week"].strftime("%d/%m"), "value": round(r["net"] / 100)}
        for r in s["revenue_weeks"]
    ]
    rev_chart = indicators.hbar(rev_items, "value", "label", label_w=80, suffix=" €")
    ai_summary = None
    if request.tenant.module_enabled("ai_summary") and settings.EIRA_AI_ENABLED:
        from apps.integrations.registry import get_adapter

        try:
            ai_summary = get_adapter("ai").weekly_summary(indicators.ai_aggregates(request.tenant))
        except Exception:  # o asistente é opcional: nunca rompe o panel
            ai_summary = _("O asistente non está dispoñible agora.")
    return render(
        request,
        "analytics/dashboard.html",
        {
            "s": s,
            "weeks": weeks,
            "occ_chart": occ_chart,
            "ns_chart": ns_chart,
            "rev_chart": rev_chart,
            "weekdays": [_("Lu"), _("Ma"), _("Mé"), _("Xo"), _("Ve"), _("Sá"), _("Do")],
            "ai_summary": ai_summary,
            "nav": "manage",
            "sub": "indicators",
        },
    )
