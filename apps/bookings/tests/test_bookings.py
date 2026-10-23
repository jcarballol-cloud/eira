# SPDX-License-Identifier: EUPL-1.2
import datetime as dt
from urllib.parse import quote

import pytest
from django.utils import timezone

from apps.bookings import services
from apps.bookings.ics import calendar, google_calendar_url
from apps.bookings.models import Booking
from apps.facilities.models import Closure
from apps.incidents.models import Incident
from apps.integrations.models import FakePayment
from apps.notifications.models import Notification
from conftest import next_slot

pytestmark = pytest.mark.django_db


def book(facility, user, start=None, **kw):
    return services.create_booking(
        facility, start or next_slot(facility), user, rules_version=facility.current_rules(), **kw
    )


def test_resident_and_non_resident_prices(padel_a, citizen, outsider):
    assert services.price_for(padel_a, citizen) == ("resident", 400)
    assert services.price_for(padel_a, outsider) == ("non_resident", 800)


def test_youth_and_senior_tariffs(pool_a, citizen):
    citizen.birth_year = timezone.localdate().year - 20
    assert services.audience_for(pool_a, citizen) == "youth"
    citizen.birth_year = timezone.localdate().year - 70
    assert services.audience_for(pool_a, citizen) == "senior"


def test_paid_booking_is_pending_until_payment(padel_a, citizen):
    b = book(padel_a, citizen)
    assert b.status == Booking.Status.PENDING_PAYMENT and b.hold_expires_at
    assert b.rules_version == padel_a.current_rules() and b.rules_accepted_at
    services.mark_paid(b, "REF1", b.price_cents)
    assert b.status == Booking.Status.CONFIRMED
    assert Notification.objects.filter(user=citizen, title__contains=padel_a.name).exists()


def test_free_booking_confirmed_immediately(court_b, outsider):
    from apps.facilities.models import Tariff

    Tariff.objects.filter(facility=court_b).update(price_cents=0)
    assert book(court_b, outsider).status == Booking.Status.CONFIRMED


def test_exclusive_slot_cannot_be_double_booked(padel_a, citizen, outsider):
    start = next_slot(padel_a)
    book(padel_a, citizen, start)
    with pytest.raises(services.BookingError):
        book(padel_a, outsider, start)


def test_expired_hold_frees_the_slot(padel_a, citizen, outsider):
    start = next_slot(padel_a)
    b = book(padel_a, citizen, start)
    Booking.objects.filter(pk=b.pk).update(hold_expires_at=timezone.now() - dt.timedelta(minutes=1))
    assert book(padel_a, outsider, start)
    assert services.expire_holds() == 1


def test_shared_capacity(gym_a, citizen, outsider):
    start = next_slot(gym_a, hour=10)
    gym_a.capacity = 2
    gym_a.save()
    book(gym_a, citizen, start)
    book(gym_a, outsider, start)
    from apps.accounts.models import User

    third = User.objects.create_user("terceira@example.org")
    with pytest.raises(services.BookingError):
        book(gym_a, third, start)


@pytest.mark.parametrize("delta", [dt.timedelta(minutes=15), dt.timedelta(hours=-72)])
def test_invalid_starts(padel_a, citizen, delta):
    with pytest.raises(services.BookingError):
        book(padel_a, citizen, next_slot(padel_a) + delta)


def test_too_far_in_advance(padel_a, citizen):
    padel_a.municipality.max_advance_days = 3
    padel_a.municipality.save()
    with pytest.raises(services.BookingError):
        book(padel_a, citizen, next_slot(padel_a, days=10))


def test_requires_current_rules(padel_a, court_b, citizen):
    with pytest.raises(services.BookingError):
        services.create_booking(
            padel_a, next_slot(padel_a), citizen, rules_version=court_b.current_rules()
        )


def test_max_active_bookings(padel_a, citizen):
    padel_a.municipality.max_active_bookings = 1
    padel_a.municipality.save()
    book(padel_a, citizen, next_slot(padel_a, hour=19))
    with pytest.raises(services.BookingError):
        book(padel_a, citizen, next_slot(padel_a, hour=21))


