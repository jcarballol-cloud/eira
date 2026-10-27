# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · A (Aviso e Alerta, protocolo e rexistro de accidentes) e B (peche sen confirmar)."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.access.models import LockDevice
from apps.accounts.models import Membership, Role, User
from apps.activities.models import Activity, Group, Session
from apps.bookings.models import Booking
from apps.bookings.services import submit_closing_checklist
from apps.incidents.models import Incident
from apps.integrations.models import DevMail
from apps.notifications.models import Notification
from apps.safety import services
from apps.safety.models import (
    AccidentProtocol,
    AccidentReport,
    Alert,
    ClosingEscalation,
    PoliceContact,
    ResponsibleContact,
)

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


def _booking(facility, user, start, minutes=60, status=Booking.Status.CONFIRMED, **extra):
    return Booking.objects.create(
        municipality=facility.municipality,
        facility=facility,
        user=user,
        start=start,
        end=start + dt.timedelta(minutes=minutes),
        status=status,
        **extra,
    )


@pytest.fixture
def conserxe(muni_a):
    return ResponsibleContact.objects.create(
        municipality=muni_a,
        order=1,
        name="Conserxe de proba",
        email="conserxe@example.org",
        from_time=dt.time(0, 0),
        until_time=dt.time(23, 59),
    )


@pytest.fixture
def dpo_a(muni_a):
    u = User.objects.create_user("dpd@example.org")
    Membership.objects.create(user=u, municipality=muni_a, role=Role.DPO)
    return u


# ---------------------------------------------------------------- A · botóns
def test_safety_page_keeps_old_options_and_adds_two_big_buttons(client, citizen, hall_a):
    client.force_login(citizen)
    html = client.get(f"{C}/seguridade/").content.decode()
    assert "big-choice__btn--notice" in html and "big-choice__btn--alert" in html
    assert ">Aviso<" in html and ">Alerta<" in html
    # O que xa existía segue: 112, risco e problema na instalación
    assert 'href="tel:112"' in html and "?risco=1" in html and "Avisar dun problema" in html
    assert "?comentario=1" in html


def test_alert_page_has_two_options(client, citizen, hall_a):
    client.force_login(citizen)
    html = client.get(f"{C}/seguridade/alerta/?instalacion={hall_a.pk}").content.decode()
    assert "Accidente deportivo" in html and "Emerxencia de seguridade" in html
    assert hall_a.name in html


def test_accident_alert_opens_protocol_notifies_and_creates_urgent_incident(
    client, citizen, admin_a, hall_a, conserxe
):
    hall_a.aed_on_site = True
    hall_a.aed_inside_location = "Entrada, á dereita do conserxe"
    hall_a.save()
    client.force_login(citizen)
    r = client.post(f"{C}/seguridade/alerta/accidente/", {"instalacion": hall_a.pk})
    alert = Alert.objects.get()
    assert alert.kind == Alert.Kind.ACCIDENT and alert.facility == hall_a
    assert r.status_code == 302 and f"/seguridade/accidente/{hall_a.pk}/?alerta={alert.pk}" in r.url
    # Incidencia de prioridade máxima vinculada, para que mantemento revise
    inc = alert.incident
    assert inc.priority == Incident.Priority.URGENT and inc.source == Incident.Source.ALERT
    # Avísase ao momento: persoa responsable (correo) e administración (app)
    assert DevMail.objects.filter(to="conserxe@example.org").exists()
    assert Notification.objects.filter(user=admin_a, title__startswith="ALERTA").exists()
    assert "Conserxe de proba" in alert.notified
    html = client.get(r.url).content.decode()
    for step in ("Protexe", "112", "DESA", "Avisar á persoa responsable", "Rexistrar o accidente"):
        assert step in html
    assert "Entrada, á dereita do conserxe" in html and 'href="tel:112"' in html


def test_security_alert_shows_112(client, citizen, hall_a):
    client.force_login(citizen)
    r = client.post(f"{C}/seguridade/alerta/emerxencia/", {"instalacion": hall_a.pk}, follow=True)
    html = r.content.decode()
    assert Alert.objects.get().kind == Alert.Kind.SECURITY
    assert "emergency-call--huge" in html and 'href="tel:112"' in html
    assert "Avisamos ao concello" in html


