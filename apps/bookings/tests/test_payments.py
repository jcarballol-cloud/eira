# SPDX-License-Identifier: EUPL-1.2
"""v2 fase 3: cobros cribles. Unha reserva só se confirma cun pagamento aceptado."""

import datetime as dt
import io
import zipfile

import pytest
from django.db.models import F
from django.utils import timezone

from apps.accounts.models import Eligibility
from apps.bookings import payments, services
from apps.bookings.models import Booking, Payment
from apps.facilities.models import Tariff
from apps.integrations.models import FakePayment
from apps.integrations.registry import get_adapter
from apps.notifications.models import Notification
from conftest import next_slot

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


def book_and_go_to_tpv(client, facility, user, start=None):
    client.force_login(user)
    start = start or next_slot(facility)
    r = client.post(
        f"{C}/instalacions/{facility.pk}/reservar/",
        {"inicio": start.isoformat(), "accept_rules": "on"},
    )
    assert r.status_code == 302 and "/dev/tpv/" in r["Location"], r
    return Booking.objects.filter(user=user).latest("created_at"), r["Location"]


def test_rejected_payment_never_confirms_and_releases_slot(client, padel_a, citizen, outsider):
    booking, tpv = book_and_go_to_tpv(client, padel_a, citizen)
    r = client.post(tpv, {"result": "ko"})
    assert "resultado=ko" in r["Location"]
    booking.refresh_from_db()
    assert booking.status == Booking.Status.REJECTED and booking.paid_cents == 0
    assert booking.payments.get().status == Payment.Status.REJECTED
    titles = list(Notification.objects.filter(user=citizen).values_list("title", flat=True))
    assert not any("confirmada" in t.lower() for t in titles)
    page = client.get(r["Location"]).content.decode()
    assert "non se completou" in page
    # a franxa queda libre para outra persoa
    assert services.create_booking(
        padel_a, booking.start, outsider, rules_version=padel_a.current_rules()
    )


def test_resolved_payment_cannot_be_flipped(client, padel_a, citizen):
    """O fallo detectado: tras un KO, volver atrás e premer «Pagar» confirmaba a reserva."""
    booking, tpv = book_and_go_to_tpv(client, padel_a, citizen)
    client.post(tpv, {"result": "ko"})
    r = client.post(tpv, {"result": "ok"})  # segundo intento sobre a mesma operación
    assert "xa está resolta" in r.content.decode()
    booking.refresh_from_db()
    assert booking.status == Booking.Status.REJECTED
    fake = FakePayment.objects.get(reference=booking.payment_reference)
    # unha notificación repetida e asinada co resultado contrario tampouco cambia nada
    payments.handle_notification(get_adapter("payment").build_notification(fake, True))
    booking.refresh_from_db()
    assert booking.status == Booking.Status.REJECTED


def test_accepted_payment_confirms_once(client, padel_a, citizen):
    booking, tpv = book_and_go_to_tpv(client, padel_a, citizen)
    r = client.post(tpv, {"result": "ok"})
    assert "resultado=ok" in r["Location"]
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED and booking.paid_cents == booking.price_cents
    p = booking.payments.get()
    assert p.status == Payment.Status.PAID and p.signature_ok
    assert (
        Notification.objects.filter(user=citizen, title__startswith="Reserva confirmada").count()
        == 1
    )
    assert "Reserva confirmada" in client.get(r["Location"]).content.decode()


def test_return_url_alone_confirms_nothing(client, padel_a, citizen):
    booking, _tpv = book_and_go_to_tpv(client, padel_a, citizen)
    client.get(f"{C}/reservas/{booking.pk}/pagamento/?resultado=ok")  # sen notificación
    booking.refresh_from_db()
    assert booking.status == Booking.Status.PENDING_PAYMENT


def test_notification_endpoint_checks_signature(client, padel_a, citizen):
    booking, tpv = book_and_go_to_tpv(client, padel_a, citizen)
    fake = FakePayment.objects.get(reference=booking.payment_reference)
    data = get_adapter("payment").build_notification(fake, True)
    forged = {**data, "Ds_Signature": "AAAA" + data["Ds_Signature"][4:]}
    assert client.post("/pagamentos/notificacion/", forged).status_code == 403
    booking.refresh_from_db()
    assert booking.status == Booking.Status.PENDING_PAYMENT
    assert client.post("/pagamentos/notificacion/", data).status_code == 200
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED


def test_amount_mismatch_is_rejected(client, padel_a, citizen):
    from apps.integrations.payments import encode_params, sign

    booking, _tpv = book_and_go_to_tpv(client, padel_a, citizen)
    b64 = encode_params(
        {"Ds_Order": booking.payment_reference, "Ds_Amount": "1", "Ds_Response": "0000"}
    )
    client.post(
        "/pagamentos/notificacion/", {"Ds_MerchantParameters": b64, "Ds_Signature": sign(b64)}
    )
    booking.refresh_from_db()
    assert booking.status == Booking.Status.REJECTED


