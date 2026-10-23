# SPDX-License-Identifier: EUPL-1.2
"""v3: axenda do concello en calendario (semana e mes), filtro, estados e .ics."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.activities.models import Activity, Group
from apps.bookings.models import Booking
from apps.facilities.models import Closure

pytestmark = pytest.mark.django_db


@pytest.fixture
def week(padel_a, gym_a, citizen):
    monday = timezone.localdate() - dt.timedelta(days=timezone.localdate().weekday())
    tz = timezone.get_current_timezone()

    def at(days, hour):
        return dt.datetime.combine(monday + dt.timedelta(days=days), dt.time(hour), tzinfo=tz)

    def book(f, days, hour, **kw):
        return Booking.objects.create(
            municipality=f.municipality,
            facility=f,
            user=citizen,
            start=at(days, hour),
            end=at(days, hour) + dt.timedelta(hours=1),
            **kw,
        )

    paid = book(padel_a, 1, 18, status="confirmed", price_cents=400, paid_cents=400)
    pending = book(padel_a, 2, 19, status="pending_payment", price_cents=400)
    book(padel_a, 3, 20, status="cancelled", price_cents=400, paid_cents=400, refunded_cents=400)
    for _ in range(3):
        book(gym_a, 1, 9, status="confirmed")
    Closure.objects.create(
        municipality=padel_a.municipality,
        facility=padel_a,
        reason="Obras na rede",
        starts_at=at(4, 10),
        ends_at=at(4, 12),
    )
    act = Activity.objects.create(municipality=padel_a.municipality, name="Pádel escola")
    Group.objects.create(
        municipality=padel_a.municipality,
        activity=act,
        name="Iniciación",
        facility=padel_a,
        weekdays="0",
        start_time=dt.time(17),
        places=8,
        fee_cents=0,
    )
    return {"monday": monday, "paid": paid, "pending": pending}


def test_week_view_shows_states_and_groups_shared_slots(client, admin_a, week, padel_a):
    client.force_login(admin_a)
    html = client.get(
        f"/c/concello-a/xestion/axenda/?vista=semana&dia={week['monday']}"
    ).content.decode()
    assert f"/xestion/reservas/{week['paid'].pk}/" in html and "ev-paid" in html
    assert "ev-pending" in html and "ev-closed" in html and "ev-activity" in html
    assert "3 reservas" in html  # ximnasio: tres reservas da mesma hora nunha ficha
    assert "Cancelada" not in html  # as canceladas non ocupan a axenda
    assert '<th scope="col"' in html and '<th scope="row"' in html


def test_filter_by_facility(client, admin_a, week, padel_a, gym_a):
    client.force_login(admin_a)
    html = client.get(
        f"/c/concello-a/xestion/axenda/?vista=semana&dia={week['monday']}&i={gym_a.pk}"
    ).content.decode()
    assert "3 reservas" in html and f"/xestion/reservas/{week['paid'].pk}/" not in html


def test_month_view_counts(client, admin_a, week):
    client.force_login(admin_a)
    r = client.get(f"/c/concello-a/xestion/axenda/?vista=mes&dia={week['monday']}")
    days = [d for w in r.context["month"] for d in w["days"]]
    tuesday = next(d for d in days if d["day"] == week["monday"] + dt.timedelta(days=1))
    assert dict((k, n) for k, _l, n in tuesday["counts"]) == {"paid": 1, "reserved": 3}


def test_ics_export_of_filtered_week(client, admin_a, week, padel_a):
    client.force_login(admin_a)
    r = client.get(
        f"/c/concello-a/xestion/axenda/?vista=semana&dia={week['monday']}&i={padel_a.pk}&formato=ics"
    )
    body = r.content.decode()
    assert r["Content-Type"].startswith("text/calendar") and body.count("BEGIN:VEVENT") == 4
    assert "veciña@example.org" not in body and "Veciña" not in body  # sen datos persoais


def test_calendar_admin_only(client, citizen, operator_a, week):
    for u in (citizen, operator_a):
        client.force_login(u)
        assert client.get("/c/concello-a/xestion/axenda/?vista=semana").status_code == 403
