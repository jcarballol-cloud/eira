# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · E: enquisa anual con NPS (n ≥ 10, unha resposta por persoa) e NPS opcional tras o uso."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import Membership, Role, User
from apps.bookings.models import Booking, Rating
from apps.notifications.models import Notification
from apps.surveys import services
from apps.surveys.models import Survey, SurveyResponse, UseNps

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


@pytest.fixture
def survey(muni_a):
    today = timezone.localdate()
    return Survey.objects.create(
        municipality=muni_a,
        year=today.year,
        opens_on=today - dt.timedelta(days=3),
        closes_on=today + dt.timedelta(days=20),
    )


def _people(muni, n):
    out = []
    for i in range(n):
        u = User.objects.create_user(f"p{i}@example.org", birth_year=1980)
        Membership.objects.create(user=u, municipality=muni, role=Role.CITIZEN)
        out.append(u)
    return out


def _answers(survey, scores, **extra):
    start = SurveyResponse.objects.filter(survey=survey).count()
    for i, s in enumerate(scores, start=start):
        u = User.objects.create_user(f"r{survey.pk}-{i}@example.org")
        SurveyResponse.objects.create(survey=survey, user=u, nps=s, **extra)


def test_nps_formula():
    # 4 promotoras (9–10), 3 pasivas (7–8), 3 detractoras (0–6) → 40 − 30 = 10
    r = services.nps([10, 9, 9, 10, 7, 8, 8, 0, 6, 5])
    assert r == {"n": 10, "promoters": 40, "passives": 30, "detractors": 30, "nps": 10}
    assert services.nps([10] * 9) is None  # n < 10: sen cifra
    assert services.nps([0] * 10)["nps"] == -100
    assert services.nps([10] * 10)["nps"] == 100


def test_results_only_aggregated_with_ten(survey, padel_a):
    _answers(survey, [10] * 9, cleanliness=5)
    r = services.results(survey)
    assert not r["enough"] and r["nps"] is None and r["aspects"] == [] and r["comments"] == []
    _answers(survey, [3], cleanliness=1)
    r = services.results(survey)
    assert r["enough"] and r["nps"]["nps"] == 80
    clean = next(a for a in r["aspects"] if a["key"] == "cleanliness")
    assert clean["avg"] == 4.6  # (9×5 + 1) / 10
    price = next(a for a in r["aspects"] if a["key"] == "price")
    assert price["avg"] is None  # ninguén o valorou
    assert r["facilities"] == []  # ningunha instalación con n ≥ 10


def test_answer_once_and_only_in_window(client, citizen, survey, padel_a):
    client.force_login(citizen)
    assert "Do 0 ao 10" in client.get(f"{C}/enquisa/").content.decode()
    data = {"nps": "9", "cleanliness": "4", "price": "", "facility": padel_a.pk, "comment": "Ben"}
    r = client.post(f"{C}/enquisa/", data)
    assert r.status_code == 302
    resp = SurveyResponse.objects.get()
    assert resp.nps == 9 and resp.cleanliness == 4 and resp.price is None
    client.post(f"{C}/enquisa/", {**data, "nps": "2"})
    assert SurveyResponse.objects.count() == 1  # unha resposta por persoa
    assert "Xa respondiches" in client.get(f"{C}/enquisa/").content.decode()
    survey.closes_on = timezone.localdate() - dt.timedelta(days=1)
    survey.save()
    other = User.objects.create_user("outra@example.org")
    client.force_login(other)
    assert "non hai ningunha enquisa aberta" in client.get(f"{C}/enquisa/").content.decode()


def test_staff_cannot_answer(client, admin_a, survey):
    client.force_login(admin_a)
    assert client.get(f"{C}/enquisa/").status_code == 403


