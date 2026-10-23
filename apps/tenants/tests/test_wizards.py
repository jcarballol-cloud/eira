# SPDX-License-Identifier: EUPL-1.2
"""Alta asistida de instalacións (plantillas) e alta de concello en tres pasos desde a deputación."""

import pytest

from apps.accounts.models import Membership, RegionMembership, User
from apps.facilities.models import Facility
from apps.tenants.models import Municipality

pytestmark = pytest.mark.django_db


def test_facility_wizard_with_template(client, admin_a, muni_a):
    client.force_login(admin_a)
    assert "Piscina" in client.get("/c/concello-a/xestion/instalacions/nova/").content.decode()
    r = client.post(
        "/c/concello-a/xestion/instalacions/nova/",
        {
            "plantilla": "pool",
            "name": "Piscina nova",
            "kind": "pool",
            "capacity": 20,
            "slot_minutes": 60,
            "access_level": 3,
            "indoor": "on",
            "lighting": "on",
        },
    )
    f = Facility.objects.get(name="Piscina nova")
    assert r["Location"].endswith(f"/xestion/instalacions/{f.pk}/revisar/")
    assert not f.is_published
    assert f.opening_hours.count() == 6 and f.tariffs.count() == 4 and f.current_rules()
    assert f.maintenance_plans.get().tasks.count() == 3 and f.lock.kind == "connected"
    client.post(f"/c/concello-a/xestion/instalacions/{f.pk}/revisar/")
    f.refresh_from_db()
    assert f.is_published


def test_level1_requires_key_holder(client, admin_a, muni_a):
    client.force_login(admin_a)
    client.post(
        "/c/concello-a/xestion/instalacions/nova/",
        {
            "plantilla": "sports_hall",
            "name": "Pavillón sen chave",
            "kind": "sports_hall",
            "capacity": 1,
            "slot_minutes": 60,
            "access_level": 1,
        },
    )
    assert not Facility.objects.filter(name="Pavillón sen chave").exists()


def test_municipality_wizard_three_steps(client, region):
    dep = User.objects.create_user("dep@example.org")
    RegionMembership.objects.create(user=dep, region=region)
    client.force_login(dep)
    url = "/rexion/proba/novo-concello/"
    r = client.post(
        url,
        {
            "step": 1,
            "name": "Concello Novo",
            "slug": "novo",
            "accent_color": "#2E6A4F",
            "population": 900,
        },
    )
    assert r["Location"].endswith("?paso=2")
    r = client.post(
        url,
        {
            "step": 2,
            "modules": ["bookings", "access", "incidents"],
            "cancellation_hours": 12,
            "max_advance_days": 10,
        },
    )
    assert r["Location"].endswith("?paso=3")
    r = client.post(
        url,
        {"step": 3, "admin_email": "alcaldia@novo.example", "templates": ["outdoor_court", "gym"]},
    )
    m = Municipality.objects.get(slug="novo")
    assert m.region == region and m.cancellation_hours == 12
    assert m.module_enabled("bookings") and not m.module_enabled("activities")
    assert Membership.objects.filter(
        municipality=m, user__email="alcaldia@novo.example", role="admin"
    ).exists()
    assert Facility.objects.filter(municipality=m).count() == 2
    assert r["Location"] == "/c/novo/xestion/"
