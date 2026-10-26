# SPDX-License-Identifier: EUPL-1.2
"""v1.1 · Rexistro de limpeza.

- Persoal de limpeza (rol `cleaning`), propio ou dunha empresa contratada (`Membership.company`).
- Plans de limpeza co motor de mantemento preventivo: tarefas de tipo «limpeza» por zona,
  frecuencia (varias veces ao día, diaria, semanal) e checklist.
- QR por zona: ao escanealo ábrese o checklist e queda rexistrado quen, cando, que e foto.
- Última limpeza visible na ficha pública e aviso ao concello se unha zona leva demasiado
  tempo sen limpar.
- Enrutado: o que ten a etiqueta «limpeza» xera tarefa para o persoal de limpeza; as avarías
  seguen indo a mantemento; a administración ve todo.
"""

import datetime as dt

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.accounts.models import Membership, Role, audit

from .models import (
    CleaningLog,
    CleaningZone,
    Frequency,
    MaintenancePlan,
    MaintenanceTask,
    TaskKind,
    WorkOrder,
)

Z = CleaningZone.Kind

DEFAULT_CHECKLIST = {
    Z.CHANGING: [
        gettext_lazy("Chan varrido e fregado"),
        gettext_lazy("Duchas e desaugadoiros limpos"),
        gettext_lazy("Bancos e colgadoiros limpos"),
        gettext_lazy("Papeleiras baleiradas"),
    ],
    Z.TOILETS: [
        gettext_lazy("Inodoros e lavabos desinfectados"),
        gettext_lazy("Papel, xabón e secamáns repostos"),
        gettext_lazy("Chan fregado"),
        gettext_lazy("Papeleiras baleiradas"),
    ],
    Z.COURT: [
        gettext_lazy("Pista varrida ou mopeada"),
        gettext_lazy("Sen lixo nin obxectos esquecidos"),
        gettext_lazy("Papeleiras baleiradas"),
    ],
    Z.STANDS: [
        gettext_lazy("Bancadas varridas"),
        gettext_lazy("Varandas limpas"),
        gettext_lazy("Papeleiras baleiradas"),
    ],
    Z.STORAGE: [
        gettext_lazy("Material recollido e ordenado"),
        gettext_lazy("Chan varrido"),
    ],
    Z.POOL: [
        gettext_lazy("Praia do vaso fregada e desinfectada"),
        gettext_lazy("Escumadoiras sen restos"),
        gettext_lazy("Duchas exteriores limpas"),
    ],
    Z.OTHER: [
        gettext_lazy("Zona limpa e recollida"),
        gettext_lazy("Papeleiras baleiradas"),
    ],
}

# Modelos de plan de limpeza por tipo de instalación (alta asistida e botón «Aplicar modelo»):
# (tipo de zona, nome, frecuencia, veces ao día, horas máximas sen limpar). As horas cobren a
# noite (de 19:30 a 8:30 van 13 h), para que non salte o aviso todas as mañás.
TEMPLATES = {
    "sports_hall": [
        (Z.COURT, gettext_lazy("Pista central"), Frequency.DAILY, 1, 30),
        (Z.CHANGING, gettext_lazy("Vestiario 1"), Frequency.SEVERAL, 2, 16),
        (Z.CHANGING, gettext_lazy("Vestiario 2"), Frequency.SEVERAL, 2, 16),
        (Z.TOILETS, gettext_lazy("Aseos"), Frequency.SEVERAL, 3, 16),
        (Z.STANDS, gettext_lazy("Bancadas"), Frequency.WEEKLY, 1, 24 * 8),
        (Z.STORAGE, gettext_lazy("Almacén de material"), Frequency.WEEKLY, 1, 24 * 8),
    ],
    "pool": [
        (Z.POOL, gettext_lazy("Vaso e praia"), Frequency.SEVERAL, 2, 16),
        (Z.CHANGING, gettext_lazy("Vestiarios"), Frequency.SEVERAL, 3, 16),
        (Z.TOILETS, gettext_lazy("Aseos"), Frequency.SEVERAL, 3, 16),
    ],
    "gym": [
        (Z.COURT, gettext_lazy("Sala de máquinas"), Frequency.DAILY, 1, 30),
        (Z.CHANGING, gettext_lazy("Vestiarios"), Frequency.DAILY, 1, 30),
    ],
    "grass_field": [
        (Z.CHANGING, gettext_lazy("Vestiarios"), Frequency.DAILY, 1, 30),
        (Z.STANDS, gettext_lazy("Bancada"), Frequency.WEEKLY, 1, 24 * 8),
    ],
    "padel": [
        (Z.COURT, gettext_lazy("Pista"), Frequency.WEEKLY, 1, 24 * 8),
    ],
    "outdoor_court": [
        (Z.COURT, gettext_lazy("Pista e arredores"), Frequency.WEEKLY, 1, 24 * 8),
    ],
}


