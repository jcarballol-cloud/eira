# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · D: cálculos de rendemento (ocupación, uso real, consumo estimado, coste, CO₂, perfil)."""

import datetime as dt
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.analytics import performance
from apps.bookings.models import Booking
from apps.facilities.models import Closure, EnergyReading, Equipment, OpeningHours

pytestmark = pytest.mark.django_db
C = "/c/concello-a"
MONDAY = dt.date(2026, 3, 2)  # luns


@pytest.fixture
def court(padel_a):
    """Pista aberta só os luns de 10 a 14 (4 h) para facer as contas á man."""
    padel_a.opening_hours.all().delete()
    OpeningHours.objects.create(facility=padel_a, weekday=0, opens=dt.time(10), closes=dt.time(14))
    padel_a.capacity = 1
    padel_a.save()
    return padel_a


def _at(day, hour):
    return timezone.make_aware(dt.datetime.combine(day, dt.time(hour)))


def _b(f, hour, status=Booking.Status.USED, light=False, user=None, checkin_late=0, day=MONDAY):
    start = _at(day, hour)
    return Booking.objects.create(
        municipality=f.municipality,
        facility=f,
        user=user,
        start=start,
        end=start + dt.timedelta(hours=1),
        status=status,
        checked_in_at=start + dt.timedelta(minutes=checkin_late)
        if status == Booking.Status.USED
        else None,
        needs_light=light,
    )


def test_occupancy_real_use_and_average(court):
    _b(court, 10)
    _b(court, 11, checkin_late=15)
    _b(court, 12, status=Booking.Status.NO_SHOW)
    s = performance.period_stats(court, MONDAY, MONDAY + dt.timedelta(days=7))
    assert s["available_h"] == 4.0
    assert s["booked_h"] == 3.0 and s["occupancy_pct"] == 75
    assert s["used_h"] == 2.0 and s["real_use_pct"] == 50
    assert s["avg_use_min"] == round((60 + 45) / 2)


def test_closures_reduce_available_hours(court):
    Closure.objects.create(
        municipality=court.municipality,
        facility=court,
        reason="Obras",
        starts_at=_at(MONDAY, 12),
        ends_at=_at(MONDAY, 13),
    )
    s = performance.period_stats(court, MONDAY, MONDAY + dt.timedelta(days=1))
    assert s["available_h"] == 3.0


def test_estimated_kwh_cost_and_co2_by_mode(court, muni_a):
    muni_a.energy_price_eur_kwh = Decimal("0.2")
    muni_a.co2_kg_kwh = Decimal("0.1")
    muni_a.save()
    court.refresh_from_db()
    Equipment.objects.create(
        facility=court,
        kind="hvac",
        power_kw=Decimal("2"),
        mode="opening",
        use_factor=Decimal("0.5"),
    )
    Equipment.objects.create(
        facility=court, kind="other", power_kw=Decimal("3"), mode="booking", use_factor=Decimal("1")
    )
    Equipment.objects.create(
        facility=court,
        kind="lighting",
        power_kw=Decimal("4"),
        mode="light",
        use_factor=Decimal("1"),
    )
    Equipment.objects.create(
        facility=court,
        kind="pumps",
        power_kw=Decimal("1"),
        mode="continuous",
        use_factor=Decimal("0.25"),
    )
    _b(court, 10, light=True)
    _b(court, 11)
    _b(court, 12, status=Booking.Status.NO_SHOW)  # non acende nada
    s = performance.period_stats(court, MONDAY, MONDAY + dt.timedelta(days=1))
    # apertura 4 h × 2 × 0,5 = 4 · reserva 2 h × 3 = 6 · luz 1 h × 4 = 4 · continuo 24 h × 0,25 = 6
    assert s["kwh"] == Decimal("20.0")
    assert s["cost_eur"] == Decimal("4.00") and s["co2_kg"] == Decimal("2.0")
    assert s["kwh_per_use_h"] == Decimal("10.00") and s["eur_per_use_h"] == Decimal("2.00")


def test_shared_facility_uses_union_and_capacity(gym_a):
    gym_a.opening_hours.all().delete()
    OpeningHours.objects.create(facility=gym_a, weekday=0, opens=dt.time(10), closes=dt.time(12))
    gym_a.capacity = 4
    gym_a.save()
    Equipment.objects.create(
        facility=gym_a, kind="other", power_kw=Decimal("1"), mode="booking", use_factor=Decimal("1")
    )
    for _ in range(4):
        _b(gym_a, 10)
    s = performance.period_stats(gym_a, MONDAY, MONDAY + dt.timedelta(days=1))
    assert s["occupancy_pct"] == 50  # 4 h-praza de 2 h × 4 prazas
    assert s["kwh"] == Decimal("1.0")  # catro persoas á vez: o equipo funciona unha hora


def test_profile_needs_ten_people(court):
    for i in range(9):
        u = User.objects.create_user(f"u{i}@example.org", birth_year=1990)
        _b(court, 10, user=u, day=MONDAY + dt.timedelta(days=7 * i))
    p = performance.profile(court, MONDAY, MONDAY + dt.timedelta(days=200))
    assert p == {"n": 9, "enough": False}
    _b(court, 11, user=User.objects.create_user("u9@example.org", birth_year=1950))
    p = performance.profile(court, MONDAY, MONDAY + dt.timedelta(days=200))
    assert p["enough"] and p["n"] == 10
    assert {b["label"]: b["pct"] for b in p["bands"]}["65+"] == 10


def test_reading_vs_estimate(court):
    Equipment.objects.create(
        facility=court, kind="hvac", power_kw=Decimal("1"), mode="opening", use_factor=Decimal("1")
    )
    EnergyReading.objects.create(
        facility=court, period_start=MONDAY, period_end=MONDAY, kwh=Decimal("5")
    )
    r = performance.readings_vs_estimate(court)[0]
    assert r["estimate"] == Decimal("4.0") and r["diff_pct"] == -20


def test_month_start_arithmetic():
    assert performance._month_start(dt.date(2026, 1, 15), 1) == dt.date(2025, 12, 1)
    assert performance._month_start(dt.date(2026, 12, 15), -1) == dt.date(2027, 1, 1)
    assert performance._month_start(dt.date(2026, 3, 1), 14) == dt.date(2025, 1, 1)


def test_panel_and_region(client, admin_a, court, region):
    from apps.accounts.models import RegionMembership

    client.force_login(admin_a)
    html = client.get(f"{C}/xestion/instalacions/{court.pk}/rendemento/").content.decode()
    assert "Estimación orientativa" in html and "Inventario de equipos" in html
    r = client.post(
        f"{C}/xestion/instalacions/{court.pk}/rendemento/",
        {
            "accion": "equipos",
            "eq-TOTAL_FORMS": "1",
            "eq-INITIAL_FORMS": "0",
            "eq-0-kind": "lighting",
            "eq-0-power_kw": "2.5",
            "eq-0-mode": "light",
            "eq-0-use_factor": "1",
        },
    )
    assert r.status_code == 302 and court.energy_equipment.count() == 1
    assert client.get(f"{C}/xestion/rendemento/").status_code == 200
    dep = User.objects.create_user("dep@example.org")
    RegionMembership.objects.create(user=dep, region=region)
    client.force_login(dep)
    html = client.get(f"/rexion/{region.slug}/").content.decode()
    assert "Rendemento (últimos 30 días)" in html
    # A deputación ve o panel (só agregados) pero non pode editar
    r = client.get(f"{C}/xestion/instalacions/{court.pk}/rendemento/")
    assert r.status_code == 200 and "Gardar equipos" not in r.content.decode()
