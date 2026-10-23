# SPDX-License-Identifier: EUPL-1.2
"""Inscricións (con prazas, lista de espera e consentimentos), sesións, asistencia e esforzo percibido."""

import datetime as dt
import hashlib
import hmac

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import Consent, Dependent, Household, Membership, Role, User, audit
from apps.notifications.services import notify

from .models import Attendance, Enrollment, PendingParticipant, Session


class EnrollmentError(Exception):
    pass


def pseudonym(enrollment_id):
    """Seudónimo estable e non reversible sen o segredo do servidor."""
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f"enrollment:{enrollment_id}".encode(), hashlib.sha256).hexdigest()[:12]


def enroll(group, user, dependent=None):
    if dependent is not None:
        if dependent.household.responsible_id != user.pk:
            raise EnrollmentError(_("Só podes inscribir menores da túa unidade familiar."))
        if not dependent.has_consent(Consent.Kind.DATA):
            raise EnrollmentError(_("Falta o consentimento para o tratamento de datos do menor."))
        age = dependent.age
    else:
        age = user.age
    if age is not None and not (group.min_age <= age <= group.max_age):
        raise EnrollmentError(_("A idade non corresponde a este grupo."))
    existing = Enrollment.objects.filter(group=group, user=user, dependent=dependent).exclude(
        status=Enrollment.Status.CANCELLED
    )
    if existing.exists():
        raise EnrollmentError(_("Xa hai unha inscrición para esta persoa neste grupo."))
    with transaction.atomic():
        full = (
            group.enrolled().count()
            + group.enrollments.filter(status=Enrollment.Status.PENDING_PAYMENT).count()
            >= group.places
        )
        if full:
            status = Enrollment.Status.WAITLIST
        elif group.fee_cents:
            status = Enrollment.Status.PENDING_PAYMENT
        else:
            status = Enrollment.Status.ACTIVE
        e = Enrollment.objects.create(
            municipality=group.municipality,
            group=group,
            user=user,
            dependent=dependent,
            status=status,
        )
        e.pseudonym = pseudonym(e.pk)
        e.save(update_fields=["pseudonym"])
    audit("enrollment.create", user, group.municipality, e, status=status)
    return e


def validate_pending(pending, email, actor):
    """Converte unha persoa apuntada polo monitor nunha inscrición real.

    Menor de idade → menor ao cargo da conta do correo indicado (coa autorización en papel
    rexistrada como consentimento). Adulta → inscrición na súa propia conta."""
    with transaction.atomic():
        user, created = User.objects.get_or_create(email=email)
        if created:
            user.set_unusable_password()
            user.display_name = "" if _is_minor(pending) else pending.first_name
            user.birth_year = None if _is_minor(pending) else pending.birth_year
            user.save()
        Membership.objects.get_or_create(
            user=user, municipality=pending.municipality, role=Role.CITIZEN
        )
        dependent = None
        if _is_minor(pending):
            household, _c = Household.objects.get_or_create(responsible=user)
            dependent = household.dependents.filter(first_name=pending.first_name).first()
            if dependent is None:
                dependent = Dependent.objects.create(
                    household=household,
                    first_name=pending.first_name,
                    birth_year=pending.birth_year,
                )
            if not dependent.has_consent(Consent.Kind.DATA):
                Consent.objects.create(
                    dependent=dependent,
                    kind=Consent.Kind.DATA,
                    granted_by=user,
                    text_version="papel",
                )
        e = enroll(pending.group, user, dependent)
        pending.status = PendingParticipant.Status.VALIDATED
        pending.resolved_at = timezone.now()
        pending.enrollment = e
        pending.save(update_fields=["status", "resolved_at", "enrollment"])
        audit("enrollment.validate_pending", actor, pending.municipality, e)
    return e


def _is_minor(pending):
    return bool(pending.birth_year) and timezone.localdate().year - pending.birth_year < 18


def mark_enrollment_paid(enrollment, reference, amount):
    if enrollment.status != Enrollment.Status.PENDING_PAYMENT:
        return enrollment
    enrollment.status = Enrollment.Status.ACTIVE
    enrollment.paid_cents = amount
    enrollment.payment_reference = reference
    enrollment.save(update_fields=["status", "paid_cents", "payment_reference"])
    notify(
        enrollment.user,
        _("Inscrición confirmada: %(g)s") % {"g": enrollment.group},
        municipality=enrollment.municipality,
        level="success",
    )
    return enrollment


def cancel_enrollment(enrollment, by=None):
    was_holding = enrollment.status in (Enrollment.Status.ACTIVE, Enrollment.Status.PENDING_PAYMENT)
    enrollment.status = Enrollment.Status.CANCELLED
    enrollment.save(update_fields=["status"])
    audit("enrollment.cancel", by, enrollment.municipality, enrollment)
    if was_holding:
        promote_waitlist(enrollment.group)


def promote_waitlist(group):
    nxt = group.enrollments.filter(status=Enrollment.Status.WAITLIST).order_by("created_at").first()
    if nxt:
        nxt.status = (
            Enrollment.Status.PENDING_PAYMENT if group.fee_cents else Enrollment.Status.ACTIVE
        )
        nxt.save(update_fields=["status"])
        notify(
            nxt.user,
            _("Quedou unha praza libre en %(g)s") % {"g": group},
            _("Saíches da lista de espera.")
            + (" " + _("Completa o pagamento para confirmala.") if group.fee_cents else ""),
            municipality=group.municipality,
            level="success",
        )
    return nxt


def sessions_for_day(groups, day):
    """Sesións do día (créanse ao vóo segundo os días da semana de cada grupo)."""
    out = []
    for g in groups:
        if day.weekday() in g.weekday_list():
            s, _c = Session.objects.get_or_create(
                group=g,
                date=day,
                defaults={
                    "municipality": g.municipality,
                    "start_time": g.start_time,
                    "duration_minutes": g.duration_minutes,
                },
            )
            out.append(s)
    return sorted(out, key=lambda s: s.start_time)


def record_attendance(session, present_ids):
    for e in session.group.enrolled():
        Attendance.objects.update_or_create(
            session=session,
            enrollment=e,
            defaults={
                "present": e.pk in present_ids,
                "minutes": session.duration_minutes if e.pk in present_ids else 0,
            },
        )


def can_record_effort(enrollment):
    """O esforzo dos menores só se rexistra co seu consentimento específico."""
    if enrollment.dependent_id:
        return enrollment.dependent.has_consent(Consent.Kind.PERFORMANCE)
    return True


def record_rpe(session, values):
    """values: {enrollment_id: rpe 0–10}. Pecha a sesión."""
    for att in session.attendances.filter(present=True).select_related("enrollment__dependent"):
        v = values.get(att.enrollment_id)
        if v is not None and 0 <= v <= 10 and can_record_effort(att.enrollment):
            att.rpe = v
            att.save(update_fields=["rpe"])
    session.closed_at = timezone.now()
    session.save(update_fields=["closed_at"])


def session_load_summary(session):
    loads = [a.session_load for a in session.attendances.all() if a.session_load is not None]
    return {
        "present": session.attendances.filter(present=True).count(),
        "avg_rpe": round(
            sum(a.rpe for a in session.attendances.all() if a.rpe is not None) / len(loads), 1
        )
        if loads
        else None,
        "avg_load": round(sum(loads) / len(loads)) if loads else None,
    }


def week_start(day):
    return day - dt.timedelta(days=day.weekday())
