# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · H: abonos (oficina e TPV, renovación, desconto), carné con QR asinado (dixital que
caduca e impreso anulable), lector do persoal, tableta, PDF e adaptador municipal_card."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import Membership, Role, User
from apps.activities.models import Activity, Attendance, Enrollment, Group, Session
from apps.bookings import payments
from apps.bookings.models import Booking, Payment
from apps.bookings.services import price_for
from apps.integrations.registry import get_adapter
from apps.members import services
from apps.members.models import MemberCard, PassType, SportsPass

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


@pytest.fixture
def general(muni_a):
    return PassType.objects.create(
        municipality=muni_a, name="Abono xeral", price_cents=3000, valid_days=365, discount_pct=20
    )


def test_office_sale_activates_and_renewal_chains(citizen, general, admin_a):
    p = services.buy_pass(general, citizen, method="cash", by=admin_a)
    assert p.status == "active" and p.starts_on == timezone.localdate()
    assert p.expires_on == p.starts_on + dt.timedelta(days=364)
    assert Payment.objects.get(sports_pass=p).status == Payment.Status.PAID
    assert MemberCard.objects.filter(user=citizen).count() == 1
    renewal = services.buy_pass(general, citizen, method="card_terminal", by=admin_a)
    assert renewal.starts_on == p.expires_on + dt.timedelta(days=1)


def test_tpv_purchase_from_app(client, citizen, general):
    client.force_login(citizen)
    r = client.post(f"{C}/carne/", {"accion": "abono", "tipo": general.pk})
    assert r.status_code == 302 and "/dev/tpv/" in r.url
    p = SportsPass.objects.get(user=citizen)
    assert p.status == "pending"
    pay = Payment.objects.get(sports_pass=p)
    payments._apply_paid(pay)
    p.refresh_from_db()
    assert p.status == "active"


def test_member_discount_adds_to_existing_rules(citizen, general, padel_a, muni_a):
    base = price_for(padel_a, citizen).price
    services.buy_pass(general, citizen, method="cash")
    citizen = User.objects.get(pk=citizen.pk)  # sen a caché do abono
    q = price_for(padel_a, citizen)
    assert q.price == base * 80 // 100 and q.member_pct == 20 and q.audience == "resident"
    muni_a.modules = {**muni_a.modules, "cards": False}
    muni_a.save()
    padel_a.municipality.refresh_from_db()
    citizen = User.objects.get(pk=citizen.pk)
    assert price_for(padel_a, citizen).price == base


def test_live_qr_expires_and_print_qr_can_be_revoked(citizen, muni_a, muni_b):
    card = services.ensure_card(muni_a, citizen)
    token = services.live_token(card)
    assert services.read_token(token, muni_a) == card
    with pytest.raises(services.CardError):
        services.read_token(token, muni_a, max_age=-1)  # pasados os minutos, xa non vale
    with pytest.raises(services.CardError):
        services.read_token(token, muni_b)  # doutro concello
    printed = services.print_token(card)
    assert services.read_token(printed, muni_a) == card
    services.revoke_printed(card)
    with pytest.raises(services.CardError):
        services.read_token(printed, muni_a)
    with pytest.raises(services.CardError):
        services.read_token("non-é-un-carné", muni_a)
    # O QR non leva datos persoais
    assert citizen.email not in token and "Veciña" not in printed


def test_card_page_qr_refresh_and_pdf(client, citizen, general):
    client.force_login(citizen)
    html = client.get(f"{C}/carne/").content.decode()
    assert "<svg" in html and 'hx-trigger="every 60s"' in html and "Abono xeral" in html
    assert "<svg" in client.get(f"{C}/carne/qr/").content.decode()
    pdf = client.get(f"{C}/carne/carne.pdf").content
    assert pdf.startswith(b"%PDF") and b"/MarkInfo" in pdf and b"/MediaBox [0 0 243 153]" in pdf


def test_reader_checkin_and_vouchers(client, citizen, admin_a, padel_a, general):
    services.buy_pass(general, citizen, method="cash")
    now = timezone.now()
    b = Booking.objects.create(
        municipality=padel_a.municipality,
        facility=padel_a,
        user=citizen,
        start=now - dt.timedelta(minutes=5),
        end=now + dt.timedelta(minutes=55),
        status=Booking.Status.CONFIRMED,
    )
    card = MemberCard.objects.get(user=citizen)
    client.force_login(admin_a)
    token = services.live_token(card)
    html = client.post(f"{C}/xestion/carne/", {"qr": token}).content.decode()
    assert "Abono xeral" in html and "Rexistrar a entrada" in html
    client.post(f"{C}/xestion/carne/", {"qr": token, "accion": "entrada"})
    b.refresh_from_db()
    assert b.status == Booking.Status.USED and b.checked_in_at


def test_tablet_attendance_with_card(client, citizen, muni_a, hall_a):
    monitor = User.objects.create_user("monitora@example.org")
    Membership.objects.create(user=monitor, municipality=muni_a, role=Role.MONITOR)
    group = Group.objects.create(
        municipality=muni_a,
        activity=Activity.objects.create(municipality=muni_a, name="Ioga"),
        name="Adultos",
        monitor=monitor,
        facility=hall_a,
        places=10,
        weekdays="0,1,2,3,4,5,6",
        start_time=dt.time(18),
    )
    e = Enrollment.objects.create(municipality=muni_a, group=group, user=citizen, status="active")
    session = Session.objects.create(
        group=group, municipality=muni_a, date=timezone.localdate(), start_time=dt.time(18)
    )
    card = services.ensure_card(muni_a, citizen)
    client.force_login(monitor)
    html = client.get(f"{C}/monitor/sesion/{session.pk}/asistencia/").content.decode()
    assert "Ler carné" in html and "name-toggle" in html  # a lista por nome mantense
    client.post(f"{C}/monitor/sesion/{session.pk}/carne/", {"qr": services.live_token(card)})
    assert Attendance.objects.get(session=session, enrollment=e).present


def test_manage_passes(client, admin_a, muni_a, citizen):
    client.force_login(admin_a)
    r = client.post(
        f"{C}/xestion/abonos/",
        {
            "accion": "tipo",
            "t-name": "Maiores",
            "t-kind": "senior",
            "t-price_cents": 1500,
            "t-valid_days": 365,
            "t-discount_pct": 30,
            "t-active": "on",
        },
    )
    assert r.status_code == 302
    pt = PassType.objects.get(name="Maiores")
    r = client.post(
        f"{C}/xestion/abonos/",
        {"accion": "vender", "v-email": citizen.email, "v-type": pt.pk, "v-method": "cash"},
    )
    assert r.status_code == 302 and SportsPass.objects.get(user=citizen).status == "active"


def test_municipal_card_adapter_is_simulated(citizen, muni_a):
    adapter = get_adapter("municipal_card")
    assert adapter.lookup(muni_a, "BIB-00012") is None  # concello-a non está no CSV ficticio
    from apps.tenants.models import Municipality

    vil = Municipality.objects.create(name="Vilardeiras", slug="vilardeiras")
    card = services.ensure_card(vil, citizen)
    assert adapter.link(card, "BIB-00012") and card.external_id == "BIB-00012"
    assert not adapter.link(card, "BIB-00077")  # caducado


def test_municipality_with_passes_can_be_deleted(citizen, general, muni_a):
    """A rexeneración da demo (e o borrado dun concello) non se pode bloquear polos abonos."""
    services.buy_pass(general, citizen, method="cash")
    muni_a.delete()
    assert not SportsPass.objects.exists() and not PassType.objects.exists()