def test_hold_expires_and_releases_slot(client, padel_a, citizen, outsider):
    booking, _tpv = book_and_go_to_tpv(client, padel_a, citizen)
    assert (booking.hold_expires_at - timezone.now()) <= dt.timedelta(minutes=10, seconds=5)
    Booking.objects.filter(pk=booking.pk).update(
        hold_expires_at=timezone.now() - dt.timedelta(seconds=1)
    )
    assert services.expire_holds() == 1
    booking.refresh_from_db()
    assert booking.status == Booking.Status.EXPIRED
    assert booking.payments.get().status == Payment.Status.EXPIRED
    assert services.create_booking(
        padel_a, booking.start, outsider, rules_version=padel_a.current_rules()
    )


def test_late_payment_after_expiry(client, padel_a, citizen, outsider):
    booking, _tpv = book_and_go_to_tpv(client, padel_a, citizen)
    fake = FakePayment.objects.get(reference=booking.payment_reference)
    Booking.objects.filter(pk=booking.pk).update(status=Booking.Status.EXPIRED)
    Payment.objects.filter(booking=booking).update(status=Payment.Status.PENDING)
    # caso 1: a franxa segue libre → confírmase
    payments.handle_notification(get_adapter("payment").build_notification(fake, True))
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED


def test_late_payment_with_slot_taken_is_refunded(client, padel_a, citizen, outsider):
    booking, _tpv = book_and_go_to_tpv(client, padel_a, citizen)
    fake = FakePayment.objects.get(reference=booking.payment_reference)
    Booking.objects.filter(pk=booking.pk).update(status=Booking.Status.EXPIRED)
    other = services.create_booking(
        padel_a, booking.start, outsider, rules_version=padel_a.current_rules()
    )
    services.mark_paid(other, "X", other.price_cents)
    payments.handle_notification(get_adapter("payment").build_notification(fake, True))
    booking.refresh_from_db()
    p = booking.payments.get()
    assert booking.status == Booking.Status.EXPIRED and p.status == Payment.Status.REFUNDED
    assert Notification.objects.filter(user=citizen, title__startswith="Pagamento devolto").exists()


def test_refund_on_cancel_within_window(client, padel_a, citizen):
    booking, tpv = book_and_go_to_tpv(client, padel_a, citizen, start=next_slot(padel_a, days=5))
    client.post(tpv, {"result": "ok"})
    client.post(f"{C}/reservas/{booking.pk}/cancelar/")
    booking.refresh_from_db()
    p = booking.payments.get()
    assert (
        booking.status == Booking.Status.CANCELLED and booking.refunded_cents == booking.paid_cents
    )
    assert p.status == Payment.Status.REFUNDED and p.refunded_cents == p.amount_cents


def test_counter_payment_visible_immediately_in_agenda_and_detail(client, padel_a, admin_a):
    client.force_login(admin_a)
    start = next_slot(padel_a)
    client.post(
        f"{C}/xestion/reservar/",
        {
            "instalacion": padel_a.pk,
            "inicio": start.isoformat(),
            "holder_name": "Veciña de mostrador",
            "channel": "counter",
            "payment": "pending",
            "rules_read": "on",
        },
    )
    booking = Booking.objects.get(holder_name="Veciña de mostrador")
    assert booking.status == Booking.Status.PENDING_PAYMENT
    agenda = f"{C}/xestion/axenda/?dia={timezone.localdate(start).isoformat()}"
    assert "Pendente de pago" in client.get(agenda).content.decode()
    client.post(
        f"{C}/xestion/reservas/{booking.pk}/", {"action": "counter_pay", "method": "card_terminal"}
    )
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED
    assert booking.payments.get().method == Payment.Method.CARD_TERMINAL
    assert "Pagada" in client.get(agenda).content.decode()
    assert "Pagada" in client.get(f"{C}/xestion/reservas/{booking.pk}/").content.decode()


def test_cheapest_applicable_tariff_and_reduced_collective(padel_a, citizen, admin_a):
    Tariff.objects.create(facility=padel_a, audience=Tariff.Audience.REDUCED, price_cents=100)
    assert services.price_for(padel_a, citizen).price == 400
    Eligibility.objects.create(
        user=citizen, municipality=padel_a.municipality, kind="unemployed", validated_by=admin_a
    )
    q = services.price_for(padel_a, citizen)
    assert (q.audience, q.price) == ("reduced", 100)


