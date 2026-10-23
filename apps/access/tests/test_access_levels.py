# SPDX-License-Identifier: EUPL-1.2
import datetime as dt

import pytest
from django.utils import timezone

from apps.access import services
from apps.access.models import AccessEvent, KeyHandover, LockDevice
from apps.bookings.models import Booking
from apps.bookings.services import create_booking
from apps.integrations.models import DevMail, OutboundMessage
from conftest import next_slot

pytestmark = pytest.mark.django_db


def booking_now(facility, user):
    """Reserva que inclúe o instante actual (creada directamente, sen validar o pasado)."""
    step = dt.timedelta(minutes=facility.slot_minutes)
    now = timezone.now().replace(second=0, microsecond=0)
    start = (
        now.replace(minute=0)
        if facility.slot_minutes == 60
        else now.replace(minute=(now.minute // 30) * 30)
    )
    return Booking.objects.create(
        municipality=facility.municipality,
        facility=facility,
        user=user,
        start=start,
        end=start + step,
        status=Booking.Status.CONFIRMED,
        rules_version=facility.current_rules(),
        rules_accepted_at=now,
    )


def test_level2_device_validates_and_checks_in(gym_a, citizen):
    b = booking_now(gym_a, citizen)
    device = gym_a.lock
    code = device.code_for_booking(b)
    result = services.validate_code(device, code, at=b.start + dt.timedelta(minutes=5))
    assert result["ok"] and result["booking"] == b
    b.refresh_from_db()
    assert b.status == Booking.Status.USED and b.checked_in_at
    assert AccessEvent.objects.filter(kind="code_ok", booking=b).exists()


def test_level2_lockout_after_five_failures(gym_a):
    device = gym_a.lock
    at = timezone.now()
    for _ in range(LockDevice.MAX_FAILED):
        assert not services.validate_code(device, "000000", at=at)["ok"]
    device.refresh_from_db()
    assert device.locked_until and device.locked_until > at
    assert services.validate_code(device, "000000", at=at)["reason"] == "locked"
    later = at + dt.timedelta(minutes=LockDevice.LOCKOUT_MINUTES, seconds=1)
    assert services.validate_code(device, "000000", at=later)["reason"] == "invalid"


def test_level2_access_info_shows_code_and_window(gym_a, citizen):
    b = create_booking(gym_a, next_slot(gym_a), citizen, rules_version=gym_a.current_rules())
    b.status = Booking.Status.CONFIRMED
    info = services.booking_access_info(b)
    assert info["code"] and len(info["code"]) == 6
    assert info["valid_from"] == b.start - dt.timedelta(minutes=10)


def test_level3_open_only_within_window(pool_a, citizen):
    future = create_booking(
        pool_a, next_slot(pool_a, hour=10), citizen, rules_version=pool_a.current_rules()
    )
    future.status = Booking.Status.CONFIRMED
    future.save()
    assert not services.booking_access_info(future)["can_open"]
    assert services.remote_open(future, citizen) is False
    current = booking_now(pool_a, citizen)
    assert services.remote_open(current, citizen) is True
    current.refresh_from_db()
    assert current.status == Booking.Status.USED
    assert OutboundMessage.objects.filter(channel="mqtt", payload__cmd="open").exists()
    pool_a.lock.refresh_from_db()
    assert pool_a.lock.lights_on_until == current.end  # luces só ata o fin da franxa


def test_level0_qr_checkin_with_and_without_booking(court_b, outsider):
    assert services.qr_checkin(court_b, None) is None
    assert AccessEvent.objects.filter(kind="anonymous_use", facility=court_b).count() == 1
    b = booking_now(court_b, outsider)
    assert services.qr_checkin(court_b, outsider) == b
    b.refresh_from_db()
    assert b.checked_in_at is not None


def test_level1_custodian_notified_and_handover(hall_a, citizen, admin_a):
    b = create_booking(hall_a, next_slot(hall_a), citizen, rules_version=hall_a.current_rules())
    from apps.bookings.services import mark_paid

    mark_paid(b, "REF", b.price_cents)
    handover = KeyHandover.objects.get(booking=b)
    assert handover.custodian_notified_at
    assert DevMail.objects.filter(to="custodia@example.org").exists()
    services.key_out(b, admin_a)
    services.key_in(b, admin_a)
    handover.refresh_from_db()
    assert handover.handed_at and handover.returned_at


def test_checkin_view(client, court_b):
    url = f"/c/{court_b.municipality.slug}/acceso/entrada/{court_b.checkin_token}/"
    assert client.get(url).status_code == 200
    assert client.post(url).status_code == 200
    assert (
        client.get(f"/c/{court_b.municipality.slug}/acceso/entrada/token-falso/").status_code == 404
    )


def test_lock_simulator_page(client, gym_a, citizen):
    b = booking_now(gym_a, citizen)
    code = gym_a.lock.code_for_booking(b)
    at = timezone.localtime(b.start + dt.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M")
    r = client.post("/dev/lock-simulator/", {"device": gym_a.lock.pk, "at": at, "code": code})
    assert "ABERTO" in r.content.decode()
    late = timezone.localtime(b.end + dt.timedelta(minutes=11)).strftime("%Y-%m-%dT%H:%M")
    r = client.post("/dev/lock-simulator/", {"device": gym_a.lock.pk, "at": late, "code": code})
    assert "DENEGADO" in r.content.decode()


def test_exponential_lockout_and_alert(gym_a, admin_a):
    from apps.notifications.models import Notification

    device = gym_a.lock
    at = timezone.now()
    durations = []
    for _round in range(LockDevice.ALERT_AFTER_LOCKOUTS):
        for _ in range(LockDevice.MAX_FAILED):
            services.validate_code(device, "000000", at=at)
        device.refresh_from_db()
        durations.append(round((device.locked_until - at).total_seconds() / 60))
        at = device.locked_until + dt.timedelta(seconds=1)
    assert durations == [5, 10, 20]
    assert Notification.objects.filter(user=admin_a, title__contains="forzar").exists()


def test_simulator_lockout_uses_real_time_not_simulated_clock(client, gym_a, citizen):
    """v3: bloquear o teclado cunha hora simulada futura non pode deixalo bloqueado horas reais."""
    b = booking_now(gym_a, citizen)
    future = timezone.localtime(timezone.now() + dt.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    for _ in range(LockDevice.MAX_FAILED):
        client.post("/dev/lock-simulator/", {"device": gym_a.lock.pk, "at": future, "code": "000000"})
    gym_a.lock.refresh_from_db()
    assert gym_a.lock.locked_until <= timezone.now() + dt.timedelta(minutes=LockDevice.LOCKOUT_MINUTES, seconds=5)
    # Restablecer (só demo) desbloquea e a reserva abre á súa hora
    client.post("/dev/lock-simulator/", {"device": gym_a.lock.pk, "action": "reset"})
    at = timezone.localtime(b.start + dt.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M")
    r = client.post(
        "/dev/lock-simulator/", {"device": gym_a.lock.pk, "at": at, "code": gym_a.lock.code_for_booking(b)}
    )
    assert "ABERTO" in r.content.decode()


def test_simulator_preselects_device_of_my_next_booking(client, gym_a, citizen, padel_a):
    b = booking_now(gym_a, citizen)
    client.force_login(citizen)
    html = client.get("/dev/lock-simulator/").content.decode()
    assert f'<option value="{gym_a.lock.pk}" selected' in html
    # reserva en curso: o reloxo da pechadura ponse na hora actual (dentro da franxa)
    expected = max(b.start, timezone.now().replace(second=0, microsecond=0))
    assert f'value="{timezone.localtime(expected).strftime("%Y-%m-%dT%H:%M")}"' in html