def cleaning_staff(municipality):
    return [
        m.user
        for m in Membership.objects.filter(
            municipality=municipality, role=Role.CLEANING
        ).select_related("user")
    ]


def has_cleaning_staff(municipality):
    return Membership.objects.filter(municipality=municipality, role=Role.CLEANING).exists()


def company_of(user, municipality):
    m = (
        Membership.objects.filter(user=user, municipality=municipality, role=Role.CLEANING)
        .exclude(company="")
        .first()
    )
    return m.company if m else ""


def last_cleaning(facility):
    log = facility.cleaning_logs.order_by("-done_at").first()
    return log.done_at if log else None


# ---------------------------------------------------------------------------
# Plans
@transaction.atomic
def apply_template(facility, key=None):
    """Crea as zonas e o plan de limpeza do modelo do tipo de instalación (idempotente por nome)."""
    rows = TEMPLATES.get(key or facility.kind) or TEMPLATES["outdoor_court"]
    plan, _c = MaintenancePlan.objects.get_or_create(
        municipality=facility.municipality,
        facility=facility,
        name=str(gettext_lazy("Plan de limpeza")),
    )
    created = 0
    for kind, name, freq, times, max_hours in rows:
        zone, made = CleaningZone.objects.get_or_create(
            municipality=facility.municipality,
            facility=facility,
            name=str(name),
            defaults={"kind": kind, "max_hours": max_hours},
        )
        if made:
            created += 1
        if not zone.tasks.exists():
            MaintenanceTask.objects.create(
                plan=plan,
                kind=TaskKind.CLEANING,
                zone=zone,
                title=_("Limpeza: %(z)s") % {"z": zone.name},
                frequency=freq,
                times_per_day=times,
                checklist="\n".join(str(i) for i in DEFAULT_CHECKLIST[kind]),
                estimated_minutes=20,
            )
    return created


# ---------------------------------------------------------------------------
# Rexistro
def record(
    *,
    facility,
    user,
    zone=None,
    done_labels=(),
    all_labels=None,
    notes="",
    photo=None,
    at=None,
    order=None,
    source=CleaningLog.Source.QR,
):
    """Garda unha limpeza. Desde o QR, pecha tamén a orde de limpeza pendente máis antiga da zona."""
    labels = list(all_labels if all_labels is not None else done_labels)
    done = set(done_labels)
    now = timezone.now()
    at = at if at and at <= now else now
    log = CleaningLog.objects.create(
        municipality=facility.municipality,
        facility=facility,
        zone=zone,
        user=user,
        by_name=str(user)[:120] if user else "",
        company=company_of(user, facility.municipality) if user else "",
        done_at=at,
        items=[{"label": label, "done": label in done} for label in labels],
        notes=(notes or "").strip()[:500],
        photo=photo or "",
        order=order,
        source=source,
    )
    if zone is not None:
        # Xa non está atrasada: o seguinte atraso volverá avisar
        CleaningZone.objects.filter(pk=zone.pk, alerted_at__isnull=False).update(alerted_at=None)
    if order is None and zone is not None:
        pending = (
            WorkOrder.objects.filter(
                zone=zone, kind="cleaning", due_date__lte=timezone.localdate(at)
            )
            .exclude(status=WorkOrder.Status.DONE)
            .order_by("due_date", "slot")
            .first()
        )
        if pending:
            from .services import close_order

            pending.checklist_state = [
                {"label": i["label"], "done": i["label"] in done}
                for i in (pending.checklist_state or [])
            ]
            pending.save(update_fields=["checklist_state"])
            close_order(pending, user, notes, log=False)
            log.order = pending
            log.save(update_fields=["order"])
    audit("cleaning.log", user, facility.municipality, log, zone=zone.pk if zone else None)
    return log


