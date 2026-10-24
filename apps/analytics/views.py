# SPDX-License-Identifier: EUPL-1.2
import csv

from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _

from apps.tenants.urlutils import aggregate_view, role_required

from . import indicators

ADMIN_ROLES = ("admin", "region_admin")


def _csv(filename, header, rows, ods=False):
    if ods:
        from .ods import write_ods

        name = filename.replace(".csv", ".ods")
        response = HttpResponse(
            write_ods(name[:-4], header, rows),
            content_type="application/vnd.oasis.opendocument.spreadsheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{name}"'
        return response
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")  # BOM para que as follas de cálculo detecten UTF-8
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response


@role_required(*ADMIN_ROLES)
@aggregate_view
def dashboard(request):
    weeks = 8 if request.GET.get("semanas") == "8" else 4
    s = indicators.summary(request.tenant, weeks)
    fmt = request.GET.get("csv") or request.GET.get("ods")
    ods = bool(request.GET.get("ods"))
    if fmt == "ocupacion":
        return _csv(
            "ocupacion.csv",
            ["instalacion", "prazas_ofertadas", "reservas", "ocupacion_pct", "non_presentadas"],
            [
                [r["facility"], r["available"], r["booked"], r["pct"], r["no_shows"]]
                for r in s["occupancy"]
            ],
            ods=ods,
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
            ods=ods,
        )
    if fmt == "ingresos":
        return _csv(
            "ingresos.csv",
            ["semana", "cobrado_eur", "devolto_eur", "neto_eur"],
            [
                [r["week"].isoformat(), r["paid"] / 100, r["refunded"] / 100, r["net"] / 100]
                for r in s["revenue_weeks"]
            ],
            ods=ods,
        )
    if fmt == "incidencias":
        return _csv(
            "incidencias.csv",
            ["estado", "total"],
            [[str(k), v] for k, v in s["incidents"]["by_status"]],
            ods=ods,
        )
    occ_chart = indicators.hbar(s["occupancy"], "pct", "facility", suffix=" %", scale="percent")
    ns_chart = indicators.hbar(
        [r for r in s["occupancy"] if r["booked"]],
        "no_show_pct",
        "facility",
        suffix=" %",
        scale="percent",
    )
    rev_items = [
        {"label": r["week"].strftime("%d/%m"), "value": round(r["net"] / 100)}
        for r in s["revenue_weeks"]
    ]
    rev_chart = indicators.hbar(rev_items, "value", "label", suffix=" €")
    from apps.integrations.ai import FakeAIAdapter
    from apps.integrations.registry import get_adapter

    from . import ai_summary as ai

    summary_text = ai.cached(request.tenant)
    if request.method == "POST" and request.POST.get("action") == "ai":
        summary_text = ai.generate(request.tenant) or _("O asistente non está dispoñible agora.")
    elif (
        summary_text is None
        and ai.enabled(request.tenant)
        and isinstance(get_adapter("ai"), FakeAIAdapter)
    ):
        summary_text = ai.generate(request.tenant)  # o resumo por regras é instantáneo
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
            "ai_summary": summary_text,
            "ai_enabled": ai.enabled(request.tenant),
            "nav": "manage",
            "sub": "indicators",
        },
    )
