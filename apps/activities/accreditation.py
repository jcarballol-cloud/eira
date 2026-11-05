# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · E: acreditación das persoas monitoras ou voluntarias para actividades con menores.

Eira non garda nin sube o certificado do Rexistro Central de Delincuentes Sexuais (datos penais,
art. 10 RGPD): iso queda na contratación do concello. Só garda quen marcou a comprobación e cando.
Ver docs/rxpd/acreditacion-menores.md."""

import datetime as dt

from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import Membership, Role, audit
from apps.notifications.services import notify

from .models import MinorsAccreditation

CURRENT, EXPIRED, MISSING = "current", "expired", "missing"


class AssignmentBlocked(Exception):
    """Non se pode asignar: falta a acreditación ou pasou o prazo de revisión."""


def _days(municipality):
    return 30 * municipality.accreditation_review_months


def review_due(record, now=None):
    now = now or timezone.now()
    return record.confirmed_at + dt.timedelta(days=_days(record.municipality)) <= now


def status_of(municipality, user, now=None):
    record = (
        MinorsAccreditation.objects.filter(municipality=municipality, user=user)
        .select_related("municipality")
        .first()
    )
    if record is None:
        return MISSING
    return EXPIRED if review_due(record, now) else CURRENT


def status_label(status):
    return {
        CURRENT: _("Acreditación verificada"),
        EXPIRED: _("Revisión pendente"),
        MISSING: _("Acreditación pendente"),
    }[status]


def blocked_message(group, user, now=None):
    """Texto do bloqueo, ou "" se esta persoa pode levar este grupo."""
    if user is None or not group.has_minors:
        return ""
    status = status_of(group.municipality, user, now)
    if status == CURRENT:
        return ""
    if status == EXPIRED:
        return _(
            "%(p)s non pode levar este grupo con menores: pasou o prazo de revisión da "
            "acreditación. A administración do concello debe volver confirmala en «Acreditacións»."
        ) % {"p": user}
    return _(
        "%(p)s non pode levar este grupo con menores: falta marcar a acreditación verificada na "
        "contratación. Faino a administración do concello en «Acreditacións»."
    ) % {"p": user}


def assign_monitor(group, user, *, by):
    """Punto único de asignación desde a interface. `user=None` deixa o grupo sen monitora."""
    message = blocked_message(group, user)
    if message:
        audit("accreditation.blocked", by, group.municipality, group, person=user.pk)
        raise AssignmentBlocked(message)
    group.monitor = user
    group.save(update_fields=["monitor"])
    audit("group.assign_monitor", by, group.municipality, group, person=user.pk if user else None)
    return group


def confirm(municipality, user, *, by):
    """Marca ou renova: só quen e cando. Non se admite ningún outro dato."""
    record, _created = MinorsAccreditation.objects.update_or_create(
        municipality=municipality,
        user=user,
        defaults={"confirmed_by": by, "confirmed_at": timezone.now(), "review_notified_at": None},
    )
    audit("accreditation.confirm", by, municipality, record, person=user.pk)
    return record


def withdraw(municipality, user, *, by):
    """Retira a marca (p. ex. fin do contrato). Os grupos asignados móstranse co aviso."""
    removed, _detail = MinorsAccreditation.objects.filter(
        municipality=municipality, user=user
    ).delete()
    if removed:
        audit("accreditation.withdraw", by, municipality, None, person=user.pk)
    return bool(removed)


def _members(municipality):
    return (
        Membership.objects.filter(municipality=municipality, role=Role.MONITOR)
        .select_related("user")
        .order_by("user__display_name", "user__email")
    )


def rows(municipality, now=None):
    records = {
        r.user_id: r
        for r in MinorsAccreditation.objects.filter(municipality=municipality).select_related(
            "confirmed_by"
        )
    }
    out = []
    for member in _members(municipality):
        record = records.get(member.user_id)
        status = status_of(municipality, member.user, now)
        due = record.confirmed_at + dt.timedelta(days=_days(municipality)) if record else None
        out.append(
            {
                "member": member,
                "record": record,
                "status": status,
                "status_label": status_label(status),
                "review_on": due,
            }
        )
    return out


def monitor_options(municipality):
    return [
        {
            "user": m.user,
            "is_volunteer": m.is_volunteer,
            "status": (status := status_of(municipality, m.user)),
            "status_label": status_label(status),
        }
        for m in _members(municipality)
    ]


def notify_due_reviews(now=None):
    """Execútase en `booking_maintenance`. Avisa unha vez á administración por cada revisión."""
    from apps.tenants.urlutils import treverse

    now = now or timezone.now()
    sent = 0
    records = MinorsAccreditation.objects.filter(review_notified_at__isnull=True).select_related(
        "municipality", "user"
    )
    for record in records:
        if not review_due(record, now):
            continue
        m = record.municipality
        for admin in Membership.objects.filter(municipality=m, role=Role.ADMIN).select_related(
            "user"
        ):
            notify(
                admin.user,
                _("Toca revisar unha acreditación para actividades con menores"),
                _("Volve confirmar a acreditación de %(p)s na contratación.") % {"p": record.user},
                url=treverse(m, "manage:accreditations"),
                municipality=m,
                level="warning",
                email=True,
            )
        record.review_notified_at = now
        record.save(update_fields=["review_notified_at"])
        sent += 1
    return sent
