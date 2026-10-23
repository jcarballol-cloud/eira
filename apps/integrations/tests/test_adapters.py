# SPDX-License-Identifier: EUPL-1.2
import datetime as dt

import pytest
from django.utils import timezone

from apps.integrations.registry import get_adapter
from apps.integrations.weather import Forecast, MeteoSixAdapter, advice


def test_fake_weather_is_plausible_and_deterministic():
    w = get_adapter("weather")
    at = timezone.make_aware(dt.datetime(2026, 7, 15, 15))
    f1 = w.forecast(42.5, -8.1, at)
    assert f1 == w.forecast(42.5, -8.1, at)
    assert (
        10 < f1.temperature_c < 35 and 0 <= f1.precipitation_prob <= 100 and 0 <= f1.uv_index <= 11
    )
    night = w.forecast(42.5, -8.1, timezone.make_aware(dt.datetime(2026, 1, 15, 23)))
    assert night.uv_index == 0


def test_advice_rules():
    hot = Forecast(30, 10, 10, 8, "clear")
    tips = " ".join(advice(hot))
    assert "auga" in tips and "UV" in tips
    assert "UV" not in " ".join(advice(hot, indoor=True))
    cold_rain = " ".join(advice(Forecast(5, 80, 40, 0, "rain")))
    assert "abrigo" in cold_rain and "chuvia" in cold_rain and "Vento" in cold_rain


def test_meteosix_skeleton_requires_key(settings):
    settings.EIRA_METEOSIX_API_KEY = ""
    with pytest.raises(RuntimeError):
        MeteoSixAdapter().forecast(42.5, -8.1, timezone.now())


@pytest.mark.django_db
def test_mail_adapter_writes_dev_mailbox():
    from apps.integrations.models import DevMail

    get_adapter("mail").send("x@example.org", "Asunto", "Corpo")
    assert DevMail.objects.get().subject == "Asunto"


@pytest.mark.django_db
def test_weather_alert_closes_outdoor_facilities(client, admin_a, padel_a, gym_a, citizen):
    from apps.bookings.models import Booking
    from apps.bookings.services import create_booking, slot_starts

    now = timezone.now()
    start = next(
        s
        for d in range(0, 2)
        for s in slot_starts(padel_a, timezone.localdate() + dt.timedelta(days=d))
        if s > now + dt.timedelta(minutes=5)
    )
    if start - now < dt.timedelta(hours=20):
        b = create_booking(padel_a, start, citizen, rules_version=padel_a.current_rules())
        client.force_login(admin_a)
        client.post("/c/concello-a/xestion/peches/alerta/", {"hours": 24})
        b.refresh_from_db()
        assert b.status == Booking.Status.CANCELLED
    client.force_login(admin_a)
    client.post("/c/concello-a/xestion/peches/alerta/", {"hours": 6})
    assert padel_a.closures.filter(kind="weather").exists()
    assert not gym_a.closures.exists()  # cuberta: non se pecha
