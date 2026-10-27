# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · G: partidas abertas («Busco xente»).

Privacidade: só nome de pila e inicial; nunca teléfono nin correo; sen chat libre (mensaxes
predefinidas); consentimento explícito para aparecer; menores de 14 anos non poden publicar nin
unirse. Cada concello pode desactivar a función (módulo `open_games`)."""

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import Membership, Role, audit
from apps.notifications.services import notify

from .models import Booking, GameJoin, GameMessage, GameReport, OpenGame

MIN_AGE = 14
REPORTS_TO_HIDE = 3


class GameError(Exception):
    pass


def public_name(user):
    """«Uxía P.»: nome de pila e inicial do apelido (se o hai). Nunca o correo."""
    parts = (getattr(user, "display_name", "") or "").split()
    if not parts:
        return _("Persoa usuaria")
    return f"{parts[0]} {parts[1][0]}." if len(parts) > 1 else parts[0]


def check_age(user):
    if user.age is None:
        raise GameError(
            _("Indica o teu ano de nacemento na túa conta para usar as partidas abertas.")
        )
    if user.age < MIN_AGE:
        raise GameError(_("As partidas abertas son para maiores de 14 anos."))


def _url(m, name, *args):
    from apps.tenants.urlutils import treverse

    return treverse(m, name, *args)


def can_publish(booking):
    return (
        booking.municipality.module_enabled("open_games")
        and booking.status == Booking.Status.CONFIRMED
        and booking.start > timezone.now()
        and booking.user_id is not None
    )


def publish(booking, user, *, spots, level, message="", consent=False):
    if booking.user_id != user.pk or not can_publish(booking):
        raise GameError(_("Esta reserva non se pode abrir a máis xente."))
    check_age(user)
    if not consent:
        raise GameError(_("Tes que aceptar aparecer nas partidas abertas."))
    room = booking.facility.max_participants - booking.participants
    if not 1 <= spots <= max(1, room):
        raise GameError(_("Poden unirse ata %(n)s persoas máis.") % {"n": max(1, room)})
    game, _created = OpenGame.objects.update_or_create(
        booking=booking,
        defaults={
            "municipality": booking.municipality,
            "spots": spots,
            "base_participants": booking.participants,
            "level": level,
            "message": (message or "").strip()[:140],
            "consent_at": timezone.now(),
            "active": True,
        },
    )
    audit("open_game.publish", user, booking.municipality, booking)
    return game


def close(game, by):
    game.active = False
    game.save(update_fields=["active"])
    audit("open_game.close", by, game.municipality, game.booking)


def visible_games(tenant, *, kind="", day=None, level=""):
    """Partidas do propio concello e dos concellos próximos da rede (coa función activa)."""
    towns = Q(municipality=tenant)
    if tenant.region_id:
        towns |= Q(municipality__region_id=tenant.region_id, municipality__network_open=True)
    qs = (
        OpenGame.objects.filter(
            towns,
            active=True,
            hidden_by_reports=False,
            booking__status=Booking.Status.CONFIRMED,
            booking__start__gt=timezone.now(),
        )
        .select_related("booking__facility", "booking__user", "municipality")
        .order_by("booking__start")
    )
    if kind:
        qs = qs.filter(booking__facility__kind=kind)
    if day:
        qs = qs.filter(booking__start__date=day)
    if level:
        qs = qs.filter(level=level)
    return [g for g in qs if g.municipality.module_enabled("open_games") and g.spots_left > 0]


def request_join(game, user, consent=False):
    if game.booking.user_id == user.pk:
        raise GameError(_("É a túa partida."))
    check_age(user)
    if not consent:
        raise GameError(_("Tes que aceptar que quen organiza vexa o teu nome de pila e inicial."))
    if not game.active or game.spots_left <= 0:
        raise GameError(_("Esta partida xa non ten prazas."))
    join, created = GameJoin.objects.get_or_create(
        game=game, user=user, defaults={"consent_at": timezone.now()}
    )
    if not created:
        if join.status == GameJoin.Status.ACCEPTED:
            return join
        join.status, join.consent_at, join.decided_at = (
            GameJoin.Status.PENDING,
            timezone.now(),
            None,
        )
        join.save(update_fields=["status", "consent_at", "decided_at"])
    notify(
        game.booking.user,
        _("%(n)s quere unirse á túa partida") % {"n": public_name(user)},
        _("%(f)s · Acepta ou rexeita a solicitude.") % {"f": game.booking.facility.name},
        url=_url(game.municipality, "bookings:game", game.pk),
        municipality=game.municipality,
        email=False,
    )
    return join


def decide(join, by, accept):
    game = join.game
    if game.booking.user_id != by.pk:
        raise GameError(_("Só a persoa que organiza pode decidir."))
    if accept and game.spots_left <= 0:
        raise GameError(_("Xa non quedan prazas."))
    join.status = GameJoin.Status.ACCEPTED if accept else GameJoin.Status.REJECTED
    join.decided_at = timezone.now()
    join.save(update_fields=["status", "decided_at"])
    if accept:
        b = game.booking
        b.participants = min(b.facility.max_participants, b.participants + 1)
        b.save(update_fields=["participants"])
    notify(
        join.user,
        _("Aceptáronte na partida") if accept else _("Non hai sitio nesta partida"),
        f"{game.booking.facility.name} · {timezone.localtime(game.booking.start):%d/%m %H:%M}",
        url=_url(game.municipality, "bookings:game", game.pk),
        municipality=game.municipality,
        level="success" if accept else "info",
        email=False,
    )
    audit("open_game.decide", by, game.municipality, game.booking, accept=accept)
    return join


def withdraw(join):
    was_accepted = join.status == GameJoin.Status.ACCEPTED
    join.status = GameJoin.Status.WITHDRAWN
    join.save(update_fields=["status"])
    if was_accepted:
        b = join.game.booking
        b.participants = max(1, b.participants - 1)
        b.save(update_fields=["participants"])


def is_member(game, user):
    return (
        game.booking.user_id == user.pk
        or game.joins.filter(user=user, status=GameJoin.Status.ACCEPTED).exists()
    )


def post_message(game, user, code):
    from .models import GAME_MESSAGES

    if code not in dict(GAME_MESSAGES) or not is_member(game, user):
        raise GameError(_("Só se poden enviar as mensaxes predefinidas da partida."))
    msg = GameMessage.objects.create(game=game, user=user, code=code)
    others = [game.booking.user] + [j.user for j in game.accepted().select_related("user")]
    for person in others:
        if person.pk != user.pk:
            notify(
                person,
                f"{public_name(user)}: {msg.get_code_display()}",
                game.booking.facility.name,
                url=_url(game.municipality, "bookings:game", game.pk),
                municipality=game.municipality,
                email=False,
            )
    return msg


def report(game, user, reason):
    rep, created = GameReport.objects.get_or_create(
        game=game, user=user, defaults={"reason": reason}
    )
    if created:
        for m in Membership.objects.filter(
            municipality=game.municipality, role=Role.ADMIN
        ).select_related("user"):
            notify(
                m.user,
                _("Denuncia dunha partida aberta"),
                f"{game.booking.facility.name} · {rep.get_reason_display()}",
                url=_url(game.municipality, "manage:booking", game.booking_id),
                municipality=game.municipality,
                level="warning",
                email=False,
            )
        if game.reports.count() >= REPORTS_TO_HIDE:
            game.hidden_by_reports = True
            game.save(update_fields=["hidden_by_reports"])
        audit("open_game.report", user, game.municipality, game.booking, reason=reason)
    return rep
