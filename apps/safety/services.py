# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · Regras de seguridade.

A · Alertas: «Accidente deportivo» (protocolo paso a paso) e «Emerxencia de seguridade» (112).
    Ao pulsar avísase ao momento á persoa responsable e á administración, e créase unha
    incidencia de prioridade máxima vinculada para que mantemento revise a instalación.
B · Peche sen confirmar: 1.º recordatorio (push) → 2.º (app + canle activa) → persoa
    responsable segundo orde e horario. A Policía Local nunca se avisa soa.
"""

import datetime as dt

from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import Membership, Role, audit
from apps.notifications.services import notify, notify_email_only

from .models import (
    AccidentProtocol,
    AccidentReport,
    Alert,
    ClosingEscalation,
    PoliceContact,
    ResponsibleContact,
)

ANON_ALERTS_PER_HOUR = 3


# ------------------------------------------------------------------ protocolo
def protocol_for(municipality, facility=None):
    """Protocolo efectivo: o da instalación, se non o do concello, se non a plantilla."""
    if facility is not None:
        own = AccidentProtocol.objects.filter(facility=facility).first()
        if own:
            return own
    town = AccidentProtocol.objects.filter(municipality=municipality, facility__isnull=True).first()
    return town or AccidentProtocol(municipality=municipality)


def aed_info(facility):
    """Onde está o DESA: o da instalación ou o máis próximo (bloque C)."""
    if facility is None:
        return None
    if facility.aed_on_site:
        return {
            "on_site": True,
            "where": facility.aed_inside_location,
            "hours": facility.aed_hours,
        }
    if facility.aed_near_name or facility.aed_near_address or facility.aed_location:
        return {
            "on_site": False,
            "name": facility.aed_near_name,
            "address": facility.aed_near_address or facility.aed_location,
            "distance_m": facility.aed_near_distance_m,
            "hours": facility.aed_near_hours,
        }
    return None


# ------------------------------------------------------------------ responsables
def on_duty(municipality, at=None):
    """Persoas responsables de servizo agora, pola orde que fixou o concello."""
    at = at or timezone.now()
    return [
        c
        for c in ResponsibleContact.objects.filter(municipality=municipality, active=True)
        if c.covers(at)
    ]


def _admins(municipality):
    return [
        m.user
        for m in Membership.objects.filter(
            municipality=municipality, role=Role.ADMIN
        ).select_related("user")
    ]


def tell_contact(contact, title, body, url):
    """Aviso a unha persoa responsable: na app (se ten conta) e por correo."""
    if contact.user_id:
        notify(
            contact.user,
            title,
            body,
            url=url,
            municipality=contact.municipality,
            level="warning",
            email=not contact.email,
        )
    if contact.email:
        notify_email_only(contact.email, f"Eira · {title}", f"{body}\n\n{url}".strip())


# ------------------------------------------------------------------ alertas
def anonymous_alert_allowed(key):
    """As alertas sen sesión permítense (é unha emerxencia), pero con límite por orixe."""
    cache_key = f"eira:alert:{key}"
    count = cache.get(cache_key, 0)
    if count >= ANON_ALERTS_PER_HOUR:
        return False
    cache.set(cache_key, count + 1, 3600)
    return True


def raise_alert(
    kind,
    municipality,
    *,
    user=None,
    facility=None,
    booking=None,
    session=None,
    origin=Alert.Origin.APP,
):
    from apps.incidents.models import Incident
    from apps.incidents.services import notify_staff_new_incident
    from apps.tenants.urlutils import treverse

    if booking is not None and facility is None:
        facility = booking.facility
    alert = Alert.objects.create(
        municipality=municipality,
        kind=kind,
        origin=origin,
        facility=facility,
        booking=booking,
        session=session,
        raised_by=user if (user and user.is_authenticated) else None,
    )
    where = facility.name if facility else _("lugar sen indicar")
    if kind == Alert.Kind.ACCIDENT:
        title = _("ALERTA · Accidente deportivo en %(f)s") % {"f": where}
        body = _("Abriuse o protocolo de accidente. Revisa se fai falta axuda no lugar.")
    else:
        title = _("ALERTA · Emerxencia de seguridade en %(f)s") % {"f": where}
        body = _(
            "Unha persoa pulsou «Emerxencia de seguridade». O 112 aparece destacado na súa pantalla."
        )
    url = treverse(municipality, "manage:safety")
    notified = []
    for contact in on_duty(municipality)[:1]:
        tell_contact(contact, title, body, url)
        notified.append(contact.name)
    for admin in _admins(municipality):
        notify(admin, title, body, url=url, municipality=municipality, level="warning", email=True)
        notified.append(str(_("Administración do concello")))
    # Incidencia de prioridade máxima para que mantemento revise a instalación
    if facility is not None:
        incident = Incident.objects.create(
            municipality=municipality,
            facility=facility,
            reporter=alert.raised_by,
            booking=booking,
            category=Incident.Category.SAFETY,
            source=Incident.Source.ALERT,
            priority=Incident.Priority.URGENT,
            description=_(
                "%(k)s. Revisar se a instalación tivo que ver (chan, material, iluminación…)."
            )
            % {"k": alert.get_kind_display()},
        )
        alert.incident = incident
        notify_staff_new_incident(incident)
    alert.notified = list(dict.fromkeys(notified))
    alert.save(update_fields=["incident", "notified"])
    audit(f"alert.{kind}", alert.raised_by, municipality, alert, origin=origin)
    return alert


def acknowledge(alert, by):
    if alert.acknowledged_at is None:
        alert.acknowledged_at = timezone.now()
        alert.acknowledged_by = by
        alert.save(update_fields=["acknowledged_at", "acknowledged_by"])
        audit("alert.ack", by, alert.municipality, alert)
    return alert


# ------------------------------------------------------------------ rexistro de accidentes
def register_accident(
    municipality,
    facility,
    *,
    kind,
    severity,
    called_112,
    reporter_role,
    occurred_at=None,
    user=None,
    alert=None,
):
    report = AccidentReport.objects.create(
        municipality=municipality,
        facility=facility,
        occurred_at=occurred_at or timezone.now(),
        kind=kind,
        severity=severity,
        called_112=called_112 or severity == AccidentReport.Severity.EMERGENCY,
        reporter_role=reporter_role,
        reported_by=user if (user and user.is_authenticated) else None,
        alert=alert,
    )
    audit("accident.register", report.reported_by, municipality, report)
    return report


def close_accident(report, by, facility_related=None):
    report.closed_at = timezone.now()
    report.closed_by = by
    report.facility_related = facility_related
    report.save(update_fields=["closed_at", "closed_by", "facility_related"])
    audit("accident.close", by, report.municipality, report)
    return report


def purge_accidents(now=None):
    """Conservación configurable por concello: bórranse os rexistros pechados máis antigos."""
    from apps.tenants.models import Municipality

    now = now or timezone.now()
    removed = 0
    for m in Municipality.objects.all():
        limit = now - dt.timedelta(days=30 * m.accident_retention_months)
        removed += AccidentReport.objects.filter(
            municipality=m, closed_at__isnull=False, occurred_at__lt=limit
        ).delete()[0]
    return removed


# ------------------------------------------------------------------ B · peche sen confirmar
def _door_state(booking):
    """Nivel 3: se o adaptador da pechadura informa do estado da porta, úsase ese dato."""
    from apps.integrations.registry import get_adapter

    device = getattr(booking.facility, "lock", None)
    if booking.facility.access_level != 3 or device is None:
        return ""
    try:
        return get_adapter("lock").door_state(device) or ""
    except NotImplementedError:
        return ""


def _needs_escalation(booking):
    # Só onde hai algo que pechar (niveis 1–3) e se a persoa entrou (check-in ou apertura)
    return booking.facility.access_level >= 1 and booking.status == "used"


def _resolve(esc, outcome, by=None, note=""):
    esc.resolved_at = timezone.now()
    esc.outcome = outcome
    esc.resolved_by = by
    if note:
        esc.note = note[:300]
    esc.save(update_fields=["resolved_at", "outcome", "resolved_by", "note"])
    audit("closing.resolved", by, esc.municipality, esc.booking, outcome=outcome)


def on_checklist_submitted(booking):
    esc = getattr(booking, "closing_escalation", None)
    if esc is not None and esc.is_open:
        _resolve(esc, ClosingEscalation.Outcome.CLOSED_BY_USER, by=booking.user)


def escalate_closings(now=None):
    """Executar cada pouco (cron cada 5 min, ou desde `booking_maintenance`)."""
    from apps.bookings.models import Booking
    from apps.tenants.urlutils import treverse

    now = now or timezone.now()
    done = {"first": 0, "second": 0, "escalated": 0, "door": 0}
    candidates = (
        Booking.objects.filter(
            status=Booking.Status.USED,
            closed_at__isnull=True,
            end__lte=now,
            end__gte=now - dt.timedelta(hours=12),
            facility__access_level__gte=1,
        )
        .select_related("municipality", "facility", "user")
        .order_by("end")
    )
    for booking in candidates:
        m = booking.municipality
        esc, _created = ClosingEscalation.objects.get_or_create(
            booking=booking, defaults={"municipality": m}
        )
        if not esc.is_open:
            continue
        url = treverse(m, "bookings:checklist", booking.pk)
        t1 = booking.end + dt.timedelta(minutes=m.close_reminder_minutes)
        t2 = t1 + dt.timedelta(minutes=m.close_second_minutes)
        t3 = t2 + dt.timedelta(minutes=m.close_escalate_minutes)
        if esc.stage < ClosingEscalation.Stage.FIRST and now >= t1:
            # 1.º recordatorio: só pola app (notificación push)
            notify(
                booking.user,
                _("Falta confirmar o peche de %(f)s") % {"f": booking.facility.name},
                _("Completa a lista de peche: porta, chave e que todo quede en orde."),
                url=url,
                municipality=m,
                level="warning",
                email=False,
                telegram=False,
            )
            esc.stage, esc.first_at = ClosingEscalation.Stage.FIRST, now
            esc.save(update_fields=["stage", "first_at"])
            booking.close_unconfirmed = True
            booking.save(update_fields=["close_unconfirmed"])
            done["first"] += 1
        elif esc.stage == ClosingEscalation.Stage.FIRST and now >= t2:
            # 2.º: app e a canle que teña activa (correo ou Telegram)
            notify(
                booking.user,
                _("Segundo aviso: confirma o peche de %(f)s") % {"f": booking.facility.name},
                _("Se non o confirmas, avisaremos á persoa responsable do concello."),
                url=url,
                municipality=m,
                level="warning",
                email=True,
                telegram=True,
            )
            esc.stage, esc.second_at = ClosingEscalation.Stage.SECOND, now
            esc.save(update_fields=["stage", "second_at"])
            done["second"] += 1
        elif esc.stage == ClosingEscalation.Stage.SECOND and now >= t3:
            state = _door_state(booking)
            esc.door_state = state
            if state == "closed":
                # A pechadura di que a porta está pechada: non se escala
                esc.save(update_fields=["door_state"])
                _resolve(esc, ClosingEscalation.Outcome.DOOR_CLOSED)
                done["door"] += 1
                continue
            contact = next(iter(on_duty(m, now)), None)
            esc.stage, esc.escalated_at, esc.contact = (
                ClosingEscalation.Stage.ESCALATED,
                now,
                contact,
            )
            esc.counted_as_breach = m.close_breach_enabled
            esc.save(
                update_fields=[
                    "stage",
                    "escalated_at",
                    "contact",
                    "door_state",
                    "counted_as_breach",
                ]
            )
            link = treverse(m, "safety:closing", esc.token)
            title = _("Peche sen confirmar: %(f)s") % {"f": booking.facility.name}
            body = _(
                "A reserva rematou ás %(h)s e ninguén confirmou o peche. Revisa a instalación."
            ) % {"h": timezone.localtime(booking.end).strftime("%H:%M")}
            if contact:
                tell_contact(contact, title, body, link)
            for admin in _admins(m):
                notify(admin, title, body, url=link, municipality=m, level="warning", email=False)
            audit("closing.escalated", None, m, booking, contact=contact.name if contact else "")
            done["escalated"] += 1
    return done


def resolve_by_contact(esc, by=None, note=""):
    _resolve(esc, ClosingEscalation.Outcome.CHECKED, by=by, note=note)


def log_police_contact(esc, *, user=None, contact=None):
    phone = esc.municipality.police_phone
    entry = PoliceContact.objects.create(
        municipality=esc.municipality,
        escalation=esc,
        phone=phone,
        by_user=user if (user and user.is_authenticated) else None,
        by_contact=contact,
    )
    audit("closing.police_contact", entry.by_user, esc.municipality, esc.booking, phone=phone)
    return entry
