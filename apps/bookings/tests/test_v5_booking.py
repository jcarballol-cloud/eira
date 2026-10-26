# SPDX-License-Identifier: EUPL-1.2
"""v5 · C: participantes, formas de pagamento, aprobación do concello e suplemento de luz."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.access.models import LockDevice
from apps.access.services import remote_open
from apps.bookings import payments, services
from apps.bookings.lighting import slot_needs_light, sun_times
from apps.bookings.models import Booking, Payment, Voucher, VoucherType
from apps.integrations.models import FakePayment
from apps.integrations.registry import get_adapter
from apps.notifications.models import Notification
from conftest import next_slot

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


def slot_at(facility, hour, days=2):
    for extra in range(7):
        day = timezone.localdate() + dt.timedelta(days=days + extra)
        for s in services.slot_starts(facility, day):
            if timezone.localtime(s).hour == hour:
                return s
    raise AssertionError(f"sen franxa ás {hour}")


def pay_ok(booking):
    """Simula a notificación asinada da pasarela para o último pagamento pendente."""
    payment = booking.payments.filter(status=Payment.Status.PENDING).latest("created_at")
    fake = FakePayment.objects.get(reference=payment.reference)
    payments.handle_notification(get_adapter("payment").build_notification(fake, ok=True))
    booking.refresh_from_db()
    return payment


def start_tpv(booking):
    payments.start_online_payment(booking=booking, url_ok="/ok", url_ko="/ko")


@pytest.fixture
def lit_padel(padel_a, muni_a):
    muni_a.lighting_rule = "fixed"
    muni_a.lighting_from = dt.time(20, 0)
    muni_a.lighting_until = dt.time(8, 0)
    muni_a.save()
    padel_a.lighting = True
    padel_a.lighting_supplement_cents = 150
    padel_a.save()
    return padel_a


# ------------------------------------------------------------------ participantes


def test_participants_required_and_limited(padel_a, citizen):
    padel_a.max_participants = 4
    padel_a.save()
    rules = padel_a.current_rules()
    with pytest.raises(services.BookingError):
        services.create_booking(
            padel_a, next_slot(padel_a), citizen, rules_version=rules, participants=5
        )
    b = services.create_booking(
        padel_a,
        next_slot(padel_a),
        citizen,
        rules_version=rules,
        participants=4,
        participant_names="Ana\nBieito\n\n",
    )
    assert b.participants == 4 and b.participant_name_list() == ["Ana", "Bieito"]


def test_participants_over_max_rejected_in_view(client, padel_a, citizen):
    padel_a.max_participants = 4
    padel_a.save()
    client.force_login(citizen)
    start = next_slot(padel_a)
    r = client.post(
        f"{C}/instalacions/{padel_a.pk}/reservar/",
        {"inicio": start.isoformat(), "accept_rules": "on", "participants": "9"},
    )
    assert r.status_code == 200 and not Booking.objects.filter(user=citizen).exists()


# ------------------------------------------------------------------ luz


def test_sunset_is_later_in_summer_than_in_winter():
    _r1, summer = sun_times(dt.date(2026, 6, 21), 42.8, -8.5)
    _r2, winter = sun_times(dt.date(2026, 12, 21), 42.8, -8.5)
    assert summer.hour >= 21 and 17 <= winter.hour <= 18


def test_lighting_supplement_fixed_schedule_and_on_request(lit_padel, citizen):
    night = slot_at(lit_padel, 21)
    day = slot_at(lit_padel, 10)
    assert slot_needs_light(lit_padel, night, night + dt.timedelta(minutes=90))
    assert not slot_needs_light(lit_padel, day, day + dt.timedelta(minutes=90))
    q_night = services.quote(lit_padel, citizen, night)
    q_day = services.quote(lit_padel, citizen, day)
    q_day_light = services.quote(lit_padel, citizen, day, needs_light=True)
    assert q_night.lighting_cents == 150 and q_night.lighting_auto
    assert q_night.total_cents == q_night.slot_cents + 150
    assert q_day.lighting_cents == 0
    assert q_day_light.lighting_cents == 150 and not q_day_light.lighting_auto


def test_breakdown_shown_before_paying_and_in_receipt(client, lit_padel, citizen):
    client.force_login(citizen)
    night = slot_at(lit_padel, 21)
    url = f"{C}/instalacions/{lit_padel.pk}/reservar/?inicio={night.isoformat()}"
    html = client.get(url.replace("+", "%2B")).content.decode()
    assert "luz 1,50 €" in html and "Total" in html
    r = client.post(
        f"{C}/instalacions/{lit_padel.pk}/reservar/",
        {"inicio": night.isoformat(), "accept_rules": "on", "participants": "2"},
    )
    assert "/dev/tpv/" in r["Location"]
    booking = Booking.objects.get(user=citizen)
    assert booking.lighting_cents == 150 and booking.price_cents == booking.slot_cents + 150
    assert FakePayment.objects.get().amount_cents == booking.price_cents
    pay_ok(booking)
    receipt = client.get(f"{C}/reservas/{booking.pk}/recibo/").content.decode()
    assert "luz 1,50 €" in receipt
    pdf = client.get(f"{C}/reservas/{booking.pk}/recibo/?formato=pdf").content
    assert b"luz" in pdf


def test_level3_lights_only_with_supplement(pool_a, citizen):
    pool_a.lighting = True
    pool_a.lighting_supplement_cents = 200
    pool_a.save()
    LockDevice.objects.filter(facility=pool_a).update(controls_lights=True)
    now = timezone.now()
    b = Booking.objects.create(
        municipality=pool_a.municipality,
        facility=pool_a,
        user=citizen,
        start=now - dt.timedelta(minutes=5),
        end=now + dt.timedelta(minutes=55),
        status=Booking.Status.CONFIRMED,
        rules_version=pool_a.current_rules(),
    )
    assert remote_open(b, citizen)
    pool_a.lock.refresh_from_db()
    assert not pool_a.lock.lights_on()  # sen suplemento, as luces non se acenden
    b.needs_light, b.lighting_cents = True, 200
    b.save()
    assert remote_open(b, citizen)
    pool_a.lock.refresh_from_db()
    assert pool_a.lock.lights_on()


# ------------------------------------------------------------------ formas de pagamento


def test_default_methods_are_tpv_only_and_deferred_off(padel_a, muni_a):
    assert padel_a.payment_method_list() == ["tpv"]
    padel_a.payment_methods = ["tpv", "deferred"]
    padel_a.save()
    assert "deferred" not in padel_a.payment_method_list()  # o concello non o activou
    muni_a.payment_methods = ["tpv", "deferred"]
    muni_a.save()
    padel_a.refresh_from_db()
    assert "deferred" in padel_a.payment_method_list()


def test_method_not_allowed_is_rejected(padel_a, citizen):
    with pytest.raises(services.BookingError):
        services.create_booking(
            padel_a,
            next_slot(padel_a),
            citizen,
            rules_version=padel_a.current_rules(),
            payment_method="office",
        )


def test_office_payment_holds_until_deadline_then_expires(
    padel_a, muni_a, citizen, admin_a, client
):
    muni_a.payment_methods = ["tpv", "office"]
    muni_a.office_payment_hours = 24
    muni_a.save()
    start = next_slot(padel_a, days=4)
    b = services.create_booking(
        padel_a, start, citizen, rules_version=padel_a.current_rules(), payment_method="office"
    )
    assert b.status == Booking.Status.PENDING_OFFICE and b.paid_cents == 0
    assert abs((b.hold_expires_at - timezone.now()) - dt.timedelta(hours=24)) < dt.timedelta(
        minutes=1
    )
    assert Booking.objects.filter(pk=b.pk).holding().exists()  # a franxa queda gardada
    # Cobro no mostrador: confírmase
    client.force_login(admin_a)
    client.post(f"{C}/xestion/reservas/{b.pk}/", {"action": "counter_pay", "method": "cash"})
    b.refresh_from_db()
    assert b.status == Booking.Status.CONFIRMED and b.paid_cents == b.price_cents
    # Outra sen pagar caduca ao pasar o prazo
    b2 = services.create_booking(
        padel_a,
        next_slot(padel_a, days=5),
        citizen,
        rules_version=padel_a.current_rules(),
        payment_method="office",
    )
    payments.expire_pending(now=timezone.now() + dt.timedelta(hours=25))
    b2.refresh_from_db()
    assert b2.status == Booking.Status.EXPIRED


def test_free_method_and_deferred(padel_a, muni_a, citizen):
    muni_a.payment_methods = ["tpv", "free", "deferred"]
    muni_a.save()
    free = services.create_booking(
        padel_a,
        next_slot(padel_a),
        citizen,
        rules_version=padel_a.current_rules(),
        payment_method="free",
    )
    assert free.status == Booking.Status.CONFIRMED and free.price_cents == 0
    deferred = services.create_booking(
        padel_a,
        next_slot(padel_a, days=3),
        citizen,
        rules_version=padel_a.current_rules(),
        payment_method="deferred",
    )
    assert (
        deferred.status == Booking.Status.CONFIRMED
        and deferred.outstanding_cents == deferred.price_cents > 0
    )


def test_voucher_bought_online_used_and_returned_on_time(client, padel_a, muni_a, citizen):
    muni_a.payment_methods = ["tpv", "voucher"]
    muni_a.save()
    vt = VoucherType.objects.create(
        municipality=muni_a, name="Bono 5 pádel", facility=padel_a, uses=5, price_cents=1500
    )
    client.force_login(citizen)
    r = client.post(f"{C}/reservas/bonos/", {"type": vt.pk})
    assert "/dev/tpv/" in r["Location"]
    v = Voucher.objects.get(user=citizen)
    assert v.status == Voucher.Status.PENDING
    fake = FakePayment.objects.get()
    payments.handle_notification(get_adapter("payment").build_notification(fake, ok=True))
    v.refresh_from_db()
    assert v.status == Voucher.Status.ACTIVE and v.expires_at
    assert Payment.objects.get(voucher=v).municipality == muni_a
    b = services.create_booking(
        padel_a,
        next_slot(padel_a, days=5),
        citizen,
        rules_version=padel_a.current_rules(),
        payment_method="voucher",
        voucher=v,
    )
    v.refresh_from_db()
    assert b.status == Booking.Status.CONFIRMED and b.price_cents == 0 and v.uses_left == 4
    services.cancel_booking(b, by=citizen)
    v.refresh_from_db()
    assert v.uses_left == 5


def test_voucher_for_other_facility_not_usable(padel_a, gym_a, muni_a, citizen):
    muni_a.payment_methods = ["tpv", "voucher"]
    muni_a.save()
    vt = VoucherType.objects.create(
        municipality=muni_a, name="Bono ximnasio", facility=gym_a, uses=3, price_cents=900
    )
    v = payments.sell_voucher(vt, citizen, method="cash")
    with pytest.raises(services.BookingError):
        services.create_booking(
            padel_a,
            next_slot(padel_a),
            citizen,
            rules_version=padel_a.current_rules(),
            payment_method="voucher",
            voucher=v,
        )


def test_reconciliation_shows_every_method(client, admin_a, padel_a, muni_a, citizen):
    muni_a.payment_methods = ["tpv", "office", "free", "voucher", "deferred"]
    muni_a.save()
    services.create_booking(
        padel_a,
        next_slot(padel_a),
        citizen,
        rules_version=padel_a.current_rules(),
        payment_method="office",
    )
    client.force_login(admin_a)
    html = client.get(f"{C}/xestion/cobros/").content.decode()
    for label in ("TPV en liña", "Pagamento na oficina", "Gratuíta", "Bono", "Aprazado"):
        assert label in html
    assert "Por forma de pagamento" in html


# ------------------------------------------------------------------ aprobación


@pytest.fixture
def approval_padel(padel_a):
    padel_a.booking_mode = "approval"
    padel_a.save()
    return padel_a


def test_paid_booking_waits_for_approval_and_manager_is_notified(approval_padel, citizen, admin_a):
    b = services.create_booking(
        approval_padel,
        next_slot(approval_padel),
        citizen,
        rules_version=approval_padel.current_rules(),
    )
    start_tpv(b)
    pay_ok(b)
    assert b.status == Booking.Status.PENDING_APPROVAL and b.paid_cents == b.price_cents
    assert Booking.objects.filter(pk=b.pk).holding().exists()
    assert Notification.objects.filter(
        user=admin_a, title__startswith="Reserva para aprobar"
    ).exists()
    services.approve_booking(b, admin_a)
    b.refresh_from_db()
    assert b.status == Booking.Status.CONFIRMED and b.approved_at
    assert Notification.objects.filter(
        user=citizen, title__startswith="Reserva confirmada"
    ).exists()


def test_declining_a_paid_booking_refunds_automatically(client, approval_padel, citizen, admin_a):
    b = services.create_booking(
        approval_padel,
        next_slot(approval_padel),
        citizen,
        rules_version=approval_padel.current_rules(),
    )
    start_tpv(b)
    payment = pay_ok(b)
    client.force_login(admin_a)
    r = client.post(f"{C}/xestion/reservas/{b.pk}/", {"action": "decline", "reason": ""})
    b.refresh_from_db()
    assert b.status == Booking.Status.PENDING_APPROVAL  # sen motivo non se rexeita
    client.post(
        f"{C}/xestion/reservas/{b.pk}/",
        {"action": "decline", "reason": "Pista reservada para un torneo"},
    )
    b.refresh_from_db()
    payment.refresh_from_db()
    assert r.status_code == 302
    assert b.status == Booking.Status.DECLINED and b.refunded_cents == b.paid_cents
    assert payment.status == Payment.Status.REFUNDED
    assert (
        FakePayment.objects.get(reference=payment.reference).refunded_cents == payment.amount_cents
    )
    n = Notification.objects.filter(user=citizen, title__startswith="Reserva non aprobada").get()
    assert "torneo" in n.body and "Devolvémosche" in n.body
    assert not Booking.objects.filter(pk=b.pk).holding().exists()


def test_change_on_approval_facility_waits_for_manager(approval_padel, citizen, admin_a):
    b = services.create_booking(
        approval_padel,
        next_slot(approval_padel, days=4),
        citizen,
        rules_version=approval_padel.current_rules(),
        payment_method="tpv",
    )
    start_tpv(b)
    pay_ok(b)
    services.approve_booking(b, admin_a)
    b.refresh_from_db()
    old = b.start
    new = next_slot(approval_padel, days=5)
    services.modify_booking(b, new, by=citizen)
    b.refresh_from_db()
    assert b.start == old and b.requested_start == new
    assert Notification.objects.filter(
        user=admin_a, title__startswith="Cambio para aprobar"
    ).exists()
    services.approve_booking(b, admin_a)
    b.refresh_from_db()
    assert b.start == new and b.requested_start is None


def test_direct_mode_is_default(padel_a, citizen):
    assert padel_a.booking_mode == "direct"
    b = services.create_booking(
        padel_a, next_slot(padel_a), citizen, rules_version=padel_a.current_rules()
    )
    start_tpv(b)
    pay_ok(b)
    assert b.status == Booking.Status.CONFIRMED


def test_town_with_vouchers_can_be_deleted(padel_a, muni_a, citizen):
    """A demo rexenérase borrando os concellos: os bonos non o poden impedir."""
    vt = VoucherType.objects.create(municipality=muni_a, name="Bono", uses=2, price_cents=500)
    payments.sell_voucher(vt, citizen, method="cash")
    muni_a.delete()
    assert not Voucher.objects.exists()
