# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · B: Alerta en todos os perfís, aviso ao persoal de servizo, DESA e ubicación para o 112."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import Membership, Role, User
from apps.activities.models import Activity, Group, Session
from apps.integrations.models import DevMail
from apps.maintenance.models import CleaningLog, WorkOrder
from apps.notifications.models import Notification
from apps.safety import services
from apps.safety.models import AccidentReport, Alert, ResponsibleContact

pytestmark = pytest.mark.django_db
C = "/c/concello-a"
ALERTA = "alert-pill"


def staff(muni, email, role):
    user = User.objects.create_user(email)
    Membership.objects.create(user=user, municipality=muni, role=role)
    return user


def open_session(muni, facility, monitor):
    now = timezone.localtime()
    group = Group.objects.create(
        municipality=muni,
        activity=Activity.objects.create(municipality=muni, name="Fútbol"),
        name="Benxamín",
        monitor=monitor,
        facility=facility,
        weekdays="0,1,2,3,4,5,6",
        start_time=now.time(),
    )
    return Session.objects.create(
        group=group,
        municipality=muni,
        date=now.date(),
        start_time=(now - dt.timedelta(minutes=5)).time(),
        duration_minutes=60,
    )


@pytest.mark.parametrize(
    "role,home,origin",
    [
        (Role.MAINTENANCE, "/operario/", Alert.Origin.OPERATOR),
        (Role.CLEANING, "/operario/", Alert.Origin.CLEANING),
        (Role.MONITOR, "/monitor/", Alert.Origin.MONITOR),
        (Role.ADMIN, "/xestion/", Alert.Origin.ADMIN),
    ],
)
def test_button_on_each_profile_and_origin(client, muni_a, hall_a, role, home, origin):
    user = staff(muni_a, f"{role}@example.org", role)
    client.force_login(user)
    html = client.get(f"{C}{home}").content.decode()
    assert ALERTA in html and f"{C}/seguridade/alerta/" in html
    client.post(f"{C}/seguridade/alerta/accidente/", {"instalacion": hall_a.pk})
    assert Alert.objects.get().origin == origin


def test_neighbour_keeps_existing_entry_without_new_button(client, citizen, muni_a):
    client.force_login(citizen)
    html = client.get(f"{C}/app/").content.decode()
    assert ALERTA not in html and "safety-btn" in html


def test_warns_designated_and_staff_on_service_only_there(muni_a, hall_a, gym_a):
    designated = ResponsibleContact.objects.create(
        municipality=muni_a, order=1, name="Garda", email="garda@example.org"
    )
    here_monitor = staff(muni_a, "aqui@example.org", Role.MONITOR)
    away_monitor = staff(muni_a, "ala@example.org", Role.MONITOR)
    open_session(muni_a, hall_a, here_monitor)
    open_session(muni_a, gym_a, away_monitor)
    operator = staff(muni_a, "op@example.org", Role.MAINTENANCE)
    WorkOrder.objects.create(
        municipality=muni_a,
        facility=hall_a,
        title="Revisar",
        due_date=timezone.localdate(),
        status=WorkOrder.Status.IN_PROGRESS,
        assigned_to=operator,
    )
    cleaner = staff(muni_a, "limpa@example.org", Role.CLEANING)
    CleaningLog.objects.create(
        municipality=muni_a, facility=hall_a, user=cleaner, done_at=timezone.now()
    )
    old_cleaner = staff(muni_a, "vella@example.org", Role.CLEANING)
    CleaningLog.objects.create(
        municipality=muni_a,
        facility=hall_a,
        user=old_cleaner,
        done_at=timezone.now() - dt.timedelta(hours=5),
    )
    alert = services.raise_alert(Alert.Kind.ACCIDENT, muni_a, facility=hall_a)
    for person in (here_monitor, operator, cleaner):
        assert Notification.objects.filter(user=person, title__startswith="ALERTA").exists()
    assert not Notification.objects.filter(user=away_monitor).exists()
    assert not Notification.objects.filter(user=old_cleaner).exists()
    # Correo á persoa designada; canles de cada persoa (correo para quen o ten activado)
    assert DevMail.objects.filter(to=designated.email).exists()
    assert DevMail.objects.filter(to=here_monitor.email).exists()
    # A alerta garda postos, nunca nomes nin correos do persoal
    assert "Garda" in alert.notified and "Persoa monitora" in alert.notified
    assert not any("@" in str(item) for item in alert.notified)