def parse_queued_at(value):
    """Hora en que se gardou sen conexión (a cola engade `_queued_at`). Ata 7 días atrás."""
    if not value:
        return None
    try:
        at = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timezone.is_naive(at):
        at = timezone.make_aware(at)
    now = timezone.now()
    if at > now or now - at > dt.timedelta(days=7):
        return None
    return at


# ---------------------------------------------------------------------------
# Atrasos
def zone_status(zone, now=None):
    now = now or timezone.now()
    last = zone.last_log()
    last_at = last.done_at if last else None
    hours = (now - last_at).total_seconds() / 3600 if last_at else None
    # Sen ningún rexistro, o prazo conta desde que se creou a zona
    since = last_at or zone.created_at or now
    overdue = zone.active and (now - since).total_seconds() / 3600 > zone.max_hours
    return {"zone": zone, "last": last, "last_at": last_at, "hours": hours, "overdue": overdue}


def overdue_zones(municipality, now=None, facility=None):
    qs = (
        CleaningZone.objects.for_tenant(municipality).filter(active=True).select_related("facility")
    )
    if facility is not None:
        qs = qs.filter(facility=facility)
    rows = [zone_status(z, now) for z in qs]
    return [r for r in rows if r["overdue"]]


def check_overdue(municipality=None, now=None):
    """Avisa (unha vez por atraso) á administración e ao persoal de limpeza."""
    from apps.notifications.services import notify
    from apps.tenants.models import Municipality
    from apps.tenants.urlutils import treverse

    now = now or timezone.now()
    towns = [municipality] if municipality else Municipality.objects.filter(is_active=True)
    sent = 0
    for m in towns:
        rows = overdue_zones(m, now)
        if not rows:
            continue
        admins = [
            ms.user
            for ms in Membership.objects.filter(municipality=m, role=Role.ADMIN).select_related(
                "user"
            )
        ]
        for row in rows:
            zone = row["zone"]
            if zone.alerted_at:
                continue
            title = _("Limpeza atrasada: %(z)s") % {"z": str(zone)}
            body = (
                _("Leva máis de %(h)s horas sen limpar (última: %(d)s).")
                % {
                    "h": zone.max_hours,
                    "d": timezone.localtime(row["last_at"]).strftime("%d/%m %H:%M"),
                }
                if row["last_at"]
                else _("Non hai ningunha limpeza rexistrada.")
            )
            for user in admins:
                notify(
                    user,
                    title,
                    body,
                    url=treverse(m, "manage:cleaning"),
                    municipality=m,
                    level="warning",
                    email=False,
                )
            for user in cleaning_staff(m):
                notify(
                    user,
                    title,
                    body,
                    url=treverse(m, "maintenance:cleaning_zone", zone.token),
                    municipality=m,
                    level="warning",
                    email=False,
                )
            CleaningZone.objects.filter(pk=zone.pk).update(alerted_at=now)
            audit("cleaning.overdue", None, m, zone)
            sent += 1
    return sent


