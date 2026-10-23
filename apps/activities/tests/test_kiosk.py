# SPDX-License-Identifier: EUPL-1.2
"""v3: tableta da monitora (quiosco): inicial do primeiro apelido e API de toques."""

import datetime as dt
import json

import pytest
from django.utils import timezone

from apps.accounts.models import Consent, Dependent, Household, Membership, Role, User
from apps.activities.models import Activity, Attendance, Enrollment, Group, Session
from apps.activities.names import initial, sort_key

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "surnames, name, expected",
    [
        ("da Silva Pazos", "Ana", "S"),
        ("de la Fuente", "Xan", "F"),
        ("Do Campo", "Iria", "C"),
        ("dos Santos", "Luís", "S"),
        ("Álvarez Rial", "Eva", "A"),
        ("Ñeiro Souto", "Rosa", "Ñ"),
        ("Núñez", "Brais", "N"),
        ("Mc Donald", "Ian", "D"),
        ("", "Úrsula", "U"),
        ("Y", "Pepe", "Y"),
    ],
)
def test_initial_of_first_surname(surnames, name, expected):
    assert initial(surnames, name) == expected


def test_sort_by_surname_ignoring_particles_and_accents():
    people = [("da Silva", "B"), ("Álvarez", "C"), ("Souto", "A")]
    ordered = sorted(people, key=lambda p: sort_key(*p))
    assert [p[0] for p in ordered] == ["Álvarez", "da Silva", "Souto"]


@pytest.fixture
def setup(muni_a, citizen):
    monitor = User.objects.create_user("monitora@example.org")
    Membership.objects.create(user=monitor, municipality=muni_a, role=Role.MONITOR)
    a = Activity.objects.create(municipality=muni_a, name="Fútbol")
    g = Group.objects.create(
        municipality=muni_a,
        activity=a,
        name="Mixto",
        monitor=monitor,
        min_age=0,
        max_age=110,
        places=10,
        fee_cents=0,
        weekdays="0,1,2,3,4,5,6",
        start_time=dt.time(17),
        rpe_scale="omni",
    )
    hh = Household.objects.create(responsible=citizen)
    year = timezone.localdate().year
    kid = Dependent.objects.create(
        household=hh, first_name="Lúa", surnames="Ñeiro Pazos", birth_year=year - 9
    )
    Consent.objects.create(dependent=kid, kind="data", granted_by=citizen)
    e_kid = Enrollment.objects.create(
        municipality=muni_a, group=g, user=citizen, dependent=kid, status="active"
    )
    citizen.surnames = "da Silva"
    citizen.save()
    e_adult = Enrollment.objects.create(municipality=muni_a, group=g, user=citizen, status="active")
    s = Session.objects.create(
        municipality=muni_a, group=g, date=timezone.localdate(), start_time=dt.time(17)
    )
    return {"monitor": monitor, "session": s, "kid": e_kid, "adult": e_adult}


def api(client, s, events):
    return client.post(
        f"/c/concello-a/monitor/sesion/{s.pk}/rexistro/api/",
        data=json.dumps(events),
        content_type="application/json",
    )


def test_kiosk_page_lists_people_by_initial(client, setup):
    client.force_login(setup["monitor"])
    r = client.get(f"/c/concello-a/monitor/sesion/{setup['session'].pk}/rexistro/")
    data = r.context["data"]
    by_name = {p["name"]: p for p in data["people"]}
    assert by_name["Lúa"]["initial"] == "Ñ" and by_name["Lúa"]["label"] == "Ñeiro Pazos, Lúa"
    assert not by_name["Lúa"]["effort"]  # sen consentimento de esforzo
    assert data["scale"] == "omni" and len(data["points"]) == 11


def test_api_entry_and_exit_last_value_wins(client, setup):
    client.force_login(setup["monitor"])
    s, e = setup["session"], setup["adult"]
    assert api(client, s, [{"enrollment": e.pk, "action": "in"}]).json()["ok"]
    a = Attendance.objects.get(session=s, enrollment=e)
    assert a.present and a.checked_in_at and a.rpe is None
    api(
        client,
        s,
        [
            {"enrollment": e.pk, "action": "out", "value": 6},
            {"enrollment": e.pk, "action": "out", "value": 4},
        ],
    )
    a.refresh_from_db()
    assert a.rpe == 4 and a.rpe_at


def test_api_exit_without_entry_marks_present(client, setup):
    client.force_login(setup["monitor"])
    s, e = setup["session"], setup["adult"]
    api(client, s, [{"enrollment": e.pk, "action": "out", "value": 7}])
    a = Attendance.objects.get(session=s, enrollment=e)
    assert a.present and a.rpe == 7


def test_api_respects_effort_consent_of_minors(client, setup):
    client.force_login(setup["monitor"])
    s, e = setup["session"], setup["kid"]
    api(client, s, [{"enrollment": e.pk, "action": "out", "value": 8}])
    a = Attendance.objects.get(session=s, enrollment=e)
    assert a.present and a.rpe is None


def test_api_ignores_people_from_other_groups_and_other_monitors(client, setup, muni_a):
    other = User.objects.create_user("outra@example.org")
    Membership.objects.create(user=other, municipality=muni_a, role=Role.MONITOR)
    client.force_login(other)
    assert (
        api(
            client, setup["session"], [{"enrollment": setup["adult"].pk, "action": "in"}]
        ).status_code
        == 404
    )
    client.force_login(setup["monitor"])
    r = api(
        client,
        setup["session"],
        [
            {"enrollment": 999999, "action": "in"},
            {"enrollment": setup["adult"].pk, "action": "borrar"},
        ],
    )
    assert r.json()["applied"] == [] and not Attendance.objects.exists()
