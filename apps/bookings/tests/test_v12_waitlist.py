# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · F: recordatorios con «Confirmo»/«Cancelo», «que tes que facer e cando» e o ciclo
completo da lista de espera (liberación, oferta por orde, caducidade, aceptación e devolución)."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import Membership, Residency, Role, User
from apps.bookings import waitlist
from apps.bookings.models import Booking, SlotRelease, WaitlistEntry
from apps.bookings.services import apply_closure, cancel_booking, create_booking
from apps.facilities.models import Closure
from apps.notifications.models import Notification
from conftest import next_slot

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


def _person(muni, email):
    u = User.objects.create_user(email, display_name=email.split("@")[0].title(), birth_year=1990)
    Membership.objects.create(user=u, municipality=muni, role=Role.CITIZEN)
    Residency.objects.create(user=u, municipality=muni, method=Residency.Method.COUNTER)
    return u


@pytest.fixture
def ana(muni_a):
    return _person(muni_a, "ana@example.org")


@pytest.fixture
def berto(muni_a):
    return _person(muni_a, "berto@example.org")


def _confirmed(facility, user, start, paid=True):
    b = create_booking(
        facility, start, user, rules_version=facility.current_rules(), payment_method="tpv"
    )
    if b.status == Booking.Status.PENDING_PAYMENT:
        from apps.bookings.services import mark_paid

        mark_paid(b, "TEST", b.price_cents)
    b.refresh_from_db()
    assert b.status == Booking.Status.CONFIRMED
    return b


# ---------------------------------------------------------------- recordatorios
def test_reminders_24h_and_2h_once(citizen, padel_a):
    start = next_slot(padel_a, days=2)
    b = _confirmed(padel_a, citizen, start)
    sent = waitlist.send_reminders(now=start - dt.timedelta(hours=30))
    assert sent == {"24h": 0, "2h": 0}
    assert waitlist.send_reminders(now=start - dt.timedelta(hours=23))["24h"] == 1
    assert waitlist.send_reminders(now=start - dt.timedelta(hours=22))["24h"] == 0
    assert waitlist.send_reminders(now=start - dt.timedelta(hours=1))["2h"] == 1
    notes = Notification.objects.filter(user=citizen, title__startswith="Vés a")
    assert notes.count() == 2
    assert "#confirmar" in notes.first().url
    b.refresh_from_db()
    assert b.reminder_24_at and b.reminder_2_at


def test_confirm_and_one_tap_cancel(client, citizen, padel_a):
    start = next_slot(padel_a, days=3)
    b = _confirmed(padel_a, citizen, start)
    client.force_login(citizen)
    # Máis de 24 h antes aínda non se confirma
    assert not waitlist.can_confirm(b)
    assert "Confirmo" not in client.get(f"{C}/reservas/{b.pk}/").content.decode()
    Booking.objects.filter(pk=b.pk).update(
        start=timezone.now() + dt.timedelta(hours=5), end=timezone.now() + dt.timedelta(hours=6)
    )
    html = client.get(f"{C}/reservas/{b.pk}/").content.decode()
    assert "Confirmo" in html and "Cancelo" in html and "Que tes que facer e cando" in html
    client.post(f"{C}/reservas/{b.pk}/confirmo/")
    b.refresh_from_db()
    assert b.attendance_confirmed_at is not None
    other = _confirmed(padel_a, citizen, next_slot(padel_a, days=4))
    Booking.objects.filter(pk=other.pk).update(
        start=timezone.now() + dt.timedelta(hours=26), end=timezone.now() + dt.timedelta(hours=27)
    )
    r = client.post(f"{C}/reservas/{other.pk}/cancelo/")  # un toque
    other.refresh_from_db()
    assert r.status_code == 302 and other.status == Booking.Status.CANCELLED


