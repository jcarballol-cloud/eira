# SPDX-License-Identifier: EUPL-1.2
"""Prazos de conservación que aínda non tiñan purga automática (auditoría RXPD do 14/11/2026).

Complementa as purgas que xa había (solicitudes da app, accidentes, rexistro de auditoría e
avisos). Execútase con `booking_maintenance` (cada 15 minutos) e é idempotente. Os prazos están
na política de conservación: docs/rxpd/paquete/05-conservacion.md.

Regra xeral: o que serve á contabilidade ou ás estatísticas consérvase **anonimizado** (sen
persoa nin textos libres); o que só servía para un trámite curto bórrase.
"""

import datetime as dt

from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone

# Meses (30 días) de cada prazo. Un concello pode cambialos en `EIRA_RETENTION` (settings).
DEFAULTS = {
    "bookings": 24,  # reservas: persoa e textos libres, 2 anos despois de rematar
    "access_events": 24,  # eventos de acceso (porta, códigos)
    "incidents": 24,  # incidencias pechadas: quen avisou e a foto
    "ratings": 24,  # comentarios das valoracións
    "surveys": 24,  # enquisas anuais: persoa e comentario
    "cleaning": 24,  # rexistro de limpeza (datos do persoal)
    "game_reports": 12,  # denuncias de partidas abertas
    "pending_participants": 3,  # altas pendentes na tableta (correo da familia)
    "invitations": 1,  # códigos de empadroamento caducados e sen usar
    "simulated": 1,  # bandexa de correo e mensaxes simuladas (só adaptadores de proba)
}


def months(key):
    return int(getattr(settings, "EIRA_RETENTION", {}).get(key, DEFAULTS[key]))


def _limit(now, key):
    return now - dt.timedelta(days=30 * months(key))


def _delete_files(qs, *fields):
    """Borra do disco as fotos antes de baleirar o campo ou borrar a fila."""
    for obj in qs.only("pk", *fields):
        for f in fields:
            file = getattr(obj, f)
            if file:
                file.delete(save=False)


def purge_bookings(now):
    from apps.bookings.models import Booking, OpenGame

    old = Booking.objects.filter(end__lt=_limit(now, "bookings"))
    # As partidas abertas (e as súas solicitudes, mensaxes e denuncias) só viven coa reserva
    games = OpenGame.objects.filter(booking__in=old).delete()[0]
    _delete_files(old.exclude(start_state_photo=""), "start_state_photo")
    todo = old.exclude(
        user=None,
        holder_name="",
        holder_phone="",
        participant_names="",
        start_state_notes="",
        start_state_photo="",
        close_notes="",
        cancel_reason="",
    )
    n = todo.update(
        user=None,
        holder_name="",
        holder_phone="",
        participant_names="",
        start_state_notes="",
        start_state_photo="",
        close_notes="",
        cancel_reason="",
    )
    return n + games


def purge_access_events(now):
    from apps.access.models import AccessEvent

    return AccessEvent.objects.filter(at__lt=_limit(now, "access_events")).delete()[0]


def purge_incidents(now):
    from apps.incidents.models import Incident

    old = Incident.objects.filter(
        resolved_at__lt=_limit(now, "incidents"), status=Incident.Status.RESOLVED
    )
    _delete_files(old.exclude(photo=""), "photo")
    return old.exclude(reporter=None, photo="").update(reporter=None, photo="")


def purge_ratings(now):
    from apps.bookings.models import Rating

    return (
        Rating.objects.filter(created_at__lt=_limit(now, "ratings"))
        .exclude(comment="")
        .update(comment="")
    )


def purge_surveys(now):
    from apps.surveys.models import SurveyResponse

    old = SurveyResponse.objects.filter(created_at__lt=_limit(now, "surveys"))
    return old.exclude(user=None, comment="").update(user=None, comment="")


def purge_cleaning(now):
    from apps.maintenance.models import CleaningLog

    old = CleaningLog.objects.filter(done_at__lt=_limit(now, "cleaning"))
    _delete_files(old.exclude(photo=""), "photo")
    return old.delete()[0]


def purge_game_reports(now):
    from apps.bookings.models import GameReport

    return GameReport.objects.filter(created_at__lt=_limit(now, "game_reports")).delete()[0]


def purge_pending_participants(now):
    from apps.activities.models import PendingParticipant

    return PendingParticipant.objects.filter(
        created_at__lt=_limit(now, "pending_participants")
    ).delete()[0]


def purge_invitations(now):
    from apps.accounts.models import ResidencyInvitation

    return ResidencyInvitation.objects.filter(
        expires_at__lt=_limit(now, "invitations"), used_at__isnull=True
    ).delete()[0]


def purge_login_codes(now):
    """Códigos para entrar (levan o correo): caducan en minutos; bórranse ao día seguinte."""
    from apps.accounts.models import LoginCode

    return LoginCode.objects.filter(expires_at__lt=now - dt.timedelta(days=1)).delete()[0]


def purge_sessions(now):
    """Sesións caducadas (o que fai `clearsessions`, sen depender dun cron á parte)."""
    return Session.objects.filter(expire_date__lt=now).delete()[0]


def purge_simulated(now):
    from apps.integrations.models import DevMail, OutboundMessage

    limit = _limit(now, "simulated")
    return (
        DevMail.objects.filter(sent_at__lt=limit).delete()[0]
        + OutboundMessage.objects.filter(sent_at__lt=limit).delete()[0]
    )


RULES = [
    ("bookings", purge_bookings),
    ("access_events", purge_access_events),
    ("incidents", purge_incidents),
    ("ratings", purge_ratings),
    ("surveys", purge_surveys),
    ("cleaning", purge_cleaning),
    ("game_reports", purge_game_reports),
    ("pending_participants", purge_pending_participants),
    ("invitations", purge_invitations),
    ("login_codes", purge_login_codes),
    ("sessions", purge_sessions),
    ("simulated", purge_simulated),
]


def purge_all(now=None):
    """Aplica todos os prazos. Devolve {regra: filas borradas ou anonimizadas} e, se houbo
    algunha, deixa constancia no rexistro de auditoría (só as cifras)."""
    from apps.accounts.models import audit

    now = now or timezone.now()
    done = {key: fn(now) for key, fn in RULES}
    changed = {k: v for k, v in done.items() if v}
    if changed:
        audit("retention.purge", **changed)
    return done
