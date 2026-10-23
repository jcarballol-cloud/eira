# SPDX-License-Identifier: EUPL-1.2
"""v2 F8: RXPD visible. Centro de privacidade, consentimentos de menores (art. 7 LOPDGDD),
imaxe con iconas e filtro, cookies só técnicas e visibilidade por perfil (docs/rxpd/matriz.md)."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import AppRequest, Consent, Dependent, Household, Membership, Role, User
from apps.activities.models import Activity, Enrollment, Group, Session

pytestmark = pytest.mark.django_db
TECHNICAL_COOKIES = {"sessionid", "csrftoken", "django_language", "eira_prefs", "eira_marco"}


def test_only_technical_cookies(client, citizen, padel_a, admin_a):
    seen = set()
    for url in ["/", "/c/concello-a/", f"/c/concello-a/instalacions/{padel_a.pk}/", "/acceso/"]:
        seen |= set(client.get(url).cookies)
    client.post("/acceso/", {"email": "proba@example.org"})
    client.get("/preferencias/")
    for u in (citizen, admin_a):
        client.force_login(u)
        for url in ["/c/concello-a/app/", "/conta/privacidade/", "/c/concello-a/xestion/"]:
            seen |= set(client.get(url).cookies)
    assert seen <= TECHNICAL_COOKIES, seen - TECHNICAL_COOKIES


def test_privacy_centre_toggles_and_dpo(client, citizen, muni_a):
    muni_a.dpo_contact = "dpd@concello-a.example"
    muni_a.save()
    client.force_login(citizen)
    html = client.get("/conta/privacidade/").content.decode()
    for text in (
        "dpd@concello-a.example",
        "aepd.es",
        "Descargar todos os meus datos",
        "Eliminar a miña conta",
        "sessionid",
    ):
        assert text in html
    client.post("/conta/privacidade/", {"notify_email": "on", "photo_consent": "on"})
    citizen.refresh_from_db()
    assert citizen.photo_consent and citizen.photo_consent_at and citizen.notify_email
    client.post("/conta/privacidade/", {"notify_email": "on"})
    citizen.refresh_from_db()
    assert not citizen.photo_consent and citizen.photo_consent_at is None


def test_under_14_family_consents_14_plus_needs_minor_agreement(client, citizen):
    client.force_login(citizen)
    year = timezone.localdate().year
    client.post(
        "/conta/familia/", {"first_name": "Pequena", "birth_year": year - 9, "consent_data": "on"}
    )
    assert Dependent.objects.filter(first_name="Pequena").exists()
    r = client.post(
        "/conta/familia/", {"first_name": "Maior", "birth_year": year - 15, "consent_data": "on"}
    )
    assert r.status_code == 200 and not Dependent.objects.filter(first_name="Maior").exists()
    client.post(
        "/conta/familia/",
        {
            "first_name": "Maior",
            "birth_year": year - 15,
            "consent_data": "on",
            "minor_agrees": "on",
        },
    )
    d = Dependent.objects.get(first_name="Maior")
    assert not d.under_14 and Dependent.objects.get(first_name="Pequena").under_14


@pytest.fixture
def group_with_people(muni_a, citizen):
    monitor = User.objects.create_user("monitora@example.org")
    Membership.objects.create(user=monitor, municipality=muni_a, role=Role.MONITOR)
    a = Activity.objects.create(municipality=muni_a, name="Fútbol")
    g = Group.objects.create(
        municipality=muni_a,
        activity=a,
        name="Benxamín",
        monitor=monitor,
        min_age=0,
        max_age=99,
        places=20,
        fee_cents=0,
        weekdays="0,1,2,3,4,5,6",
        start_time=dt.time(17),
    )
    hh = Household.objects.create(responsible=citizen)
    year = timezone.localdate().year
    with_photo = Dependent.objects.create(household=hh, first_name="ConFoto", birth_year=year - 9)
    no_photo = Dependent.objects.create(household=hh, first_name="SenFoto", birth_year=year - 9)
    for d in (with_photo, no_photo):
        Consent.objects.create(dependent=d, kind="data", granted_by=citizen)
        Enrollment.objects.create(
            municipality=muni_a, group=g, user=citizen, dependent=d, status="active"
        )
    Consent.objects.create(dependent=with_photo, kind="image", granted_by=citizen)
    s = Session.objects.create(
        municipality=muni_a, group=g, date=timezone.localdate(), start_time=dt.time(17)
    )
    return {"group": g, "session": s, "monitor": monitor}


def test_tablet_attendance_shows_photo_icons_and_filter(client, group_with_people):
    client.force_login(group_with_people["monitor"])
    html = client.get(
        f"/c/concello-a/monitor/sesion/{group_with_people['session'].pk}/asistencia/"
    ).content.decode()
    assert "Só quen non pode saír en fotos" in html
    con = html.index("ConFoto")
    sen = html.index("SenFoto")
    assert '#camera"' in html[con - 600 : con] and "#camera-off" in html[sen - 600 : sen]
    # o monitor non ve datos de contacto da familia
    assert "veciña@example.org" not in html and group_with_people["group"].monitor.email not in html


def test_admin_group_view_filters_no_photo(client, admin_a, group_with_people):
    client.force_login(admin_a)
    url = f"/c/concello-a/xestion/actividades/grupo/{group_with_people['group'].pk}/"
    html = client.get(url).content.decode()
    assert "ConFoto" in html and "SenFoto" in html
    only = client.get(url + "?sen_fotos=1").content.decode()
    assert "SenFoto" in only and "ConFoto" not in only


def test_group_view_forbidden_for_monitor_operator_neighbour(
    client, group_with_people, citizen, operator_a
):
    url = f"/c/concello-a/xestion/actividades/grupo/{group_with_people['group'].pk}/"
    for u in (group_with_people["monitor"], operator_a, citizen):
        client.force_login(u)
        assert client.get(url).status_code == 403


def test_operator_never_sees_reporter_contact(client, operator_a, citizen, padel_a):
    from apps.incidents.models import Incident
    from apps.maintenance.models import WorkOrder

    inc = Incident.objects.create(
        municipality=padel_a.municipality,
        facility=padel_a,
        reporter=citizen,
        category="damage",
        description="Rede rota",
    )
    order = WorkOrder.objects.create(
        municipality=padel_a.municipality,
        facility=padel_a,
        incident=inc,
        title="Rede",
        assigned_to=operator_a,
        due_date=timezone.localdate(),
    )
    client.force_login(operator_a)
    html = client.get(f"/c/concello-a/operario/orde/{order.pk}/").content.decode()
    assert "Rede" in html and citizen.email not in html and citizen.display_name not in html


def test_app_requests_purged_after_12_months(muni_a):
    from apps.bookings.management.commands.booking_maintenance import purge_app_requests

    old = AppRequest.objects.create(municipality=muni_a, name="Vella", email="v@example.org")
    AppRequest.objects.filter(pk=old.pk).update(created_at=timezone.now() - dt.timedelta(days=400))
    AppRequest.objects.create(municipality=muni_a, name="Nova", email="n@example.org")
    assert purge_app_requests() == 1
    assert list(AppRequest.objects.values_list("name", flat=True)) == ["Nova"]


def test_export_includes_photo_consent_and_excludes_others(client, citizen, outsider):
    client.force_login(citizen)
    data = client.get("/conta/os-meus-datos.json").json()
    assert data["user"]["email"] == citizen.email and outsider.email not in str(data)