def test_low_demand_discount(padel_a, citizen, monkeypatch):
    start = next_slot(padel_a)
    monkeypatch.setattr(services, "low_demand_discount", lambda f, s: 20 if s == start else 0)
    q = services.price_for(padel_a, citizen, start=start)
    assert (q.base, q.discount, q.price) == (400, 20, 320)
    b = services.create_booking(padel_a, start, citizen, rules_version=padel_a.current_rules())
    assert b.price_cents == 320 and b.base_price_cents == 400 and b.discount_pct == 20


def test_recommended_slots_carry_discount(padel_a):
    from apps.bookings.services import day_slots

    padel_a.municipality.low_demand_discount_pct = 25
    padel_a.municipality.save()
    slots = [
        s
        for d in range(1, 4)
        for s in day_slots(padel_a, timezone.localdate() + dt.timedelta(days=d))
    ]
    assert all((s.discount_pct == 25) == (s.status == "recommended") for s in slots)


def test_receipt_pdf(client, padel_a, citizen):
    booking, tpv = book_and_go_to_tpv(client, padel_a, citizen)
    client.post(tpv, {"result": "ok"})
    r = client.get(f"{C}/reservas/{booking.pk}/recibo/?formato=pdf")
    assert r["Content-Type"] == "application/pdf" and r.content.startswith(b"%PDF-1.4")
    assert booking.reference.encode() in r.content


def test_payments_conciliation_export(client, padel_a, citizen, admin_a):
    booking, tpv = book_and_go_to_tpv(client, padel_a, citizen)
    client.post(tpv, {"result": "ok"})
    client.force_login(admin_a)
    html = client.get(f"{C}/xestion/cobros/").content.decode()
    assert booking.payment_reference in html
    csv_body = client.get(f"{C}/xestion/cobros/?exportar=csv").content.decode("utf-8-sig")
    assert booking.payment_reference in csv_body and "4.0" in csv_body
    ods = client.get(f"{C}/xestion/cobros/?exportar=ods")
    with zipfile.ZipFile(io.BytesIO(ods.content)) as zf:
        assert booking.payment_reference.encode() in zf.read("content.xml")
    assert (
        client.get(f"{C}/xestion/cobros/?estado=rejected")
        .content.decode()
        .count(booking.payment_reference)
        == 0
    )


def test_enrollment_rejected_payment_frees_place(client, muni_a, citizen):
    from apps.accounts.models import Consent, Dependent, Household
    from apps.activities.models import Activity, Enrollment, Group

    g = Group.objects.create(
        municipality=muni_a,
        activity=Activity.objects.create(municipality=muni_a, name="A"),
        name="G",
        places=1,
        fee_cents=1500,
        min_age=5,
        max_age=12,
        start_time=dt.time(17),
    )
    hh = Household.objects.create(responsible=citizen)
    d = Dependent.objects.create(
        household=hh, first_name="Noa", birth_year=timezone.localdate().year - 9
    )
    Consent.objects.create(dependent=d, kind="data", granted_by=citizen)
    client.force_login(citizen)
    r = client.post(f"{C}/actividades/grupo/{g.pk}/inscribirse/", {"participant": d.pk})
    client.post(r["Location"], {"result": "ko"})
    assert Enrollment.objects.get().status == Enrollment.Status.CANCELLED


def test_refund_labels_are_explicit(citizen, padel_a):
    """v3: «Devolto» só aparece cando hai devolución, e cunha etiqueta que se entende."""
    import datetime as dt

    from django.template.loader import render_to_string
    from django.utils import timezone

    start = timezone.now() + dt.timedelta(days=2)
    base = dict(
        municipality=padel_a.municipality,
        facility=padel_a,
        user=citizen,
        start=start,
        end=start + dt.timedelta(hours=1),
        price_cents=400,
        paid_cents=400,
    )
    cases = [
        (Booking(status="cancelled", refunded_cents=400, **base), "Cancelada · importe devolto"),
        (Booking(status="cancelled", refunded_cents=0, **base), "Cancelada · sen devolución"),
        (Booking(status="confirmed", refunded_cents=0, **base), "Pagada"),
    ]
    for b, expected in cases:
        html = render_to_string("includes/booking_status.html", {"b": b})
        assert expected in html and "Devolta" not in html


def test_demo_refunds_are_coherent(db):
    from django.core.management import call_command

    call_command("seed_demo", verbosity=0)
    total = Booking.objects.count()
    refunded = Booking.objects.filter(refunded_cents__gt=0)
    assert set(refunded.values_list("status", flat=True)) <= {"cancelled"}
    assert refunded.count() < total * 0.05
    assert not refunded.filter(cancel_reason="").exists()
    assert not Booking.objects.filter(refunded_cents__gt=F("paid_cents")).exists()