def test_anonymous_alerts_are_rate_limited(client, hall_a):
    for _ in range(services.ANON_ALERTS_PER_HOUR):
        client.post(f"{C}/seguridade/alerta/emerxencia/", {"instalacion": hall_a.pk})
    r = client.post(f"{C}/seguridade/alerta/emerxencia/", {"instalacion": hall_a.pk}, follow=True)
    assert Alert.objects.count() == services.ANON_ALERTS_PER_HOUR
    assert "Non puidemos avisar" in r.content.decode()  # o 112 segue á vista


def test_protocol_facility_overrides_town_and_default(muni_a, hall_a, gym_a):
    assert "Protexe" in services.protocol_for(muni_a, hall_a).protect  # plantilla
    AccidentProtocol.objects.create(municipality=muni_a, protect="Do concello")
    AccidentProtocol.objects.create(municipality=muni_a, facility=hall_a, protect="Do pavillón")
    assert services.protocol_for(muni_a, hall_a).protect == "Do pavillón"
    assert services.protocol_for(muni_a, gym_a).protect == "Do concello"


def test_nearest_aed_when_none_on_site(hall_a):
    hall_a.aed_on_site = False
    hall_a.aed_near_name = "Centro de saúde"
    hall_a.aed_near_distance_m = 350
    info = services.aed_info(hall_a)
    assert info["on_site"] is False and info["name"] == "Centro de saúde"
    assert info["distance_m"] == 350


def test_buttons_on_active_booking_screen(client, citizen, padel_a):
    now = timezone.now()
    live = _booking(padel_a, citizen, now - dt.timedelta(minutes=10))
    later = _booking(padel_a, citizen, now + dt.timedelta(days=2))
    client.force_login(citizen)
    assert "big-choice__btn--alert" in client.get(f"{C}/reservas/{live.pk}/").content.decode()
    assert "big-choice__btn--alert" not in client.get(f"{C}/reservas/{later.pk}/").content.decode()


def test_monitor_tablet_has_alert_button(client, muni_a, hall_a):
    monitor = User.objects.create_user("monitora@example.org")
    Membership.objects.create(user=monitor, municipality=muni_a, role=Role.MONITOR)
    group = Group.objects.create(
        municipality=muni_a,
        activity=Activity.objects.create(municipality=muni_a, name="Fútbol"),
        name="Benxamín",
        monitor=monitor,
        facility=hall_a,
        places=10,
        weekdays="0,1,2,3,4,5,6",
        start_time=dt.time(17),
    )
    session = Session.objects.create(
        group=group, municipality=muni_a, date=timezone.localdate(), start_time=dt.time(17)
    )
    client.force_login(monitor)
    for path in (
        f"{C}/monitor/sesion/{session.pk}/asistencia/",
        f"{C}/monitor/sesion/{session.pk}/rexistro/",
    ):
        html = client.get(path).content.decode()
        assert "monitor-alert" in html and f"sesion={session.pk}" in html
    client.post(f"{C}/seguridade/alerta/accidente/", {"sesion": session.pk})
    alert = Alert.objects.get()
    assert alert.origin == Alert.Origin.MONITOR and alert.facility == hall_a


# ---------------------------------------------------------------- A · rexistro de accidentes
def test_accident_register_minimal_data_and_access(
    client, citizen, admin_a, dpo_a, operator_a, hall_a
):
    client.force_login(citizen)
    r = client.post(
        f"{C}/seguridade/accidente/{hall_a.pk}/rexistrar/",
        {
            "occurred_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "kind": "fall",
            "severity": "mild",
            "reporter_role": "user",
        },
    )
    assert r.status_code == 200 and "Accidente rexistrado" in r.content.decode()
    report = AccidentReport.objects.get()
    assert report.kind == "fall" and report.reported_by == citizen and not report.called_112
    # Sen campos de texto libre: nada de diagnósticos nin datos clínicos
    text_fields = {
        f.name for f in AccidentReport._meta.fields if f.get_internal_type() == "TextField"
    }
    assert text_fields == set()
    # Só administración do concello e DPD
    for user, status in ((citizen, 403), (operator_a, 403), (admin_a, 200), (dpo_a, 200)):
        client.force_login(user)
        assert client.get(f"{C}/xestion/seguridade/accidentes/").status_code == status
    client.force_login(admin_a)
    client.post(
        f"{C}/xestion/seguridade/accidentes/", {"accidente": report.pk, "facility_related": "0"}
    )
    report.refresh_from_db()
    assert report.closed_at and report.facility_related is False


