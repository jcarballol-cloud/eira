# SPDX-License-Identifier: EUPL-1.2
"""Illamento entre concellos e permisos por rol."""

import pytest

from apps.bookings.models import Booking
from apps.bookings.services import create_booking
from apps.incidents.models import Incident
from conftest import next_slot

pytestmark = pytest.mark.django_db


def test_facility_of_other_municipality_is_404(client, padel_a, court_b):
    assert client.get(f"/c/concello-a/instalacions/{padel_a.pk}/").status_code == 200
    assert client.get(f"/c/concello-a/instalacions/{court_b.pk}/").status_code == 404
    assert client.get(f"/c/concello-b/instalacions/{padel_a.pk}/").status_code == 404


def test_listing_only_shows_own_facilities(client, padel_a, court_b):
    html = client.get("/c/concello-a/").content.decode()
    assert padel_a.name in html and court_b.name not in html


def test_unknown_municipality_is_404(client, db):
    assert client.get("/c/non-existe/").status_code == 404


def test_booking_of_other_municipality_not_visible(client, padel_a, court_b, citizen, outsider):
    b = create_booking(court_b, next_slot(court_b), outsider, rules_version=court_b.current_rules())
    client.force_login(outsider)
    assert client.get(f"/c/concello-b/reservas/{b.pk}/").status_code == 200
    assert client.get(f"/c/concello-a/reservas/{b.pk}/").status_code == 404
    client.force_login(citizen)  # outra persoa do mesmo concello tampouco a ve
    assert client.get(f"/c/concello-b/reservas/{b.pk}/").status_code == 404


def test_admin_of_a_cannot_manage_b(client, admin_a, muni_b, court_b):
    client.force_login(admin_a)
    assert client.get("/c/concello-a/xestion/").status_code == 200
    assert client.get("/c/concello-b/xestion/").status_code == 403
    assert client.get(f"/c/concello-b/xestion/instalacions/{court_b.pk}/").status_code == 403
    assert client.get("/c/concello-b/xestion/indicadores/").status_code == 403


def test_admin_cannot_edit_facility_of_other_municipality_via_own_url(
    client, admin_a, court_b, muni_a
):
    client.force_login(admin_a)
    assert client.get(f"/c/concello-a/xestion/instalacions/{court_b.pk}/").status_code == 404


def test_incident_admin_isolation(client, admin_a, court_b, outsider):
    inc = Incident.objects.create(
        municipality=court_b.municipality, facility=court_b, reporter=outsider, description="x"
    )
    client.force_login(admin_a)
    assert client.get(f"/c/concello-a/xestion/incidencias/{inc.pk}/").status_code == 404
    assert (
        f"incidencias/{inc.pk}/"
        not in client.get("/c/concello-a/xestion/incidencias/").content.decode()
    )


def test_citizen_cannot_access_management(client, citizen, muni_a):
    client.force_login(citizen)
    for path in [
        "xestion/",
        "xestion/indicadores/",
        "xestion/persoal/",
        "operario/",
        "xestion/portabilidade/exportar.zip",
    ]:
        assert client.get(f"/c/concello-a/{path}").status_code == 403, path


def test_anonymous_redirected_to_login(client, muni_a):
    r = client.get("/c/concello-a/xestion/")
    assert r.status_code == 302 and "/acceso/" in r["Location"]


def test_operator_sees_orders_but_not_admin(client, operator_a, muni_a):
    client.force_login(operator_a)
    assert client.get("/c/concello-a/operario/").status_code == 200
    assert client.get("/c/concello-a/xestion/").status_code == 403


def test_region_admin_manages_member_municipalities(client, region, muni_a, muni_b):
    from apps.accounts.models import RegionMembership, User

    dep = User.objects.create_user("dep@example.org")
    RegionMembership.objects.create(user=dep, region=region)
    client.force_login(dep)
    assert client.get("/rexion/proba/").status_code == 200
    assert client.get("/c/concello-a/xestion/").status_code == 200
    assert client.get("/c/concello-b/xestion/").status_code == 200


def test_region_admin_of_other_region_forbidden(client, muni_a):
    from apps.accounts.models import RegionMembership, User
    from apps.tenants.models import Region

    other = Region.objects.create(name="Outra", slug="outra")
    dep = User.objects.create_user("dep2@example.org")
    RegionMembership.objects.create(user=dep, region=other)
    client.force_login(dep)
    assert client.get("/rexion/proba/").status_code == 403
    assert client.get("/c/concello-a/xestion/").status_code == 403


def test_api_isolation(client, padel_a, court_b, outsider):
    r = client.get("/api/v1/municipalities/concello-a/facilities/")
    ids = [f["id"] for f in r.json()["results"]]
    assert padel_a.pk in ids and court_b.pk not in ids
    assert (
        client.get(f"/api/v1/municipalities/concello-a/facilities/{court_b.pk}/").status_code == 404
    )
    b = create_booking(court_b, next_slot(court_b), outsider, rules_version=court_b.current_rules())
    client.force_login(outsider)
    assert client.get(f"/api/v1/municipalities/concello-a/bookings/{b.pk}/").status_code == 404
    assert client.get(f"/api/v1/municipalities/concello-b/bookings/{b.pk}/").status_code == 200


def test_queryset_helper_filters(padel_a, court_b):
    from apps.facilities.models import Facility

    assert list(Facility.objects.for_tenant(padel_a.municipality)) == [padel_a]
    assert Booking.objects.for_tenant(court_b.municipality).count() == 0


def test_subdomain_resolution(client, padel_a, settings):
    settings.EIRA_BASE_DOMAIN = "eira.test"
    settings.ALLOWED_HOSTS = [".eira.test"]
    r = client.get("/", HTTP_HOST="concello-a.eira.test")
    assert r.status_code == 200 and padel_a.name in r.content.decode()
    r = client.get(f"/instalacions/{padel_a.pk}/", HTTP_HOST="concello-a.eira.test")
    assert r.status_code == 200


def test_custom_domain_resolution(client, padel_a, settings):
    muni = padel_a.municipality
    muni.domain = "deportes.concello-a.test"
    muni.save()
    settings.ALLOWED_HOSTS = ["deportes.concello-a.test"]
    r = client.get("/", HTTP_HOST="deportes.concello-a.test")
    assert padel_a.name in r.content.decode()


def test_module_flag_hides_activities(client, muni_a):
    muni_a.modules = {**muni_a.modules, "activities": False}
    muni_a.save()
    assert client.get("/c/concello-a/actividades/").status_code == 404
