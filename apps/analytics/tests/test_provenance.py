# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · C: limiar de procedencia, despois de cada filtro, e sen reidentificación por cruces."""

import csv
import datetime as dt
import io
import itertools
import json

import pytest
from django.utils import timezone

from apps.accounts.models import (
    Membership,
    RegionMembership,
    Residency,
    ResidencyInvitation,
    Role,
    User,
)
from apps.analytics import provenance
from apps.bookings.models import Booking
from apps.facilities.models import Parish
from apps.tenants.models import Municipality, Region
from conftest import make_facility

pytestmark = pytest.mark.django_db
K = 10


@pytest.fixture
def world():
    region = Region.objects.create(name="Rexión", slug="rex-prov")
    town = Municipality.objects.create(name="Vila", slug="vila-prov", region=region)
    neighbour = Municipality.objects.create(name="Beira", slug="beira-prov", region=region)
    far = Municipality.objects.create(name="Lonxe", slug="lonxe-prov")
    gym = make_facility(town, "gym", name="Ximnasio")
    padel = make_facility(town, "padel", name="Pádel")
    beira_pool = make_facility(neighbour, "pool", name="Piscina da Beira")
    big = Parish.objects.create(municipality=town, name="Bustelo", latitude=42.0, longitude=-8.0)
    small = Parish.objects.create(municipality=town, name="Outeiro", latitude=42.1, longitude=-8.1)
    for f, lat, lon in ((gym, 42.05, -8.05), (padel, 42.02, -8.02), (beira_pool, 42.3, -8.3)):
        f.latitude, f.longitude = lat, lon
        f.save()
    return {
        "region": region,
        "town": town,
        "neighbour": neighbour,
        "far": far,
        "gym": gym,
        "padel": padel,
        "pool": beira_pool,
        "big": big,
        "small": small,
    }


_seq = itertools.count()


def people(n, *, parish=None, town=None, residency=None):
    out = []
    for _i in range(n):
        user = User.objects.create_user(
            f"p{next(_seq)}@example.org", residence_parish=parish, residence_municipality=town
        )
        if residency:
            Residency.objects.create(user=user, municipality=residency, method="counter")
        out.append(user)
    return out


def book(users, facility, days_ago=5, times=1):
    for user in users:
        for t in range(times):
            start = timezone.now() - dt.timedelta(days=days_ago, hours=t)
            Booking.objects.create(
                municipality=facility.municipality,
                facility=facility,
                user=user,
                start=start,
                end=start + dt.timedelta(hours=1),
                status=Booking.Status.USED,
            )


def by_origin(flows):
    return {(r["origin_name"], r["destination_name"]): r["people"] for r in flows["rows"]}


def test_threshold_exactly_10_passes_9_goes_to_others(world):
    book(people(10, parish=world["big"]), world["gym"])
    book(people(9, parish=world["small"]), world["gym"])
    flows = provenance.town_flows(world["town"])
    assert by_origin(flows) == {("Bustelo", "Ximnasio"): 10}
    assert flows["others"][0]["destination_name"] == "Ximnasio"
    assert flows["others"][0]["people"] is None  # 9 < 10: nin sequera o grupo leva cifra


def test_others_sum_shown_only_if_reaches_threshold(world):
    third = Parish.objects.create(municipality=world["town"], name="Fontela")
    book(people(6, parish=world["small"]), world["gym"])
    book(people(5, parish=third), world["gym"])
    flows = provenance.town_flows(world["town"])
    assert flows["rows"] == []
    assert flows["others"][0]["people"] == 11


def test_counts_distinct_people_not_bookings(world):
    book(people(1, parish=world["big"]), world["gym"], times=50)
    flows = provenance.town_flows(world["town"])
    assert flows["rows"] == [] and flows["others"][0]["people"] is None


def test_threshold_applied_after_period_filter(world):
    recent = people(4, parish=world["big"])
    old = people(8, parish=world["big"])
    book(recent, world["gym"], days_ago=5)
    book(old, world["gym"], days_ago=60)
    assert by_origin(provenance.town_flows(world["town"], days=90)) == {("Bustelo", "Ximnasio"): 12}
    assert provenance.town_flows(world["town"], days=30)["rows"] == []


def test_threshold_applied_after_sport_filter(world):
    users = people(12, parish=world["big"])
    book(users, world["gym"])
    book(users[:3], world["padel"])
    assert by_origin(provenance.town_flows(world["town"], kind="gym"))
    assert provenance.town_flows(world["town"], kind="padel")["rows"] == []
    assert provenance.town_flows(world["town"], kind="pool") == {"rows": [], "others": []}