def test_accident_severity_112_marks_called(muni_a, hall_a):
    r = services.register_accident(
        muni_a, hall_a, kind="hit", severity="emergency", called_112=False, reporter_role="staff"
    )
    assert r.called_112


def test_accident_retention_purges_only_closed_old(muni_a, hall_a):
    muni_a.accident_retention_months = 12
    muni_a.save()
    old = timezone.now() - dt.timedelta(days=400)
    closed = services.register_accident(
        muni_a,
        hall_a,
        kind="fall",
        severity="mild",
        called_112=False,
        reporter_role="user",
        occurred_at=old,
    )
    services.close_accident(closed, None)
    services.register_accident(
        muni_a,
        hall_a,
        kind="fall",
        severity="mild",
        called_112=False,
        reporter_role="user",
        occurred_at=old,
    )
    assert services.purge_accidents() == 1
    assert AccidentReport.objects.count() == 1


# ---------------------------------------------------------------- B · escalado do peche
def _used(facility, user, ended_minutes_ago=0):
    end = timezone.now() - dt.timedelta(minutes=ended_minutes_ago)
    b = _booking(facility, user, end - dt.timedelta(minutes=60), status=Booking.Status.USED)
    b.checked_in_at = b.start
    b.save()
    return b


def test_escalation_reminders_then_contact_never_police(client, citizen, admin_a, hall_a, conserxe):
    muni = hall_a.municipality
    muni.police_phone = "000 000 092"
    muni.save()
    b = _used(hall_a, citizen)
    t0 = b.end
    services.escalate_closings(now=t0 + dt.timedelta(minutes=5))
    assert not ClosingEscalation.objects.get(booking=b).first_at
    # 1.º recordatorio: só pola app (sen correo)
    services.escalate_closings(now=t0 + dt.timedelta(minutes=10))
    esc = ClosingEscalation.objects.get(booking=b)
    assert esc.stage == 1
    n1 = Notification.objects.filter(user=citizen).latest("pk")
    assert "email" not in n1.channels
    b.refresh_from_db()
    assert b.close_unconfirmed  # queda anotado na reserva
    # 2.º recordatorio: app e canle activa (correo)
    services.escalate_closings(now=t0 + dt.timedelta(minutes=20))
    esc.refresh_from_db()
    assert esc.stage == 2
    assert "email" in Notification.objects.filter(user=citizen).latest("pk").channels
    # 3.º: aviso á persoa responsable de servizo, coa ligazón da súa páxina
    services.escalate_closings(now=t0 + dt.timedelta(minutes=30))
    esc.refresh_from_db()
    assert esc.stage == 3 and esc.contact == conserxe
    mail = DevMail.objects.filter(to="conserxe@example.org").latest("pk")
    assert esc.token in mail.body
    assert PoliceContact.objects.count() == 0  # a policía nunca se avisa soa
    assert not esc.counted_as_breach  # desactivado por defecto
    # A persoa responsable decide contactar coa policía: queda rexistrado
    html = client.get(f"{C}/seguridade/peche/{esc.token}/").content.decode()
    assert "Contactar coa Policía Local" in html
    r = client.post(f"{C}/seguridade/peche/{esc.token}/", {"accion": "policia"})
    assert 'href="tel:000000092"' in r.content.decode()
    assert PoliceContact.objects.get().escalation == esc
    client.post(f"{C}/seguridade/peche/{esc.token}/", {"accion": "revisado", "nota": "Todo ben"})
    esc.refresh_from_db()
    assert esc.outcome == ClosingEscalation.Outcome.CHECKED and esc.note == "Todo ben"


