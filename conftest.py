# SPDX-License-Identifier: EUPL-1.2
"""Fixtures comúns: dous concellos illados con instalacións creadas a partir das plantillas."""

import datetime as dt

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import Membership, Residency, Role, User
from apps.facilities.catalog import apply_template
from apps.facilities.models import Facility, FacilityKind
from apps.integrations.registry import reset_adapters
from apps.tenants.models import Municipality, Region


@pytest.fixture(autouse=True)
def _clean_state(settings):
    settings.EIRA_DEMO_TOOLS = True
    cache.clear()
    reset_adapters()
    yield
    cache.clear()


def make_facility(muni, key="padel", level=None, **extra):
    from apps.facilities.catalog import TEMPLATES

    t = TEMPLATES[key]
    f = Facility.objects.create(
        municipality=muni, name=extra.pop("name", f"{t['label']} {muni.slug}"), kind=t["kind"],
        capacity=t["capacity"], slot_minutes=t["slot_minutes"], indoor=t["indoor"], lighting=t["lighting"],
        access_level=t["access_level"] if level is None else level, latitude=42.5, longitude=-8.1,
        key_holder_name="Bar de proba", key_holder_email="custodia@example.org", **extra,
    )
    apply_template(f, key)
    return f


@pytest.fixture
def region(db):
    return Region.objects.create(name="Deputación de proba", slug="proba")


@pytest.fixture
def muni_a(region):
    return Municipality.objects.create(name="Concello A", slug="concello-a", region=region, max_advance_days=30)


@pytest.fixture
def muni_b(region):
    return Municipality.objects.create(name="Concello B", slug="concello-b", region=region, max_advance_days=30)


@pytest.fixture
def padel_a(muni_a):
    return make_facility(muni_a, "padel", level=2)


@pytest.fixture
def gym_a(muni_a):
    return make_facility(muni_a, "gym", level=2)


@pytest.fixture
def pool_a(muni_a):
    return make_facility(muni_a, "pool", level=3)


@pytest.fixture
def hall_a(muni_a):
    return make_facility(muni_a, "sports_hall", level=1)


@pytest.fixture
def court_b(muni_b):
    return make_facility(muni_b, "outdoor_court", level=0)


@pytest.fixture
def citizen(muni_a):
    u = User.objects.create_user("veciña@example.org", display_name="Veciña", birth_year=1990)
    Membership.objects.create(user=u, municipality=muni_a, role=Role.CITIZEN)
    Residency.objects.create(user=u, municipality=muni_a, method=Residency.Method.COUNTER)
    return u


@pytest.fixture
def outsider(db):
    return User.objects.create_user("forastera@example.org", display_name="Forastera", birth_year=1985)


@pytest.fixture
def admin_a(muni_a):
    u = User.objects.create_user("admin-a@example.org")
    Membership.objects.create(user=u, municipality=muni_a, role=Role.ADMIN)
    return u


@pytest.fixture
def admin_b(muni_b):
    u = User.objects.create_user("admin-b@example.org")
    Membership.objects.create(user=u, municipality=muni_b, role=Role.ADMIN)
    return u


@pytest.fixture
def operator_a(muni_a):
    u = User.objects.create_user("operario@example.org")
    Membership.objects.create(user=u, municipality=muni_a, role=Role.MAINTENANCE)
    return u


def next_slot(facility, days=2, hour=19):
    """Primeira franxa dispoñible `days` días despois, á hora indicada ou a primeira do día."""
    from apps.bookings.services import slot_starts

    for extra in range(0, 7):
        day = timezone.localdate() + dt.timedelta(days=days + extra)
        starts = slot_starts(facility, day)
        for s in starts:
            if timezone.localtime(s).hour == hour:
                return s
        if starts:
            return starts[0]
    raise AssertionError("Sen franxas")
