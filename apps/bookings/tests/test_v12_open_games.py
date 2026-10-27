# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · G: partidas abertas (privacidade, menores de 14, solicitudes, mensaxes e denuncias)."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import Membership, Residency, Role, User
from apps.bookings import opengames
from apps.bookings.models import Booking, GameJoin, OpenGame
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


def _person(muni, email, name, year=1990):
    u = User.objects.create_user(email, display_name=name, birth_year=year)
    Membership.objects.create(user=u, municipality=muni, role=Role.CITIZEN)
    Residency.objects.create(user=u, municipality=muni, method=Residency.Method.COUNTER)
    return u


@pytest.fixture
def org(muni_a):
    return _person(muni_a, "org@example.org", "Sabela Pereira Lago")


@pytest.fixture
def game(org, padel_a):
    start = timezone.now() + dt.timedelta(days=2)
    b = Booking.objects.create(
        municipality=padel_a.municipality,
        facility=padel_a,
        user=org,
        start=start,
        end=start + dt.timedelta(hours=1),
        status=Booking.Status.CONFIRMED,
        price_cents=1200,
        participants=2,
    )
    return opengames.publish(b, org, spots=2, level="medium", message="Dobres", consent=True)


def test_public_name_is_first_name_and_initial(org):
    assert opengames.public_name(org) == "Sabela P."


def test_publish_requires_consent_and_14(org, padel_a, muni_a):
    start = timezone.now() + dt.timedelta(days=3)
    b = Booking.objects.create(
        municipality=muni_a,
        facility=padel_a,
        user=org,
        start=start,
        end=start + dt.timedelta(hours=1),
        status=Booking.Status.CONFIRMED,
    )
    with pytest.raises(opengames.GameError):
        opengames.publish(b, org, spots=1, level="medium", consent=False)
    young = _person(muni_a, "nova@example.org", "Noa", year=timezone.localdate().year - 13)
    b.user = young
    b.save()
    with pytest.raises(opengames.GameError):
        opengames.publish(b, young, spots=1, level="medium", consent=True)


def test_list_shows_no_contact_data_and_price_split(client, game, muni_a):
    viewer = _person(muni_a, "ve@example.org", "Iago")
    client.force_login(viewer)
    html = client.get(f"{C}/reservas/partidas/").content.decode()
    assert "Sabela P." in html and "Pereira" not in html
    assert "org@example.org" not in html
    assert "3,00" in html  # 12 € entre 2 + 2 persoas


def test_filters(client, game, muni_a):
    viewer = _person(muni_a, "ve@example.org", "Iago")
    client.force_login(viewer)
    assert "Sabela P." in client.get(f"{C}/reservas/partidas/?nivel=medium").content.decode()
    assert "Sabela P." not in client.get(f"{C}/reservas/partidas/?nivel=advanced").content.decode()
    assert "Sabela P." not in client.get(f"{C}/reservas/partidas/?deporte=pool").content.decode()
    day = timezone.localdate(game.booking.start).isoformat()
    assert "Sabela P." in client.get(f"{C}/reservas/partidas/?dia={day}").content.decode()


def test_join_flow_accept_updates_participants(client, game, org, muni_a):
    p = _person(muni_a, "xogadora@example.org", "Uxía Rial")
    client.force_login(p)
    client.post(f"{C}/reservas/partidas/{game.pk}/", {"accion": "unirme"})
    assert not GameJoin.objects.exists()  # sen consentimento non
    client.post(f"{C}/reservas/partidas/{game.pk}/", {"accion": "unirme", "consent": "on"})
    join = GameJoin.objects.get()
    assert join.status == "pending"
    assert Notification.objects.filter(user=org, title__contains="Uxía R.").exists()
    client.force_login(org)
    client.post(f"{C}/reservas/partidas/{game.pk}/", {"accion": "aceptar", "solicitude": join.pk})
    join.refresh_from_db()
    game.booking.refresh_from_db()
    assert join.status == "accepted" and game.booking.participants == 3 and game.spots_left == 1
    # Mensaxes só predefinidas e só entre quen xoga
    client.post(f"{C}/reservas/partidas/{game.pk}/", {"accion": "mensaxe", "codigo": "late5"})
    client.post(
        f"{C}/reservas/partidas/{game.pk}/", {"accion": "mensaxe", "codigo": "ola, chámame"}
    )
    assert game.messages.count() == 1
    outsider = _person(muni_a, "fora@example.org", "Lois")
    with pytest.raises(opengames.GameError):
        opengames.post_message(game, outsider, "ball")


def test_under_14_cannot_join(game, muni_a):
    kid = _person(muni_a, "neno@example.org", "Breixo", year=timezone.localdate().year - 12)
    with pytest.raises(opengames.GameError):
        opengames.request_join(game, kid, consent=True)
    unknown = User.objects.create_user("sen-ano@example.org", display_name="X")
    with pytest.raises(opengames.GameError):
        opengames.request_join(game, unknown, consent=True)


def test_reports_notify_and_hide(game, muni_a, admin_a):
    for i in range(opengames.REPORTS_TO_HIDE):
        opengames.report(game, _person(muni_a, f"r{i}@example.org", f"R{i}"), "fake")
    game.refresh_from_db()
    assert game.hidden_by_reports
    assert Notification.objects.filter(user=admin_a, title__startswith="Denuncia").exists()
    assert opengames.visible_games(muni_a) == []


def test_nearby_town_games_visible(game, muni_b):
    assert game in opengames.visible_games(muni_b)


def test_council_can_disable(client, game, muni_a):
    viewer = _person(muni_a, "ve@example.org", "Iago")
    muni_a.modules = {**muni_a.modules, "open_games": False}
    muni_a.save()
    client.force_login(viewer)
    assert client.get(f"{C}/reservas/partidas/").status_code == 404
    assert opengames.visible_games(muni_a) == []


def test_booking_detail_offers_busco_xente(client, org, padel_a, muni_a):
    start = timezone.now() + dt.timedelta(days=4)
    b = Booking.objects.create(
        municipality=muni_a,
        facility=padel_a,
        user=org,
        start=start,
        end=start + dt.timedelta(hours=1),
        status=Booking.Status.CONFIRMED,
    )
    client.force_login(org)
    assert "Busco xente" in client.get(f"{C}/reservas/{b.pk}/").content.decode()
    r = client.post(
        f"{C}/reservas/{b.pk}/busco-xente/",
        {"spots": 3, "level": "beginner", "message": "", "consent": "on"},
    )
    assert r.status_code == 302 and OpenGame.objects.get(booking=b).spots == 3
