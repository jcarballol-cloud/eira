# SPDX-License-Identifier: EUPL-1.2
"""v5 · A: reservar en concellos próximos da mesma rede coa mesma conta."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.bookings import payments, services
from apps.bookings.models import Booking, Payment
from apps.facilities.models import Tariff
from apps.integrations.models import FakePayment
from apps.notifications.models import Notice
from conftest import make_facility, next_slot

pytestmark = pytest.mark.django_db
A, B = "/c/concello-a", "/c/concello-b"


@pytest.fixture
def padel_b(muni_b):
    return make_facility(muni_b, "padel", level=2, name="Pádel de B")


def book_in_b(client, citizen, facility, start=None):
    client.force_login(citizen)
    start = start or next_slot(facility)
    return client.post(
        f"{B}/instalacions/{facility.pk}/reservar/",
        {"inicio": start.isoformat(), "accept_rules": "on", "participants": "2"},
    )


def test_neighbour_of_a_books_in_b_with_non_resident_tariff_and_b_tpv(
    client, citizen, padel_b, muni_a, muni_b
):
    tariffs = {t.audience: t.price_cents for t in padel_b.tariffs.all()}
    assert tariffs[Tariff.Audience.NON_RESIDENT] > tariffs[Tariff.Audience.RESIDENT]
    # O prezo vese antes de pagar
    start = next_slot(padel_b)
    client.force_login(citizen)
    html = client.get(
        f"{B}/instalacions/{padel_b.pk}/reservar/", {"inicio": start.isoformat()}
    ).content.decode()
    assert "non empadroadas" in html and "Concello A" in html
    r = book_in_b(client, citizen, padel_b, start)
    assert "/dev/tpv/" in r["Location"]
    b = Booking.objects.get(user=citizen)
    assert b.municipality == muni_b and b.network_origin == muni_a
    assert b.tariff_audience == Tariff.Audience.NON_RESIDENT
    assert b.price_cents == tariffs[Tariff.Audience.NON_RESIDENT]
    payment = Payment.objects.get(booking=b)
    assert payment.municipality == muni_b  # o cobro é do concello de destino
    fake = FakePayment.objects.get(reference=payment.reference)
    assert "Concello B" in fake.merchant and "Concello A" not in fake.merchant
    assert "Concello B" in client.get(r["Location"]).content.decode()


def test_destination_can_close_to_the_network(client, citizen, padel_b, muni_b):
    muni_b.network_open = False
    muni_b.save()
    r = book_in_b(client, citizen, padel_b)
    assert r.status_code == 200 and "non admite agora reservas" in r.content.decode()
    assert not Booking.objects.exists()
    with pytest.raises(services.BookingError):
        services.create_booking(
            padel_b, next_slot(padel_b), citizen, rules_version=padel_b.current_rules()
        )
    # A súa propia veciñanza segue reservando
    from apps.accounts.models import Membership, Role, User

    local = User.objects.create_user("local-b@example.org")
    Membership.objects.create(user=local, municipality=muni_b, role=Role.CITIZEN)
    services.create_booking(
        padel_b, next_slot(padel_b), local, rules_version=padel_b.current_rules()
    )


def test_network_quota_and_advance(citizen, padel_b, muni_b):
    muni_b.network_max_active = 1
    muni_b.network_advance_days = 3
    muni_b.save()
    rules = padel_b.current_rules()
    with pytest.raises(services.BookingError, match="antelación"):
        services.create_booking(padel_b, next_slot(padel_b, days=6), citizen, rules_version=rules)
    services.create_booking(padel_b, next_slot(padel_b, days=1), citizen, rules_version=rules)
    with pytest.raises(services.BookingError, match="máximo"):
        services.create_booking(padel_b, next_slot(padel_b, days=2), citizen, rules_version=rules)
    # A grella tamén lle mostra só os días que pode reservar
    grid = services.week_grid(padel_b, timezone.localdate() + dt.timedelta(days=7), citizen)
    assert not any(s.bookable for _d, slots in grid["by_day"] for s in slots)


def test_destination_staff_sees_only_what_is_needed(client, citizen, padel_b, admin_b, admin_a):
    citizen.display_name = ""
    citizen.phone = "600000000"
    citizen.save()
    b = services.create_booking(
        padel_b, next_slot(padel_b), citizen, rules_version=padel_b.current_rules()
    )
    client.force_login(admin_b)
    html = client.get(f"{B}/xestion/reservas/{b.pk}/").content.decode()
    assert citizen.email not in html and "600000000" not in html
    assert "Persoa de Concello A" in html
    agenda = client.get(f"{B}/xestion/axenda/?dia={timezone.localdate(b.start)}").content.decode()
    assert citizen.email not in agenda
    # O concello de orixe non ve a reserva
    client.force_login(admin_a)
    assert client.get(f"{A}/xestion/reservas/{b.pk}/").status_code == 404


def test_my_bookings_and_home_show_bookings_in_other_towns(client, citizen, padel_b):
    b = services.create_booking(
        padel_b, next_slot(padel_b), citizen, rules_version=padel_b.current_rules()
    )
    payments.start_online_payment(booking=b, url_ok="/ok", url_ko="/ko")
    from apps.integrations.registry import get_adapter

    fake = FakePayment.objects.get()
    payments.handle_notification(get_adapter("payment").build_notification(fake, ok=True))
    client.force_login(citizen)
    mine = client.get(f"{A}/reservas/").content.decode()
    assert "Noutros concellos" in mine and f"{B}/reservas/{b.pk}/" in mine
    home = client.get(f"{A}/app/").content.decode()
    assert "Pádel de B" in home and f"{B}/reservas/{b.pk}/" in home


def test_switcher_and_nearby_page(client, citizen, padel_b, muni_b, padel_a):
    client.force_login(citizen)
    html = client.get(f"{A}/").content.decode()
    assert 'name="concello"' in html and "Concello B" in html
    r = client.get(f"{A}/app/proximos/ir/", {"concello": "concello-b"})
    assert r["Location"] == f"{B}/"
    nearby = client.get(f"{A}/app/proximos/").content.decode()
    assert "Concello B" in nearby and "Reservar en Concello B" in nearby
    # Visitando B, a app segue sendo a de A (lapelas) e avísase da tarifa
    visit = client.get(f"{B}/").content.decode()
    assert f'href="{A}/app/"' in visit and "non empadroadas" in visit
    muni_b.network_open = False
    muni_b.save()
    assert "Reservar en Concello B" not in client.get(f"{A}/app/proximos/").content.decode()


def test_nearby_activities_and_events_are_optional(client, citizen, muni_b, admin_b):
    Notice.objects.create(
        municipality=muni_b,
        category="event",
        title="Carreira popular de B",
        body="Domingo ás 10:00.",
        audience=Notice.Audience.ALL,
        sent_at=timezone.now(),
    )
    client.force_login(citizen)
    assert "Carreira popular de B" not in client.get(f"{A}/avisos/").content.decode()
    client.post(f"{A}/app/proximos/seguir/", {"concello": "concello-b", "on": "1"})
    citizen.refresh_from_db()
    assert citizen.network_feed == ["concello-b"]
    html = client.get(f"{A}/avisos/").content.decode()
    assert "Carreira popular de B" in html and "Concellos próximos" in html
    # Filtrable por concello
    assert (
        "Carreira popular de B"
        in client.get(f"{A}/avisos/", {"proximo": "concello-b"}).content.decode()
    )
    client.post(f"{A}/app/proximos/seguir/", {"concello": "concello-b", "on": "0"})
    assert "Carreira popular de B" not in client.get(f"{A}/avisos/").content.decode()