def test_closure_blocks_and_cancels_affected(padel_a, citizen):
    start = next_slot(padel_a)
    b = book(padel_a, citizen, start)
    services.mark_paid(b, "FR1", b.price_cents)
    closure = Closure.objects.create(
        municipality=padel_a.municipality,
        facility=padel_a,
        reason="Obras",
        starts_at=start - dt.timedelta(hours=1),
        ends_at=start + dt.timedelta(hours=3),
    )
    affected = services.apply_closure(closure)
    b.refresh_from_db()
    assert (
        affected == [b]
        and b.status == Booking.Status.CANCELLED
        and b.refunded_cents == b.paid_cents
    )
    assert Notification.objects.filter(user=citizen, level="warning").exists()
    with pytest.raises(services.BookingError):
        book(padel_a, citizen, start)


def test_municipality_wide_closure(padel_a, gym_a, citizen):
    start = next_slot(gym_a, hour=10)
    Closure.objects.create(
        municipality=padel_a.municipality,
        reason="Festivo",
        starts_at=start - dt.timedelta(hours=1),
        ends_at=start + dt.timedelta(hours=2),
    )
    with pytest.raises(services.BookingError):
        book(gym_a, citizen, start)


def test_cancellation_free_before_cutoff(padel_a, citizen):
    b = book(padel_a, citizen, next_slot(padel_a, days=5))
    services.mark_paid(b, "FR2", b.price_cents)
    refund, penalty = services.cancel_booking(b, by=citizen)
    assert (refund, penalty) == (400, 0)


def test_late_cancellation_penalty(padel_a, citizen):
    b = book(padel_a, citizen, next_slot(padel_a, days=2))
    services.mark_paid(b, "FR3", b.price_cents)
    padel_a.municipality.cancellation_hours = 24 * 10
    padel_a.municipality.save()
    b.refresh_from_db()
    refund, penalty = services.cancel_booking(b, by=citizen)
    assert penalty == 200 and refund == 200


def test_modify_booking(padel_a, citizen):
    b = book(padel_a, citizen, next_slot(padel_a, days=5, hour=19))
    services.mark_paid(b, "FR4", b.price_cents)
    new = next_slot(padel_a, days=5, hour=21)
    services.modify_booking(b, new, by=citizen)
    b.refresh_from_db()
    assert b.start == new


def test_modify_after_cutoff_rejected(padel_a, citizen):
    b = book(padel_a, citizen, next_slot(padel_a, days=2))
    services.mark_paid(b, "FR5", b.price_cents)
    padel_a.municipality.cancellation_hours = 24 * 10
    padel_a.municipality.save()
    b.refresh_from_db()
    with pytest.raises(services.BookingError):
        services.modify_booking(b, next_slot(padel_a, days=3), by=citizen)


def test_closing_checklist_creates_incident_on_no(padel_a, citizen):
    b = book(padel_a, citizen)
    assert services.submit_closing_checklist(b, True, None, True) is None
    b.closed_at = None
    inc = services.submit_closing_checklist(b, False, None, True, "Non pecha a fechadura")
    assert inc.source == Incident.Source.CHECKLIST and inc.facility == padel_a
    assert "porta" in inc.description


def test_no_shows(padel_a, citizen):
    b = book(padel_a, citizen)
    services.mark_paid(b, "FR6", b.price_cents)
    Booking.objects.filter(pk=b.pk).update(
        start=timezone.now() - dt.timedelta(hours=3), end=timezone.now() - dt.timedelta(hours=2)
    )
    assert services.mark_no_shows() == 1


def test_week_grid_statuses(padel_a, citizen, outsider):
    start = next_slot(padel_a, days=1)
    b = book(padel_a, citizen, start)
    services.mark_paid(b, "FR7", b.price_cents)
    monday = timezone.localdate(start) - dt.timedelta(days=timezone.localdate(start).weekday())
    grid = services.week_grid(padel_a, monday, user=citizen)
    slots = [s for _d, day in grid["by_day"] for s in day]
    assert any(s.start == start and s.status == "mine" for s in slots)
    grid = services.week_grid(padel_a, monday, user=outsider)
    slots = [s for _d, day in grid["by_day"] for s in day]
    assert any(s.start == start and s.status == "busy" for s in slots)
    assert sum(s.status == "recommended" for s in slots) <= 2 * 7