def test_cross_filters_never_show_small_cell(world):
    """Todas as combinacións de filtros: ningunha cifra visible por debaixo do limiar."""
    third = Parish.objects.create(municipality=world["town"], name="Fontela")
    book(people(13, parish=world["big"]), world["gym"], days_ago=5)
    book(people(7, parish=world["big"]), world["padel"], days_ago=5)
    book(people(1, parish=world["small"]), world["padel"], days_ago=5)
    book(people(2, parish=third), world["padel"], days_ago=60)
    book(people(3, town=world["neighbour"]), world["gym"], days_ago=200)
    for days, kind in itertools.product(provenance.PERIODS, ["", "gym", "padel", "pool"]):
        flows = provenance.town_flows(world["town"], days, kind)
        assert all(r["people"] >= K for r in flows["rows"]), (days, kind)
        assert all(o["people"] is None or o["people"] >= K for o in flows["others"]), (days, kind)
        text = provenance.csv_text(flows)
        for row in csv.DictReader(io.StringIO(text)):
            assert row["persoas"] == f"<{K}" or int(row["persoas"]) >= K


def test_lone_person_cannot_be_found_by_narrowing_or_subtraction(world):
    """Unha soa persoa de Outeiro: non se pode deducir nin filtrando nin restando."""
    lone = people(1, parish=world["small"])
    book(lone, world["padel"])
    book(people(12, parish=world["big"]), world["padel"])
    wide = provenance.town_flows(world["town"], 90)
    # Ningunha fila menciona Outeiro e o grupo de «outras» non leva cifra
    assert not any(r["origin_name"] == "Outeiro" for r in wide["rows"])
    assert wide["others"][0]["people"] is None
    # Non hai total por destino co que restar
    assert set(wide) == {"rows", "others"}
    for days, kind in itertools.product(provenance.PERIODS, ["", "padel"]):
        flows = provenance.town_flows(world["town"], days, kind)
        assert "Outeiro" not in provenance.csv_text(flows)
        assert "Outeiro" not in provenance.geojson_text(flows)


def test_free_filters_are_rejected(world):
    assert provenance.clean_filters({"periodo": "1"})["days"] == provenance.DEFAULT_PERIOD
    assert provenance.clean_filters({"periodo": "x", "deporte": "' OR 1"}) == {
        "days": provenance.DEFAULT_PERIOD,
        "kind": "",
    }


def test_other_town_uses_town_never_its_parish(world):
    beira_parish = Parish.objects.create(municipality=world["neighbour"], name="Secreta")
    book(people(10, parish=beira_parish), world["gym"])
    flows = provenance.town_flows(world["town"])
    assert by_origin(flows) == {("Beira", "Ximnasio"): 10}
    assert flows["rows"][0]["origin_kind"] == "municipality"
    assert "Secreta" not in provenance.csv_text(flows)


def test_residency_gives_town_for_outsiders_but_not_parish_for_locals(world):
    book(people(10, residency=world["neighbour"]), world["gym"])
    book(people(12, residency=world["town"]), world["padel"])  # veciñas sen parroquia
    flows = provenance.town_flows(world["town"])
    assert by_origin(flows) == {("Beira", "Ximnasio"): 10}
    assert not [o for o in flows["others"] if o["destination_name"] == "Pádel"]


def test_tenant_isolation_of_flows(world):
    book(people(12, parish=world["big"]), world["pool"])
    assert provenance.town_flows(world["town"]) == {"rows": [], "others": []}


def test_region_flows_between_towns_threshold_and_hotspots(world):
    book(people(11, town=world["neighbour"]), world["gym"])
    book(people(4, parish=world["big"]), world["pool"])
    book(people(12, parish=world["big"]), world["gym"])  # dentro do mesmo concello: non é fluxo
    flows = provenance.region_flows(world["region"])
    assert by_origin(flows) == {("Beira", "Vila"): 11}
    assert flows["hotspots"] == [{"name": "Vila", "people": 11}]
    assert flows["others"] == [
        {"destination_name": "Beira", "destination": world["neighbour"], "people": None}
    ]


def test_region_outside_towns_are_not_named(world):
    book(people(15, town=world["far"]), world["gym"])
    flows = provenance.region_flows(world["region"])
    assert flows["rows"] == []
    assert "Lonxe" not in provenance.csv_text(flows)
    assert flows["others"][0]["people"] == 15


def test_region_cross_filters(world):
    book(people(11, town=world["neighbour"]), world["gym"], days_ago=5)
    book(people(2, town=world["neighbour"]), world["padel"], days_ago=5)
    for days, kind in itertools.product(provenance.PERIODS, ["", "gym", "padel"]):
        flows = provenance.region_flows(world["region"], days, kind)
        assert all(r["people"] >= K for r in flows["rows"])
        assert all(h["people"] >= K for h in flows["hotspots"])
        assert all(o["people"] is None or o["people"] >= K for o in flows["others"])
    assert provenance.region_flows(world["region"], kind="padel")["rows"] == []


def test_exports_csv_and_geojson_are_aggregated(client, world):
    admin = User.objects.create_user("admin-prov@example.org")
    Membership.objects.create(user=admin, municipality=world["town"], role=Role.ADMIN)
    users = people(10, parish=world["big"])
    book(users, world["gym"])
    client.force_login(admin)
    url = f"/c/{world['town'].slug}/xestion/procedencia/"
    text = client.get(url + "?formato=csv").content.decode("utf-8-sig")
    assert "Bustelo,Ximnasio,10" in text and "example.org" not in text
    geo = json.loads(client.get(url + "?formato=geojson").content)
    feature = geo["features"][0]
    assert feature["geometry"]["type"] == "LineString" and feature["properties"]["people"] == 10
    assert set(feature["properties"]) == {"origin", "destination", "people", "bookings"}
    assert "example.org" not in json.dumps(geo)