def test_announce_by_app_email_and_telegram(client, admin_a, survey, muni_a):
    people = _people(muni_a, 3)
    people[0].notify_telegram, people[0].telegram_chat = True, "123"
    people[0].save()
    client.force_login(admin_a)
    client.post(f"{C}/xestion/enquisas/{survey.pk}/avisar/")
    survey.refresh_from_db()
    assert survey.announced_at
    notes = Notification.objects.filter(title__startswith="Enquisa de satisfacción")
    assert notes.count() == 3
    assert {"app", "email", "telegram"} <= set(notes.get(user=people[0]).channels.split(","))
    assert not notes.filter(user=admin_a).exists()


def test_manage_pages_and_dashboard(client, admin_a, survey, muni_a):
    _answers(survey, [9, 10, 9, 10, 9, 8, 7, 3, 9, 10, 10])
    client.force_login(admin_a)
    html = client.get(f"{C}/xestion/enquisas/").content.decode()
    assert "Evolución do NPS por ano" in html
    html = client.get(f"{C}/xestion/enquisas/{survey.pk}/").content.decode()
    assert "NPS" in html and "Promotoras" in html
    html = client.get(f"{C}/xestion/").content.decode()
    assert "Satisfacción (NPS)" in html
    r = client.post(
        f"{C}/xestion/enquisas/",
        {"year": survey.year, "opens_on": survey.opens_on, "closes_on": survey.closes_on},
    )
    assert r.status_code == 200 and Survey.objects.count() == 1  # un por ano


def test_region_sees_only_aggregate_nps(client, survey, muni_a, region):
    from apps.accounts.models import RegionMembership

    _answers(survey, [10] * 10)
    dep = User.objects.create_user("dep@example.org")
    RegionMembership.objects.create(user=dep, region=region)
    client.force_login(dep)
    html = client.get(f"/rexion/{region.slug}/").content.decode()
    assert "Satisfacción anual (NPS)" in html and "+100" in html
    csv = client.get(f"/rexion/{region.slug}/?csv=1").content.decode()
    assert "nps_ultima_enquisa" in csv


def _used_booking(facility, user):
    start = timezone.now() - dt.timedelta(hours=2)
    return Booking.objects.create(
        municipality=facility.municipality,
        facility=facility,
        user=user,
        start=start,
        end=start + dt.timedelta(hours=1),
        status=Booking.Status.USED,
        checked_in_at=start,
    )


def test_use_nps_disabled_by_default(client, citizen, padel_a):
    b = _used_booking(padel_a, citizen)
    client.force_login(citizen)
    html = client.get(f"{C}/reservas/{b.pk}/valorar/").content.decode()
    assert "Que tal foi?" in html and "nps_uso" not in html
    client.post(f"{C}/reservas/{b.pk}/valorar/", {"v-score": "good", "nps_uso": "9"})
    assert Rating.objects.filter(booking=b).exists() and not UseNps.objects.exists()


def test_use_nps_when_enabled(client, citizen, padel_a, muni_a):
    muni_a.nps_after_use = True
    muni_a.save()
    b = _used_booking(padel_a, citizen)
    client.force_login(citizen)
    html = client.get(f"{C}/reservas/{b.pk}/valorar/").content.decode()
    assert "nps_uso" in html and "Que tal foi?" in html  # «Que tal foi?» mantense
    client.post(f"{C}/reservas/{b.pk}/valorar/", {"v-score": "ok", "nps_uso": "6"})
    assert UseNps.objects.get(booking=b).score == 6
    # Opcional: sen resposta non se garda nada
    b2 = _used_booking(padel_a, citizen)
    client.post(f"{C}/reservas/{b2.pk}/valorar/", {"v-score": "good"})
    assert not UseNps.objects.filter(booking=b2).exists()


def test_app_home_banner(client, citizen, survey):
    client.force_login(citizen)
    assert "Dinos que tal" in client.get(f"{C}/app/").content.decode()
    SurveyResponse.objects.create(survey=survey, user=citizen, nps=8)
    assert "Dinos que tal" not in client.get(f"{C}/app/").content.decode()
