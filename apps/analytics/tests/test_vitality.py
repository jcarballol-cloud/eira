# SPDX-License-Identifier: EUPL-1.2
"""v5 · G: índice de vida activa (0–100) con umbral n ≥ 10 e pesos configurables."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.analytics.vitality import facility_index, weights_for
from apps.bookings.models import Booking, Rating
from apps.maintenance.models import WorkOrder

pytestmark = pytest.mark.django_db


def used_bookings(facility, people, n, score=None):
    """`n` reservas usadas nas últimas semanas, repartidas entre `people`."""
    from apps.bookings.services import slot_starts

    made = 0
    day = timezone.localdate() - dt.timedelta(days=1)
    while made < n:
        for s in slot_starts(facility, day):
            if made >= n:
                break
            user = people[made % len(people)]
            b = Booking.objects.create(
                municipality=facility.municipality,
                facility=facility,
                user=user,
                start=s,
                end=s + dt.timedelta(minutes=facility.slot_minutes),
                status=Booking.Status.USED,
                checked_in_at=s,
                rules_version=facility.current_rules(),
            )
            if score:
                Rating.objects.create(
                    municipality=facility.municipality, booking=b, facility=facility, score=score
                )
            made += 1
        day -= dt.timedelta(days=1)


@pytest.fixture
def people(db):
    years = [1950, 1960, 1975, 1985, 1995, 2005, 1948, 1970, 1990, 2008, 1980, 1958]
    return [
        User.objects.create_user(f"p{i}@example.org", birth_year=y) for i, y in enumerate(years)
    ]


def test_without_enough_people_shows_no_figure(padel_a, people):
    used_bookings(padel_a, people[:3], 6)
    idx = facility_index(padel_a)
    assert idx["value"] is None
    assert idx["components"]["occupancy"]["value"] is None  # n = 6 < 10
    assert idx["components"]["accessibility"]["value"] is not None  # sen datos de persoas


def test_index_with_data_and_configurable_weights(padel_a, people, muni_a):
    used_bookings(padel_a, people, 40, score="good")
    WorkOrder.objects.create(
        municipality=muni_a,
        facility=padel_a,
        title="Revisión",
        due_date=timezone.localdate(),
        status=WorkOrder.Status.DONE,
        closed_at=timezone.now() - dt.timedelta(days=3),
    )
    idx = facility_index(padel_a)
    c = idx["components"]
    assert c["satisfaction"]["value"] == 100 and c["satisfaction"]["n"] == 40
    assert c["diversity"]["value"] > 70  # idades ben repartidas entre 12 persoas
    assert c["maintenance"]["value"] == 100
    assert 0 <= idx["value"] <= 100
    # Só satisfacción → o índice é a satisfacción
    muni_a.vitality_weights = {
        "occupancy": 0,
        "diversity": 0,
        "satisfaction": 50,
        "accessibility": 0,
        "maintenance": 0,
    }
    muni_a.save()
    padel_a.refresh_from_db()
    assert weights_for(muni_a)["satisfaction"] == 50
    assert facility_index(padel_a)["value"] == 100


def test_diversity_low_when_everyone_is_the_same_age(padel_a, db):
    same = [User.objects.create_user(f"s{i}@example.org", birth_year=1990) for i in range(12)]
    used_bookings(padel_a, same, 24)
    assert facility_index(padel_a)["components"]["diversity"]["value"] == 0


def test_index_visible_in_facility_page_dashboard_and_region(
    client, padel_a, people, admin_a, region
):
    used_bookings(padel_a, people, 30, score="ok")
    html = client.get(f"/c/concello-a/instalacions/{padel_a.pk}/").content.decode()
    assert "Índice de vida activa" in html
    client.force_login(admin_a)
    assert "Índice de vida activa" in client.get("/c/concello-a/xestion/").content.decode()
    from apps.accounts.models import RegionMembership

    dep = User.objects.create_user("dep@example.org")
    RegionMembership.objects.create(user=dep, region=region)
    client.force_login(dep)
    assert "Índice de vida activa" in client.get(f"/rexion/{region.slug}/").content.decode()
    # O observatorio segue no seu sitio
    client.force_login(admin_a)
    assert client.get("/c/concello-a/actividades/observatorio/").status_code == 200