# ---------------------------------------------------------------------------
# Enrutado
def request_cleaning(facility, title, description="", incident=None):
    """Orde de limpeza para hoxe (sen asignar) e aviso ao persoal de limpeza."""
    from apps.notifications.services import notify
    from apps.tenants.urlutils import treverse

    order = WorkOrder.objects.create(
        municipality=facility.municipality,
        facility=facility,
        incident=incident,
        kind="cleaning",
        title=title,
        description=description,
        due_date=timezone.localdate(),
        checklist_state=[
            {"label": _("Limpar a zona indicada"), "done": False},
            {"label": _("Comprobar que queda en bo estado"), "done": False},
        ],
    )
    for user in cleaning_staff(facility.municipality):
        notify(
            user,
            _("Nova tarefa de limpeza: %(f)s") % {"f": facility.name},
            description[:200],
            url=treverse(facility.municipality, "maintenance:order", order.pk),
            municipality=facility.municipality,
            level="warning",
            email=False,
        )
    return order


def route_incident(incident):
    """Incidencia coa etiqueta «limpeza» → tarefa para o persoal de limpeza (se o concello ten).

    Sen persoal de limpeza, a incidencia segue o circuíto de sempre (a administración decide)."""
    from apps.incidents.models import Incident

    if incident.category != Incident.Category.CLEANING:
        return None
    if not has_cleaning_staff(incident.municipality):
        return None
    if incident.work_orders.exists():
        return None
    order = request_cleaning(
        incident.facility,
        _("Incidencia #%(n)s: %(c)s") % {"n": incident.pk, "c": incident.get_category_display()},
        incident.description,
        incident=incident,
    )
    incident.status = Incident.Status.WORK_ORDER
    incident.validated_at = incident.validated_at or timezone.now()
    incident.save(update_fields=["status", "validated_at"])
    audit("incident.route_cleaning", None, incident.municipality, incident, order=order.pk)
    return order


# ---------------------------------------------------------------------------
# Exportación
EXPORT_HEADER = [
    "data",
    "hora",
    "instalacion",
    "zona",
    "persoa",
    "empresa",
    "tarefas_feitas",
    "tarefas_pendentes",
    "observacions",
    "foto",
    "orixe",
]


def export_rows(municipality, start, end, facility=None):
    qs = (
        CleaningLog.objects.for_tenant(municipality)
        .filter(done_at__date__gte=start, done_at__date__lte=end)
        .select_related("facility", "zone")
        .order_by("done_at")
    )
    if facility is not None:
        qs = qs.filter(facility=facility)
    rows = []
    for log in qs:
        local = timezone.localtime(log.done_at)
        rows.append(
            [
                local.strftime("%Y-%m-%d"),
                local.strftime("%H:%M"),
                log.facility.name,
                log.zone.name if log.zone else "",
                log.by_name,
                log.company,
                " · ".join(log.done_items()),
                " · ".join(i["label"] for i in log.items if not i.get("done")),
                log.notes,
                _("si") if log.photo else _("non"),
                log.get_source_display(),
            ]
        )
    return rows


def export_pdf(municipality, start, end, facility=None):
    from apps.bookings.pdf import paged_pdf

    rows = export_rows(municipality, start, end, facility)
    lines = [
        (_("Rexistro de limpeza"), 16, True),
        (
            f"{municipality.name}"
            + (f" · {facility.name}" if facility else f" · {_('todas as instalacións')}"),
            11,
            False,
        ),
        (
            _("Período: %(a)s – %(b)s · %(n)s rexistros")
            % {"a": start.strftime("%d/%m/%Y"), "b": end.strftime("%d/%m/%Y"), "n": len(rows)},
            11,
            False,
        ),
        ("", 6, False),
    ]
    for r in rows:
        who = r[4] + (f" ({r[5]})" if r[5] else "")
        place = r[2] + (f" · {r[3]}" if r[3] else "")
        lines.append((f"{r[0][8:10]}/{r[0][5:7]} {r[1]} · {place} · {who}", 9, True))
        detail = r[6] or _("sen tarefas marcadas")
        if r[7]:
            detail += " · " + _("pendente: %(p)s") % {"p": r[7]}
        if r[8]:
            detail += " · " + r[8]
        for chunk in _wrap(detail, 105):
            lines.append(("    " + chunk, 8, False))
    if not rows:
        lines.append((_("Non hai rexistros neste período."), 10, False))
    return paged_pdf(lines, title=str(_("Rexistro de limpeza")))


def _wrap(text, width):
    out, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out or [""]
