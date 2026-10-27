# SPDX-License-Identifier: EUPL-1.2
"""v1.3 · C: consulta do rexistro de auditoría (AuditLog) na xestión do concello.

Só a administración do concello e a persoa delegada de protección de datos (o mesmo criterio ca o
rexistro de brechas: a deputación non entra nin co acceso de soporte). Ademais, toda descarga de
ficheiros feita polo persoal queda rexistrada (`ExportAuditMiddleware`)."""

import csv
import datetime as dt

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from .breaches import breach_access
from .models import AuditLog, audit
from .profiles import STAFF_ROLES

# Categoría → prefixos ou accións exactas
CATEGORIES = {
    "tarifas": (
        gettext_lazy("Tarifas, prezos e configuración"),
        ("facility.tariffs", "pass_type.", "voucher_type.", "tenant.settings", "facility.rules"),
    ),
    "permisos": (
        gettext_lazy("Persoal e permisos"),
        ("tenant.staff_", "tenant.invite", "eligibility.", "2fa.reset", "residency.issue"),
    ),
    "exportacions": (
        gettext_lazy("Exportacións e descargas"),
        ("export.", "tenant.export", "tenant.import", "account.export", "audit.export"),
    ),
    "soporte": (gettext_lazy("Acceso de soporte da deputación"), ("support.",)),
    "brechas": (gettext_lazy("Brechas de seguridade"), ("breach.",)),
    "accidentes": (gettext_lazy("Accidentes e alertas"), ("accident.", "alert.", "closing.")),
    "contas": (gettext_lazy("Accesos e dobre factor"), ("auth.", "2fa.")),
}

LABELS = {
    "facility.tariffs": gettext_lazy("Cambio de tarifas"),
    "facility.rules": gettext_lazy("Novas normas de uso"),
    "pass_type.create": gettext_lazy("Novo tipo de abono"),
    "voucher_type.create": gettext_lazy("Novo tipo de bono"),
    "tenant.settings": gettext_lazy("Cambio na configuración do concello"),
    "tenant.staff_add": gettext_lazy("Rol asignado"),
    "tenant.staff_remove": gettext_lazy("Rol retirado"),
    "tenant.invite": gettext_lazy("Invitación á administración"),
    "eligibility.validate": gettext_lazy("Tarifa reducida validada"),
    "residency.issue": gettext_lazy("Código de empadroamento emitido"),
    "export.download": gettext_lazy("Descarga dun ficheiro"),
    "tenant.export": gettext_lazy("Exportación íntegra do concello"),
    "tenant.import": gettext_lazy("Importación de datos"),
    "account.export": gettext_lazy("Descarga dos datos propios"),
    "audit.export": gettext_lazy("Descarga do rexistro de auditoría"),
    "support.request": gettext_lazy("A deputación pide acceso de soporte"),
    "support.grant": gettext_lazy("Acceso de soporte autorizado"),
    "support.revoke": gettext_lazy("Acceso de soporte revogado"),
    "support.view": gettext_lazy("Páxina vista co acceso de soporte"),
    "breach.save": gettext_lazy("Brecha rexistrada ou actualizada"),
    "accident.register": gettext_lazy("Accidente rexistrado"),
    "accident.close": gettext_lazy("Accidente pechado no rexistro"),
    "alert.accident": gettext_lazy("Alerta: accidente deportivo"),
    "alert.security": gettext_lazy("Alerta: emerxencia de seguridade"),
    "alert.ack": gettext_lazy("Alerta atendida"),
    "closing.escalated": gettext_lazy("Peche sen confirmar: aviso á persoa responsable"),
    "closing.police_contact": gettext_lazy("Contacto coa Policía Local"),
    "closing.resolved": gettext_lazy("Peche sen confirmar resolto"),
    "auth.login": gettext_lazy("Inicio de sesión"),
    "auth.2fa": gettext_lazy("Segundo factor correcto"),
    "2fa.enable": gettext_lazy("Dobre factor activado"),
    "2fa.disable": gettext_lazy("Dobre factor desactivado"),
    "2fa.reset": gettext_lazy("Dobre factor restablecido por outra persoa"),
    "2fa.failed": gettext_lazy("Código do segundo factor incorrecto"),
    "2fa.locked": gettext_lazy("Segundo factor bloqueado por intentos"),
    "2fa.recovery_regenerate": gettext_lazy("Códigos de recuperación novos"),
}

PER_PAGE = 50


def _matches(action, prefixes):
    return any(action == p or (p.endswith((".", "_")) and action.startswith(p)) for p in prefixes)