def test_todo_lists_steps_with_times(citizen, padel_a):
    b = _confirmed(padel_a, citizen, next_slot(padel_a, days=2))
    keys = [t["key"] for t in waitlist.todo_for(b)]
    assert keys == ["confirm", "cancel", "checkin", "close"]
    # Xa comezada: nin «confirma» nin «cancelación gratuíta»
    started = timezone.now() - dt.timedelta(minutes=5)
    Booking.objects.filter(pk=b.pk).update(start=started, end=started + dt.timedelta(hours=1))
    b.refresh_from_db()
    assert [t["key"] for t in waitlist.todo_for(b)] == ["checkin", "close"]


# ---------------------------------------------------------------- lista de espera
def test_join_only_busy_slots(client, citizen, ana, padel_a):
    start = next_slot(padel_a, days=2)
    with pytest.raises(waitlist.WaitlistError):
        waitlist.join(padel_a, start, ana)  # libre: resérvase directamente
    _confirmed(padel_a, citizen, start)
    with pytest.raises(waitlist.WaitlistError):
        waitlist.join(padel_a, start, citizen)  # xa é súa
    client.force_login(ana)
    # A semana da franxa: en fin de semana, dentro de 2 días xa é a grella da semana seguinte
    week = timezone.localtime(start).date().isoformat()
    html = client.get(f"{C}/instalacions/{padel_a.pk}/", {"semana": week}).content.decode()
    assert "Avísame" in html and "Elixe" in html and "Paga" in html and "Confirma" in html
    r = client.post(f"{C}/reservas/agardar/{padel_a.pk}/", {"inicio": start.isoformat()})
    assert r.status_code == 302
    assert WaitlistEntry.objects.get().user == ana
    assert "Listas de espera" in client.get(f"{C}/reservas/").content.decode()


def test_full_cycle_cancel_offer_expire_accept_and_penalty_refund(
    client, citizen, ana, berto, padel_a, muni_a
):
    from apps.bookings.services import slot_starts

    now = timezone.now()
    # Unha franxa real dentro das próximas 24 h: a cancelación será tardía (penalización do 50 %)
    start = next(
        s
        for d in (0, 1)
        for s in slot_starts(padel_a, timezone.localdate() + dt.timedelta(days=d))
        if now + dt.timedelta(hours=2) < s < now + dt.timedelta(hours=23)
    )
    original = _confirmed(padel_a, citizen, start)
    a = waitlist.join(padel_a, start, ana)
    b = waitlist.join(padel_a, start, berto)
    refund, penalty = cancel_booking(original, by=citizen)
    assert penalty > 0 and refund == original.paid_cents - penalty
    rel = SlotRelease.objects.get()
    assert rel.reason == SlotRelease.Reason.CANCELLED and rel.released_booking == original
    a.refresh_from_db()
    b.refresh_from_db()
    assert a.status == WaitlistEntry.Status.OFFERED and b.status == WaitlistEntry.Status.WAITING
    assert Notification.objects.filter(user=ana, title__startswith="Quedou libre").exists()
    # Ana non responde no prazo → pasa a Berto
    waitlist.process(now=a.offer_expires_at + dt.timedelta(seconds=1))
    a.refresh_from_db()
    b.refresh_from_db()
    assert a.status == WaitlistEntry.Status.EXPIRED and b.status == WaitlistEntry.Status.OFFERED
    # Ana xa non a pode coller; Berto si (e paga)
    with pytest.raises(waitlist.WaitlistError):
        waitlist.accept(a, ana)
    client.force_login(berto)
    r = client.post(f"{C}/reservas/lista-de-espera/{b.pk}/", {"accion": "aceptar"})
    assert r.status_code == 302 and "/dev/tpv/" in r.url  # pasarela de pagamento
    b.refresh_from_db()
    taken = b.booking
    assert taken.user == berto and taken.status == Booking.Status.PENDING_PAYMENT
    rel.refresh_from_db()
    assert rel.taken_booking == taken and rel.closed_at
    events = [e["event"] for e in rel.log]
    assert events == ["released", "offered", "expired", "offered", "accepted", "penalty_refunded"]
    # A penalización devólvese porque a franxa se volveu vender
    original.refresh_from_db()
    assert rel.penalty_refunded_cents == penalty and original.refunded_cents == original.paid_cents
    # O ciclo vese na reserva orixinal
    client.force_login(citizen)
    html = client.get(f"{C}/reservas/{original.pk}/").content.decode()
    assert "Lista de espera" in html and "colleuna" in html