def test_channels_respect_each_person(muni_a, hall_a):
    monitor = staff(muni_a, "sencorreo@example.org", Role.MONITOR)
    monitor.notify_email = False
    monitor.save()
    open_session(muni_a, hall_a, monitor)
    services.raise_alert(Alert.Kind.SECURITY, muni_a, facility=hall_a)
    assert Notification.objects.filter(user=monitor).exists()
    assert not DevMail.objects.filter(to=monitor.email).exists()


def test_raiser_is_not_told_twice(client, muni_a, hall_a):
    monitor = staff(muni_a, "lanza@example.org", Role.MONITOR)
    session = open_session(muni_a, hall_a, monitor)
    client.force_login(monitor)
    client.post(f"{C}/seguridade/alerta/accidente/", {"sesion": session.pk})
    assert not Notification.objects.filter(user=monitor, title__startswith="ALERTA").exists()
    assert Alert.objects.get().facility == hall_a


def test_concierge_of_facility_gets_it_other_facility_not(muni_a, hall_a, gym_a):
    conserxe = staff(muni_a, "conserxe2@example.org", Role.MAINTENANCE)
    ResponsibleContact.objects.create(
        municipality=muni_a, order=1, name="Xeral", email="xeral@example.org"
    )
    ResponsibleContact.objects.create(
        municipality=muni_a,
        order=2,
        name="Conserxe pavillón",
        role_label="Conserxe",
        email="c-pav@example.org",
        user=conserxe,
        facility=hall_a,
    )
    alert = services.raise_alert(Alert.Kind.ACCIDENT, muni_a, facility=hall_a)
    assert "Conserxe" in alert.notified and DevMail.objects.filter(to="c-pav@example.org").exists()
    DevMail.objects.all().delete()
    services.raise_alert(Alert.Kind.ACCIDENT, muni_a, facility=gym_a)
    assert not DevMail.objects.filter(to="c-pav@example.org").exists()


def test_alert_screen_shows_aed_and_address(client, citizen, hall_a):
    hall_a.address = "Rúa da Eira, 3"
    hall_a.latitude, hall_a.longitude = "42.100000", "-8.200000"
    hall_a.aed_on_site = True
    hall_a.aed_inside_location = "Entrada principal"
    hall_a.save()
    client.force_login(citizen)
    html = client.get(f"{C}/seguridade/alerta/?instalacion={hall_a.pk}").content.decode()
    assert "Rúa da Eira, 3" in html and "Entrada principal" in html
    assert "42.100000, -8.200000" in html
    resp = client.post(
        f"{C}/seguridade/alerta/emerxencia/", {"instalacion": hall_a.pk}, follow=True
    )
    html = resp.content.decode()
    assert "Rúa da Eira, 3" in html and "Entrada principal" in html and "tel:112" in html
    resp = client.post(f"{C}/seguridade/alerta/accidente/", {"instalacion": hall_a.pk}, follow=True)
    assert "Rúa da Eira, 3" in resp.content.decode()


def test_nearest_aed_shown(client, citizen, hall_a):
    hall_a.aed_on_site = False
    hall_a.aed_near_name = "Farmacia"
    hall_a.aed_near_address = "Praza 1"
    hall_a.save()
    client.force_login(citizen)
    html = client.get(f"{C}/seguridade/alerta/?instalacion={hall_a.pk}").content.decode()
    assert "DESA máis próximo" in html and "Praza 1" in html


def test_staff_alert_defaults_to_working_facility(client, muni_a, hall_a):
    monitor = staff(muni_a, "autolugar@example.org", Role.MONITOR)
    open_session(muni_a, hall_a, monitor)
    client.force_login(monitor)
    html = client.get(f"{C}/seguridade/alerta/").content.decode()
    assert hall_a.name in html and 'id="alert-facility"' not in html


def test_accident_register_is_unchanged_no_free_text():
    names = {f.name for f in AccidentReport._meta.get_fields()}
    assert not names & {"notes", "description", "diagnosis", "person", "name"}
    text_fields = [
        f.name for f in AccidentReport._meta.fields if f.get_internal_type() == "TextField"
    ]
    assert not text_fields


def test_contact_form_only_own_facilities(client, admin_a, muni_a, hall_a, court_b):
    client.force_login(admin_a)
    html = client.get(f"{C}/xestion/seguridade/").content.decode()
    assert hall_a.name in html and court_b.name not in html
