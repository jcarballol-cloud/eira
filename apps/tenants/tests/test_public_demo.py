# SPDX-License-Identifier: EUPL-1.2
"""Demo aberta en Internet (EIRA_PUBLIC_DEMO): aviso, vídeos, admin pechado e só correos ficticios;
e o límite de peticións por IP real detrás do proxy."""

import datetime as dt
import importlib
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.test import RequestFactory
from django.urls import clear_url_caches
from django.utils import timezone

from apps.accounts.models import LoginCode, User
from apps.bookings.models import Booking
from apps.integrations.demo import DEMO_PERSONAS
from apps.integrations.models import DevMail
from apps.tenants.demo_checks import missing
from apps.tenants.management.commands.seed_demo import Command
from apps.tenants.models import Municipality
from apps.tenants.public_demo import client_ip, rejects_email

pytestmark = pytest.mark.django_db
NOTICE = "Restáurase cada noite"
REAL_NOW = timezone.now


def at(value):
    """Reloxo fixado na hora de Madrid indicada, que segue avanzando durante a proba."""
    fixed = dt.datetime.fromisoformat(value).replace(tzinfo=ZoneInfo("Europe/Madrid"))
    offset = fixed - REAL_NOW()
    return mock.patch("django.utils.timezone.now", side_effect=lambda: REAL_NOW() + offset)


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


def _request(**meta):
    return RequestFactory().get("/", **meta)


def test_forwarded_header_is_ignored_without_declared_proxy(settings):
    settings.EIRA_BEHIND_PROXY = False
    request = _request(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.9")
    assert client_ip(request) == "10.0.0.1"


def test_behind_proxy_uses_the_address_added_by_the_proxy(settings):
    settings.EIRA_BEHIND_PROXY = True
    forged = _request(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.1.1.1, 203.0.113.9")
    assert client_ip(forged) == "203.0.113.9"
    assert client_ip(_request(REMOTE_ADDR="10.0.0.1")) == "10.0.0.1"


def test_rate_limit_is_per_visitor_behind_proxy(client, settings):
    settings.EIRA_BEHIND_PROXY = True
    settings.EIRA_LOGIN_RATE_LIMIT_IP = 1

    def post(email, ip):
        return client.post("/acceso/", {"email": email}, HTTP_X_FORWARDED_FOR=ip)

    assert post("a@demo.eira.example", "203.0.113.1").status_code == 302
    assert post("b@demo.eira.example", "203.0.113.2").status_code == 302  # outra persoa
    assert post("c@demo.eira.example", "203.0.113.1").status_code == 200  # a mesma: bloqueada
    assert LoginCode.objects.count() == 2


def test_public_demo_only_accepts_fictitious_addresses(client, settings):
    settings.EIRA_PUBLIC_DEMO = True
    response = client.post("/acceso/", {"email": "Alguen@Correo.test"})
    assert response.status_code == 200
    assert "non escribas o teu correo real" in response.content.decode()
    assert not LoginCode.objects.exists() and not DevMail.objects.exists()
    assert client.post("/acceso/", {"email": "proba@demo.eira.example"}).status_code == 302


def test_real_addresses_work_outside_the_public_demo(settings):
    settings.EIRA_PUBLIC_DEMO = False
    assert not rejects_email("alguen@correo.test")


def test_home_shows_notice_and_local_videos_only_in_public_demo(client, settings):
    settings.EIRA_PUBLIC_DEMO = False
    assert NOTICE not in client.get("/").content.decode()

    settings.EIRA_PUBLIC_DEMO = True
    html = client.get("/").content.decode()
    assert NOTICE in html
    for name in ("eira-pitch", "eira-anexo-saude"):
        assert f'src="/videos/{name}.mp4"' in html and f'src="/videos/{name}.webm"' in html
    assert "<iframe" not in html and "youtube" not in html.lower()


def test_seed_reset_removes_visitors_only_in_public_demo(settings):
    User.objects.create_user("alguen@correo.test")
    settings.EIRA_PUBLIC_DEMO = False
    Command().reset()
    assert User.objects.filter(email="alguen@correo.test").exists()

    settings.EIRA_PUBLIC_DEMO = True
    Command().reset()
    assert not User.objects.exists()


def test_django_admin_has_no_route_in_public_demo(client, settings):
    import eira.urls

    assert client.get("/admin/login/").status_code == 200
    try:
        settings.EIRA_PUBLIC_DEMO = True
        importlib.reload(eira.urls)
        clear_url_caches()
        for path in ("/admin/", "/admin/login/"):
            assert client.get(path).status_code == 404
    finally:
        settings.EIRA_PUBLIC_DEMO = False
        importlib.reload(eira.urls)
        clear_url_caches()


@pytest.mark.parametrize("day", ["2026-11-10", "2026-11-14"])  # martes e sábado
def test_examples_last_all_day_after_the_night_reseed(settings, day):
    settings.EIRA_PUBLIC_DEMO = True
    with at(f"{day}T04:00"):
        call_command("seed_demo", verbosity=0)
    for hour in ("09:00", "16:00", "19:30", "23:50"):
        with at(f"{day}T{hour}"):
            assert missing() == [], hour


def test_shared_profiles_can_always_book_in_public_demo(settings):
    """As visitas comparten as contas: ningún perfil pode quedar no máximo de reservas activas."""
    settings.EIRA_PUBLIC_DEMO = True
    call_command("seed_demo", verbosity=0)
    now = timezone.now()
    for email in [p["email"] for p in DEMO_PERSONAS]:
        for town in Municipality.objects.all():
            active = (
                Booking.objects.filter(municipality=town, user__email=email, end__gt=now)
                .holding()
                .count()
            )
            assert active + 20 < min(town.max_active_bookings, town.network_max_active), email