def test_checklist_stops_escalation(citizen, hall_a):
    b = _used(hall_a, citizen)
    services.escalate_closings(now=b.end + dt.timedelta(minutes=10))
    submit_closing_checklist(b, True, True, True)
    esc = ClosingEscalation.objects.get(booking=b)
    assert esc.outcome == ClosingEscalation.Outcome.CLOSED_BY_USER
    services.escalate_closings(now=b.end + dt.timedelta(minutes=40))
    esc.refresh_from_db()
    assert esc.stage == 1


def test_level3_door_closed_is_not_escalated(citizen, pool_a, conserxe):
    lock = LockDevice.objects.get(facility=pool_a)
    lock.door_closed = True
    lock.save()
    b = _used(pool_a, citizen)
    for minutes in (10, 20, 30):
        services.escalate_closings(now=b.end + dt.timedelta(minutes=minutes))
    esc = ClosingEscalation.objects.get(booking=b)
    assert esc.outcome == ClosingEscalation.Outcome.DOOR_CLOSED and esc.escalated_at is None
    assert not DevMail.objects.filter(to="conserxe@example.org").exists()


def test_level3_door_open_is_escalated(citizen, pool_a, conserxe):
    lock = LockDevice.objects.get(facility=pool_a)
    lock.door_closed = False
    lock.save()
    b = _used(pool_a, citizen)
    for minutes in (10, 20, 30):
        services.escalate_closings(now=b.end + dt.timedelta(minutes=minutes))
    esc = ClosingEscalation.objects.get(booking=b)
    assert esc.stage == 3 and esc.door_state == "open"


def test_breach_only_if_enabled_and_level0_skipped(citizen, hall_a, court_b, muni_a):
    muni_a.close_breach_enabled = True
    muni_a.save()
    b = _used(hall_a, citizen)
    for minutes in (10, 20, 30):
        services.escalate_closings(now=b.end + dt.timedelta(minutes=minutes))
    assert ClosingEscalation.objects.get(booking=b).counted_as_breach
    # Nivel 0 (pista aberta): non hai nada que pechar
    other = _used(court_b, citizen)
    services.escalate_closings(now=other.end + dt.timedelta(minutes=30))
    assert not ClosingEscalation.objects.filter(booking=other).exists()


def test_configurable_times(citizen, hall_a, muni_a):
    muni_a.close_reminder_minutes = 30
    muni_a.save()
    b = _used(hall_a, citizen)
    services.escalate_closings(now=b.end + dt.timedelta(minutes=15))
    assert ClosingEscalation.objects.get(booking=b).stage == 0
    services.escalate_closings(now=b.end + dt.timedelta(minutes=31))
    assert ClosingEscalation.objects.get(booking=b).stage == 1


def test_contact_schedule_by_hour(muni_a):
    day = ResponsibleContact.objects.create(
        municipality=muni_a, order=1, name="Conserxe", from_time=dt.time(8), until_time=dt.time(22)
    )
    night = ResponsibleContact.objects.create(
        municipality=muni_a, order=2, name="Garda", from_time=dt.time(22), until_time=dt.time(8)
    )
    tz = timezone.get_current_timezone()
    noon = dt.datetime.combine(timezone.localdate(), dt.time(12), tzinfo=tz)
    late = dt.datetime.combine(timezone.localdate(), dt.time(23, 30), tzinfo=tz)
    early = dt.datetime.combine(timezone.localdate(), dt.time(6), tzinfo=tz)
    assert services.on_duty(muni_a, noon) == [day]
    assert services.on_duty(muni_a, late) == [night]
    assert services.on_duty(muni_a, early) == [night]


def test_manage_safety_pages(client, admin_a, hall_a, conserxe):
    client.force_login(admin_a)
    assert client.get(f"{C}/xestion/seguridade/").status_code == 200
    r = client.post(
        f"{C}/xestion/seguridade/",
        {"accion": "contacto", "c-order": 2, "c-name": "Garda", "c-active": "on"},
    )
    assert r.status_code == 302 and ResponsibleContact.objects.filter(name="Garda").exists()
    r = client.post(
        f"{C}/xestion/seguridade/protocolo/?instalacion={hall_a.pk}",
        {"protect": "P", "call": "C", "aed": "A", "notify": "N", "register": "R"},
    )
    assert AccidentProtocol.objects.get(facility=hall_a).protect == "P"