def test_panel_map_table_and_permissions(client, world):
    book(people(10, parish=world["big"]), world["gym"])
    url = f"/c/{world['town'].slug}/xestion/procedencia/"
    citizen = User.objects.create_user("c-prov@example.org")
    client.force_login(citizen)
    assert client.get(url).status_code == 403
    admin = User.objects.create_user("admin2-prov@example.org")
    Membership.objects.create(user=admin, municipality=world["town"], role=Role.ADMIN)
    client.force_login(admin)
    html = client.get(url).content.decode()
    assert "<svg" in html and "flow-map__line" in html and "Bustelo" in html and "<table" in html
    assert "Beira" in html  # concellos da rede coa súa posición
    # A deputación entra en consulta porque é agregado
    dep = User.objects.create_user("dep-prov@example.org")
    RegionMembership.objects.create(user=dep, region=world["region"])
    client.force_login(dep)
    assert client.get(url).status_code == 200
    assert client.get(f"/rexion/{world['region'].slug}/mobilidade/").status_code == 200
    other = User.objects.create_user("outra-prov@example.org")
    client.force_login(other)
    assert client.get(f"/rexion/{world['region'].slug}/mobilidade/").status_code == 403


def test_person_sets_and_removes_residence_and_sees_distances(client, world):
    user = User.objects.create_user("eu-prov@example.org")
    Residency.objects.create(user=user, municipality=world["town"], method="counter")
    Membership.objects.create(user=user, municipality=world["town"], role=Role.CITIZEN)
    client.force_login(user)
    base = f"/c/{world['town'].slug}/app/proximos/"
    assert "Onde estou" in client.get(base).content.decode()
    client.post(base + "residencia/", {"residence": f"p{world['big'].pk}"})
    user.refresh_from_db()
    assert user.residence_parish == world["big"]
    html = client.get(base).content.decode()
    assert "Bustelo" in html and "km" in html and "Piscina da Beira" in html
    client.post(base + "residencia/", {"residence": ""})
    user.refresh_from_db()
    assert user.residence_parish is None


def test_cannot_pick_parish_of_other_town(client, world):
    user = User.objects.create_user("eu2-prov@example.org")
    Membership.objects.create(user=user, municipality=world["town"], role=Role.CITIZEN)
    alien = Parish.objects.create(municipality=world["far"], name="Allea")
    client.force_login(user)
    url = f"/c/{world['town'].slug}/app/proximos/residencia/"
    assert client.post(url, {"residence": f"p{alien.pk}"}).status_code == 404
    assert client.post(url, {"residence": f"m{world['far'].pk}"}).status_code == 404


def test_no_gps_fields_or_browser_geolocation():
    from pathlib import Path

    from django.conf import settings

    names = {f.name for f in User._meta.get_fields()}
    assert not names & {"latitude", "longitude", "gps", "location", "address"}
    root = Path(settings.BASE_DIR)
    for folder in ("static/js", "templates"):
        for path in (root / folder).rglob("*"):
            if path.suffix in (".js", ".html"):
                assert "geolocation" not in path.read_text(encoding="utf-8"), path


def test_padron_parish_is_only_thing_kept_and_passes_on_redeem(world):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.accounts import padron

    data = "dni_nie;data_nacemento;parroquia\n12345678Z;31/12/1980;Bustelo\n00000001R;01/02/1990;Inventada\n"
    padron.import_csv(world["town"], SimpleUploadedFile("p.csv", data.encode()))
    assert padron.parish_for(world["town"], "12345678Z", "31/12/1980") == world["big"]
    assert padron.parish_for(world["town"], "00000001R", "01/02/1990") is None
    invitation = ResidencyInvitation.issue(world["town"])
    invitation.parish = world["big"]
    invitation.save()
    user = User.objects.create_user("alta-prov@example.org")
    ResidencyInvitation.redeem(user, invitation.code)
    user.refresh_from_db()
    assert user.residence_parish == world["big"]


def test_padron_without_parish_column_still_works(world):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.accounts import padron

    data = "dni_nie;data_nacemento\n12345678Z;31/12/1980\n"
    batch = padron.import_csv(world["town"], SimpleUploadedFile("p.csv", data.encode()))
    assert batch.count == 1 and padron.matches(world["town"], "12345678Z", "31/12/1980")
    assert padron.parish_for(world["town"], "12345678Z", "31/12/1980") is None


def test_distance_haversine():
    assert round(provenance.distance_km((42.0, -8.0), (42.0, -8.0)), 3) == 0
    assert 100 < provenance.distance_km((42.0, -8.0), (43.0, -8.0)) < 120