def test_ics_export_rfc5545(padel_a, citizen):
    b = book(padel_a, citizen)
    body = calendar([b], name="Proba")
    assert body.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0") and body.endswith("END:VCALENDAR\r\n")
    assert f"UID:{b.reference}@concello-a.eira" in body
    assert all(len(line.encode()) <= 75 for line in body.split("\r\n"))
    assert "calendar.google.com" in google_calendar_url(b)


def test_full_booking_flow_through_views(client, padel_a, citizen):
    client.force_login(citizen)
    start = next_slot(padel_a)
    url = f"/c/concello-a/instalacions/{padel_a.pk}/reservar/?inicio={quote(start.isoformat())}"
    r = client.get(url)
    assert r.status_code == 200 and "Normas de uso" in r.content.decode()
    r = client.post(url, {"inicio": start.isoformat()})  # sen aceptar normas
    assert "aceptar as normas" in r.content.decode()
    r = client.post(url, {"inicio": start.isoformat(), "accept_rules": "on"})
    assert r.status_code == 302 and "/dev/tpv/" in r["Location"]
    ref = r["Location"].rstrip("/").split("/")[-1]
    r = client.post(r["Location"], {"result": "ok"})
    assert FakePayment.objects.get(reference=ref).status == "paid"
    r = client.get(r["Location"], follow=True)
    b = Booking.objects.get(user=citizen)
    assert b.status == Booking.Status.CONFIRMED and b.paid_cents == 400
    detail = client.get(f"/c/concello-a/reservas/{b.pk}/").content.decode()
    assert b.facility.lock.code_for_booking(b) in detail  # nivel 2: o código móstrase
    assert client.get(f"/c/concello-a/reservas/{b.pk}/reserva.ics")["Content-Type"].startswith(
        "text/calendar"
    )
    assert client.get(f"/c/concello-a/reservas/{b.pk}/recibo/").status_code == 200
    r = client.post(f"/c/concello-a/reservas/{b.pk}/cancelar/", {"reason": "Choiva"})
    b.refresh_from_db()
    assert b.status == Booking.Status.CANCELLED and b.refunded_cents == 400


def test_failed_payment_keeps_pending(client, padel_a, citizen):
    client.force_login(citizen)
    start = next_slot(padel_a)
    r = client.post(
        f"/c/concello-a/instalacions/{padel_a.pk}/reservar/",
        {"inicio": start.isoformat(), "accept_rules": "on"},
    )
    r = client.post(r["Location"], {"result": "ko"})
    client.get(r["Location"])
    assert Booking.objects.get(user=citizen).status == Booking.Status.PENDING_PAYMENT


def test_staff_booking_on_behalf(client, admin_a, padel_a):
    client.force_login(admin_a)
    start = next_slot(padel_a)
    r = client.post(
        "/c/concello-a/xestion/reservar/",
        {
            "instalacion": padel_a.pk,
            "inicio": start.isoformat(),
            "holder_name": "Veciño por teléfono",
            "holder_phone": "600000000",
            "channel": "phone",
            "paid_at_counter": "on",
            "rules_read": "on",
        },
    )
    assert r.status_code == 302
    b = Booking.objects.get(holder_name="Veciño por teléfono")
    assert b.channel == "phone" and b.status == Booking.Status.CONFIRMED and b.created_by == admin_a
    assert b.tariff_audience == "non_resident"


def test_closing_checklist_view(client, padel_a, citizen):
    b = book(padel_a, citizen)
    client.force_login(citizen)
    r = client.post(f"/c/concello-a/reservas/{b.pk}/peche/", {"door_ok": "0", "all_ok": "1"})
    assert r.status_code == 302
    assert Incident.objects.filter(booking=b, source="checklist").exists()