def category_of(action):
    for key, (_label, prefixes) in CATEGORIES.items():
        if _matches(action, prefixes):
            return key
    return ""


def _filter(qs, category):
    if category not in CATEGORIES:
        return qs
    from django.db.models import Q

    q = Q()
    for p in CATEGORIES[category][1]:
        q |= Q(action__startswith=p) if p.endswith((".", "_")) else Q(action=p)
    return qs.filter(q)


def entries_for(tenant, category="", day_from=None, day_to=None):
    """Entradas do concello e, ademais, os accesos e o dobre factor do seu persoal de xestión (esas
    gárdanse sen concello porque son da conta, non dun concello concreto)."""
    from django.db.models import Q

    from .models import Membership, Role

    staff = Membership.objects.filter(municipality=tenant).exclude(role=Role.CITIZEN)
    own_accounts = Q(
        municipality__isnull=True,
        actor__in=staff.values("user"),
    ) & (Q(action__startswith="auth.") | Q(action__startswith="2fa."))
    qs = AuditLog.objects.filter(Q(municipality=tenant) | own_accounts).select_related("actor")
    qs = _filter(qs, category)
    if day_from:
        qs = qs.filter(at__date__gte=day_from)
    if day_to:
        qs = qs.filter(at__date__lte=day_to)
    return qs


def _parse_day(value):
    try:
        return dt.date.fromisoformat(value or "")
    except ValueError:
        return None


def describe(entry):
    detail = ", ".join(
        f"{k}: {v}" for k, v in (entry.detail or {}).items() if v not in ("", None, [], {})
    )
    return {
        "entry": entry,
        "label": LABELS.get(entry.action, entry.action),
        "category": CATEGORIES.get(category_of(entry.action), ("",))[0],
        "actor": (entry.actor.display_name or entry.actor.email) if entry.actor else _("Sistema"),
        "object": f"{entry.object_type} #{entry.object_id}" if entry.object_type else "",
        "detail": detail[:300],
    }


@breach_access
def audit_log(request):
    t = request.tenant
    category = request.GET.get("categoria", "")
    day_from = _parse_day(request.GET.get("desde"))
    day_to = _parse_day(request.GET.get("ata"))
    qs = entries_for(t, category, day_from, day_to)
    if request.GET.get("formato") == "csv":
        audit("audit.export", request.user, t, category=category or "todo")
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="auditoria-{t.slug}-{timezone.localdate():%Y%m%d}.csv"'
        )
        response.write("﻿")
        w = csv.writer(response)
        w.writerow(["data", "categoria", "accion", "codigo", "persoa", "obxecto", "detalle"])
        for e in qs[:5000]:
            d = describe(e)
            w.writerow(
                [
                    timezone.localtime(e.at).strftime("%Y-%m-%d %H:%M:%S"),
                    d["category"],
                    d["label"],
                    e.action,
                    d["actor"],
                    d["object"],
                    d["detail"],
                ]
            )
        response.eira_audited = True  # xa rexistrado como audit.export
        return response
    page = Paginator(qs, PER_PAGE).get_page(request.GET.get("paxina"))
    query = "&".join(
        f"{k}={v}"
        for k, v in (
            ("categoria", category),
            ("desde", day_from.isoformat() if day_from else ""),
            ("ata", day_to.isoformat() if day_to else ""),
        )
        if v
    )
    return render(
        request,
        "manage/audit.html",
        {
            "page": page,
            "rows": [describe(e) for e in page.object_list],
            "categories": [(k, v[0]) for k, v in CATEGORIES.items()],
            "category": category,
            "day_from": day_from,
            "day_to": day_to,
            "query": query,
            "nav": "manage",
            "sub": "audit",
        },
    )


class ExportAuditMiddleware:
    """Toda descarga (`Content-Disposition: attachment`) que fai o persoal dun concello ou da
    deputación queda en AuditLog como `export.download` (ficheiro e ruta, sen contido)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        disposition = response.get("Content-Disposition", "")
        if (
            not disposition.startswith("attachment")
            or response.status_code != 200
            or getattr(response, "eira_audited", False)
        ):
            return response
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return response
        staff = bool(getattr(request, "roles", set()) & STAFF_ROLES) or request.path.startswith(
            "/rexion/"
        )
        if staff:
            filename = (
                disposition.split("filename=", 1)[-1].strip('"')
                if "filename=" in disposition
                else ""
            )
            audit(
                "export.download",
                user,
                getattr(request, "tenant", None),
                file=filename[:120],
                path=request.path[:200],
            )
        return response
