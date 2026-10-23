# SPDX-License-Identifier: EUPL-1.2
"""v2 F7: «Que tal foi?» (Ben/Regular/Mal), integrado no checklist, incidencia con «Mal» e vista do concello."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.bookings.models import Booking, Rating
from apps.bookings.ratings import stats
from apps.incidents.models import Incident

pytestmark = pytest.mark.django_db


def past_booking(facility, user, hours_ago=1):
    start = timezone.now() - dt.timedelta(hours=hours_ago)
    return Booking.objects.create(
        municipality=facility.municipality,
        facility=facility,
        user=user,
        start=start,
        end=start + dt.timedelta(minutes=facility.slot_minutes),
        status=Booking.Status.CONFIRMED,
    )


def test_checklist_includes_rating_and_bad_creates_incident(client, citizen, padel_a):
    b = past_booking(padel_a, citizen)
    client.force_login(citizen)
    html = client.get(f"/c/concello-a/reservas/{b.pk}/peche/").content.decode()
    assert "Que tal foi?" in html and "Avisar ao concello" in html
    client.post(
        f"/c/concello-a/reservas/{b.pk}/peche/",
        {
            "door_ok": "1",
            "all_ok": "1",
            "v-score": "bad",
            "v-tags": ["lights_broken", "dirty"],
            "v-comment": "Dúas lámpadas non acendían",
            "v-make_incident": "on",
        },
    )
    r = Rating.objects.get(booking=b)
    assert r.score == "bad" and r.tags == ["lights_broken", "dirty"]
    inc = r.incident
    assert inc.category == Incident.Category.LIGHTING and "lámpadas" in inc.description
    b.refresh_from_db()
    assert b.closed_at  # o checklist tamén quedou gardado


def test_bad_without_incident_checkbox_creates_none(client, citizen, padel_a):
    b = past_booking(padel_a, citizen)
    client.force_login(citizen)
    client.post(f"/c/concello-a/reservas/{b.pk}/valorar/", {"v-score": "bad", "v-tags": ["dirty"]})
    assert Rating.objects.get(booking=b).incident is None
    assert not Incident.objects.exists()


def test_rating_is_optional_in_checklist_and_unique(client, citizen, padel_a):
    b = past_booking(padel_a, citizen)
    client.force_login(citizen)
    client.post(f"/c/concello-a/reservas/{b.pk}/peche/", {"door_ok": "1", "all_ok": "1"})
    assert not Rating.objects.exists()
    client.post(f"/c/concello-a/reservas/{b.pk}/valorar/", {"v-score": "good", "v-tags": ["clean"]})
    client.post(f"/c/concello-a/reservas/{b.pk}/valorar/", {"v-score": "bad"})
    assert Rating.objects.get(booking=b).score == "good"


def test_cannot_rate_future_or_others_bookings(client, citizen, outsider, padel_a):
    future = past_booking(padel_a, citizen, hours_ago=-48)
    client.force_login(citizen)
    client.post(f"/c/concello-a/reservas/{future.pk}/valorar/", {"v-score": "good"})
    assert not Rating.objects.exists()
    mine = past_booking(padel_a, citizen)
    client.force_login(outsider)
    r = client.post(f"/c/concello-a/reservas/{mine.pk}/valorar/", {"v-score": "bad"})
    assert r.status_code == 404 and not Rating.objects.exists()


def test_detail_invites_to_rate_after_use(client, citizen, court_b, padel_a):
    b = past_booking(padel_a, citizen, hours_ago=20)  # sen checklist pendente (pasaron 12 h)
    client.force_login(citizen)
    html = client.get(f"/c/concello-a/reservas/{b.pk}/").content.decode()
    assert f"/reservas/{b.pk}/valorar/" in html


def test_admin_ratings_view_hides_names_and_ranks(client, admin_a, citizen, padel_a, gym_a):
    for i in range(6):
        b = past_booking(padel_a, citizen, hours_ago=2 + i * 3)
        Rating.objects.create(
            municipality=padel_a.municipality,
            booking=b,
            facility=padel_a,
            score="good" if i else "bad",
            tags=["clean"],
            comment=f"Comentario {i}",
        )
    b = past_booking(gym_a, citizen, hours_ago=40)
    Rating.objects.create(municipality=gym_a.municipality, booking=b, facility=gym_a, score="good")
    s = stats(padel_a.municipality)
    assert s["rows"][0]["facility"] == padel_a and s["rows"][0]["enough"]
    assert s["rows"][0]["index"] == round(500 / 6)
    assert not s["rows"][1]["enough"]  # 1 valoración: fóra do ranking
    client.force_login(admin_a)
    html = client.get("/c/concello-a/xestion/valoracions/").content.decode()
    assert "Comentario 3" in html and "Limpa" in html
    assert citizen.email not in html and "Veciña" not in html
    csv = client.get("/c/concello-a/xestion/valoracions/?csv=1").content.decode()
    assert padel_a.name in csv and "Comentario" not in csv


def test_ratings_view_admin_only(client, citizen, operator_a, muni_a):
    for u in (citizen, operator_a):
        client.force_login(u)
        assert client.get("/c/concello-a/xestion/valoracions/").status_code == 403
