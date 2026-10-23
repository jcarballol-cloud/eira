# SPDX-License-Identifier: EUPL-1.2
import csv
import datetime as dt
import io
import json

import pytest
from django.utils import timezone

from apps.analytics import indicators
from apps.analytics.recommend import expected_occupancy
from apps.bookings.models import Booking

pytestmark = pytest.mark.django_db


def past_booking(facility, user, days_ago, hour=19, status="used"):
    day = timezone.localdate() - dt.timedelta(days=days_ago)
    start = timezone.make_aware(dt.datetime.combine(day, dt.time(hour)))
    return Booking.objects.create(
        municipality=facility.municipality,
        facility=facility,
        user=user,
        start=start,
        end=start + dt.timedelta(minutes=facility.slot_minutes),
        status=status,
        paid_cents=400,
        price_cents=400,
        rules_version=facility.current_rules(),
    )


def test_occupancy_and_no_shows(padel_a, citizen):
    for d in range(1, 8):
        past_booking(padel_a, citizen, d, status="used" if d % 2 else "no_show")
    s = indicators.summary(padel_a.municipality, weeks=4)
    row = s["occupancy"][0]
    assert row["booked"] == 7 and row["no_shows"] == 3
    assert 0 < row["pct"] < 100
    assert s["no_show_pct"] == round(100 * 3 / 7)


def test_underused_detected(padel_a, gym_a, citizen):
    s = indicators.summary(padel_a.municipality, weeks=4)
    assert {r["facility"] for r in s["underused"]} == {padel_a.name, gym_a.name}


def test_dashboard_has_accessible_tables_and_csv(client, admin_a, padel_a, citizen):
    past_booking(padel_a, citizen, 2)
    client.force_login(admin_a)
    html = client.get("/c/concello-a/xestion/indicadores/").content.decode()
    assert "hbar-row" in html and "<table" in html and "Ver datos en táboa" in html
    r = client.get("/c/concello-a/xestion/indicadores/?csv=ocupacion")
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert rows[0][0] == "instalacion" and rows[1][0] == padel_a.name


def test_recommendation_prefers_low_demand_hours(padel_a, citizen):
    for d in range(1, 50):
        past_booking(padel_a, citizen, d, hour=19)
    expected = expected_occupancy(padel_a)
    assert expected[(0, 19)] > expected[(0, 10)]


def test_open_data_has_no_personal_data(client, padel_a, citizen):
    past_booking(padel_a, citizen, 3)
    body = client.get("/c/concello-a/datos-abertos/ocupacion.csv").content.decode()
    assert citizen.email not in body and "Veciña" not in body
    assert padel_a.name in body
    dcat = json.loads(client.get("/c/concello-a/datos-abertos/dcat.jsonld").content)
    assert (
        dcat["@type"] == "dcat:Dataset"
        and dcat["dcat:distribution"][0]["dcat:mediaType"] == "text/csv"
    )


def test_ai_summary_uses_only_aggregates(padel_a):
    from apps.integrations.ai import FakeAIAdapter

    agg = indicators.ai_aggregates(padel_a.municipality)
    assert "email" not in json.dumps(agg)
    assert "Resumo" in FakeAIAdapter().weekly_summary(agg)
    with pytest.raises(ValueError):
        FakeAIAdapter().weekly_summary({"email": "x@example.org"})


def test_bar_widths_use_css_classes(client, admin_a, padel_a, citizen):
    """As barras usan clases .w-N (CSP sen estilos en liña) e a maior ocupa o 100 %."""
    for d in range(1, 4):
        past_booking(padel_a, citizen, d)
    client.force_login(admin_a)
    html = client.get("/c/concello-a/xestion/indicadores/").content.decode()
    assert 'class="hbar-fill w-100"' in html