def test_no_waitlist_no_release(citizen, padel_a):
    b = _confirmed(padel_a, citizen, next_slot(padel_a, days=2))
    cancel_booking(b, by=citizen)
    assert not SlotRelease.objects.exists()


def test_closure_never_offers(citizen, ana, padel_a, muni_a):
    start = next_slot(padel_a, days=2)
    _confirmed(padel_a, citizen, start)
    waitlist.join(padel_a, start, ana)
    closure = Closure.objects.create(
        municipality=muni_a,
        facility=padel_a,
        reason="Obras",
        starts_at=start - dt.timedelta(hours=1),
        ends_at=start + dt.timedelta(hours=3),
    )
    apply_closure(closure)
    assert not SlotRelease.objects.exists()


def _now_slot(booking, minutes_from_start):
    """Move a reserva e a lista para que «agora» sexa `minutes_from_start` despois do inicio."""
    start = timezone.now() - dt.timedelta(minutes=minutes_from_start)
    end = start + dt.timedelta(minutes=booking.facility.slot_minutes)
    Booking.objects.filter(pk=booking.pk).update(start=start, end=end)
    WaitlistEntry.objects.filter(facility=booking.facility).update(start=start, end=end)
    return start


def test_no_checkin_release_levels_0_2_3_only(citizen, ana, padel_a, hall_a):
    b = _confirmed(padel_a, citizen, next_slot(padel_a, days=2))
    waitlist.join(padel_a, b.start, ana)
    _now_slot(b, 10)
    assert waitlist.process()["no_checkin"] == 0  # aínda dentro dos 15 min
    _now_slot(b, 16)
    assert waitlist.process()["no_checkin"] == 1
    b.refresh_from_db()
    assert b.status == Booking.Status.NO_SHOW
    assert SlotRelease.objects.get().reason == SlotRelease.Reason.NO_CHECKIN
    assert WaitlistEntry.objects.get(user=ana).status == WaitlistEntry.Status.OFFERED
    # Nivel 1 (chave custodiada): non se libera
    h = _confirmed(hall_a, citizen, next_slot(hall_a, days=2))
    waitlist.join(hall_a, h.start, ana)
    _now_slot(h, 20)
    waitlist.process()
    h.refresh_from_db()
    assert h.status == Booking.Status.CONFIRMED


def test_unconfirmed_release_off_by_default_then_on(citizen, ana, padel_a, muni_a):
    b = _confirmed(padel_a, citizen, next_slot(padel_a, days=2))
    waitlist.join(padel_a, b.start, ana)
    _now_slot(b, -60)  # empeza dentro dunha hora; o prazo por defecto é 120 min
    assert waitlist.process()["unconfirmed"] == 0
    muni_a.confirm_release_enabled = True
    muni_a.save()
    assert waitlist.process()["unconfirmed"] == 1
    b.refresh_from_db()
    assert b.status == Booking.Status.CANCELLED
    assert SlotRelease.objects.get().reason == SlotRelease.Reason.UNCONFIRMED


def test_confirmed_attendance_is_not_released(citizen, ana, padel_a, muni_a):
    muni_a.confirm_release_enabled = True
    muni_a.save()
    b = _confirmed(padel_a, citizen, next_slot(padel_a, days=2))
    waitlist.join(padel_a, b.start, ana)
    _now_slot(b, -60)
    b.refresh_from_db()
    waitlist.confirm_attendance(b)
    assert waitlist.process()["unconfirmed"] == 0
