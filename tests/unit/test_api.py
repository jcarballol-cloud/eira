# SPDX-License-Identifier: EUPL-1.2
import pytest

from apps.bookings.models import Booking
from conftest import next_slot

pytestmark = pytest.mark.django_db


def test_public_endpoints(client, padel_a):
    assert client.get("/api/v1/municipalities/").json()["results"][0]["slug"] == "concello-a"
    f = client.get(f"/api/v1/municipalities/concello-a/facilities/{padel_a.pk}/").json()
    assert f["rules_version"] == 1 and f["tariffs"]
    slots = client.get(
        f"/api/v1/municipalities/concello-a/facilities/{padel_a.pk}/availability/"
    ).json()
    assert slots and {"start", "end", "status"} <= set(slots[0])


def test_booking_via_api_requires_rules_acceptance(client, padel_a, citizen):
    url = "/api/v1/municipalities/concello-a/bookings/"
    payload = {
        "facility": padel_a.pk,
        "start": next_slot(padel_a).isoformat(),
        "accept_rules_version": 1,
    }
    assert client.post(url, payload, content_type="application/json").status_code == 403
    client.force_login(citizen)
    assert (
        client.post(
            url, {**payload, "accept_rules_version": 99}, content_type="application/json"
        ).status_code
        == 400
    )
    r = client.post(url, payload, content_type="application/json")
    assert r.status_code == 201 and r.json()["status"] == "pending_payment"
    assert client.post(url, payload, content_type="application/json").status_code == 409
    b = Booking.objects.get()
    r = client.post(f"{url}{b.pk}/cancel/", content_type="application/json")
    assert r.status_code == 200


def test_schema_is_openapi_31(client, db):
    r = client.get("/api/schema/")
    assert r.status_code == 200 and b"openapi: 3.1.0" in r.content
