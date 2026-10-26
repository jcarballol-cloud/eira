# SPDX-License-Identifier: EUPL-1.2
"""Ciclo das incidencias: recibida → validada → orde de traballo → resolta (con aviso a quen informou)."""

from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import Membership, Role, audit
from apps.notifications.services import notify

from .models import Incident


def _staff(municipality, roles):
    return [
        m.user
        for m in Membership.objects.filter(
            municipality=municipality, role__in=roles
        ).select_related("user")
    ]


def notify_staff_new_incident(incident):
    from apps.maintenance.cleaning import route_incident
    from apps.tenants.urlutils import treverse

    url = treverse(incident.municipality, "manage:incident_detail", incident.pk)
    # v1.1 · enrutado por tipo: o de limpeza xera tarefa e aviso ao persoal de limpeza.
    # A administración recibe igualmente o seu aviso (ve todo).
    route_incident(incident)
    if incident.priority == Incident.Priority.HIGH:
        # v5: risco → aviso inmediato á administración e a mantemento, tamén por correo
        for user in _staff(incident.municipality, [Role.ADMIN, Role.MAINTENANCE]):
            notify(
                user,
                _("RISCO: %(f)s") % {"f": incident.facility.name},
                incident.description[:200],
                url=url,
                municipality=incident.municipality,
                level="warning",
                email=True,
            )
        audit("incident.risk", incident.reporter, incident.municipality, incident)
        return
    for user in _staff(incident.municipality, [Role.ADMIN]):
        notify(
            user,
            _("Nova incidencia: %(f)s") % {"f": incident.facility.name},
            incident.description[:200],
            url=url,
            municipality=incident.municipality,
            level="warning",
            email=False,
        )
    if incident.category != Incident.Category.CLEANING:
        # v1.1: as avarías avísanse tamén a mantemento (a orde segue creándoa o concello)
        for user in _staff(incident.municipality, [Role.MAINTENANCE]):
            notify(
                user,
                _("Nova avaría: %(f)s") % {"f": incident.facility.name},
                incident.description[:200],
                url=treverse(incident.municipality, "maintenance:my_orders"),
                municipality=incident.municipality,
                email=False,
            )


def _tell_reporter(incident, title, body=""):
    from apps.tenants.urlutils import treverse

    if incident.reporter:
        notify(
            incident.reporter,
            title,
            body,
            url=treverse(incident.municipality, "incidents:detail", incident.pk),
            municipality=incident.municipality,
        )


def validate(incident, by):
    incident.status = Incident.Status.VALIDATED
    incident.validated_at = timezone.now()
    incident.save(update_fields=["status", "validated_at"])
    audit("incident.validate", by, incident.municipality, incident)
    _tell_reporter(
        incident,
        _("Recibimos o teu aviso e xa o revisamos"),
        _("Incidencia #%(n)s en %(f)s.") % {"n": incident.pk, "f": incident.facility.name},
    )


def reject(incident, by, note=""):
    incident.status = Incident.Status.REJECTED
    incident.resolution_note = note
    incident.save(update_fields=["status", "resolution_note"])
    audit("incident.reject", by, incident.municipality, incident)
    _tell_reporter(incident, _("Pechamos o teu aviso #%(n)s") % {"n": incident.pk}, note)


def _order_kind(incident, assigned_to):
    """v1.1: a orde é de limpeza se vai para o persoal de limpeza ou se a incidencia é de
    limpeza e o concello ten persoal de limpeza; se non, ordinaria (mantemento)."""
    from apps.maintenance.cleaning import has_cleaning_staff

    if assigned_to is not None:
        roles = set(
            Membership.objects.filter(
                user=assigned_to, municipality=incident.municipality
            ).values_list("role", flat=True)
        )
        if Role.CLEANING in roles and Role.MAINTENANCE not in roles:
            return "cleaning"
        if Role.MAINTENANCE in roles:
            return "regular"
    if incident.category == Incident.Category.CLEANING and has_cleaning_staff(
        incident.municipality
    ):
        return "cleaning"
    return "regular"


def create_work_order(incident, by, assigned_to=None, due_date=None, title=""):
    from apps.maintenance.models import WorkOrder

    if incident.status == Incident.Status.RECEIVED:
        incident.validated_at = timezone.now()
    order = WorkOrder.objects.create(
        kind=_order_kind(incident, assigned_to),
        municipality=incident.municipality,
        facility=incident.facility,
        incident=incident,
        title=title
        or _("Incidencia #%(n)s: %(c)s") % {"n": incident.pk, "c": incident.get_category_display()},
        description=incident.description,
        due_date=due_date or timezone.localdate(),
        assigned_to=assigned_to,
        checklist_state=[
            {"label": _("Revisar e reparar"), "done": False},
            {"label": _("Deixar a zona segura e limpa"), "done": False},
        ],
    )
    incident.status = Incident.Status.WORK_ORDER
    incident.save(update_fields=["status", "validated_at"])
    audit("incident.work_order", by, incident.municipality, incident, order=order.pk)
    if assigned_to:
        from apps.tenants.urlutils import treverse

        notify(
            assigned_to,
            _("Nova orde de traballo: %(t)s") % {"t": order.title},
            incident.facility.name,
            url=treverse(incident.municipality, "maintenance:order", order.pk),
            municipality=incident.municipality,
        )
    _tell_reporter(
        incident,
        _("O teu aviso xa ten unha orde de traballo"),
        _("O equipo de mantemento vai revisar %(f)s.") % {"f": incident.facility.name},
    )
    return order


def resolve(incident, by=None, note=""):
    incident.status = Incident.Status.RESOLVED
    incident.resolved_at = timezone.now()
    if note:
        incident.resolution_note = note
    incident.save(update_fields=["status", "resolved_at", "resolution_note"])
    audit("incident.resolve", by, incident.municipality, incident)
    _tell_reporter(
        incident,
        _("Arranxado! Grazas polo teu aviso"),
        _("A incidencia #%(n)s en %(f)s está resolta.")
        % {"n": incident.pk, "f": incident.facility.name}
        + (f"\n{note}" if note else ""),
    )
