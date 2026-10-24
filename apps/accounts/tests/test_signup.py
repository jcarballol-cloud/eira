# SPDX-License-Identifier: EUPL-1.2
"""v2 F2: solicitar a app, instalar, primeira apertura, mostrador e persoas apuntadas polo monitor."""

import datetime as dt
import re

import pytest
from django.utils import timezone

from apps.accounts.models import AppRequest, Consent, Membership, ResidencyInvitation, Role, User
from apps.activities.models import Activity, Enrollment, Group, PendingParticipant, Session
from apps.integrations.models import DevMail

pytestmark = pytest.mark.django_db


@pytest.fixture
def muni(muni_a):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.accounts import padron

    muni_a.postcodes = "15999"
    muni_a.contact_phone = "981 000 000"
    muni_a.save()
    # v4: padrón cargado por CSV (ficticio): só esta persoa figura
    padron.import_csv(
        muni_a, SimpleUploadedFile("p.csv", b"dni_nie;data_nacemento\n12345678Z;14/05/1990\n")
    )
    return muni_a


def ask(client, **over):
    data = {
        "name": "Persoa",
        "surnames": "Proba Exemplo",
        "email": "proba.app@example.org",
        "id_number": "12345678Z",
        "birth_date": "1990-05-14",
        "resident": "on",
    }
    data.update(over)
    return client.post("/c/concello-a/app/solicitar/", data)


def last_mail(to):
    return DevMail.objects.filter(to=to).latest("id")


def test_public_home_invites_to_request_the_app(client, muni):
    html = client.get("/c/concello-a/").content.decode()
    assert "/c/concello-a/app/solicitar/" in html


def test_request_matching_padron_sends_link_and_code(client, muni):
    r = ask(client)
    assert r.status_code == 302 and r["Location"].endswith("/app/solicitar/enviada/")
    req = AppRequest.objects.get()
    assert req.padron_match and req.status == AppRequest.Status.SENT
    inv = req.invitation
    assert inv.email == "proba.app@example.org"
    body = last_mail("proba.app@example.org").body
    assert inv.code in body and f"/c/concello-a/app/instalar/?codigo={inv.code}" in body
    assert "iPhone" in body and "Android" in body
    assert "Mira o teu correo" in client.get(r["Location"]).content.decode()


def test_request_not_in_padron_goes_to_review(client, muni, admin_a):
    ask(client, id_number="00000001R")
    req = AppRequest.objects.get()
    assert not req.padron_match and req.status == AppRequest.Status.PENDING
    assert req.invitation is None
    # O concello revisa e envía o código
    client.force_login(admin_a)
    assert "Proba Exemplo" in client.get("/c/concello-a/xestion/altas/").content.decode()
    client.post(f"/c/concello-a/xestion/altas/{req.pk}/resolver/", {"action": "approve"})
    req.refresh_from_db()
    assert req.status == AppRequest.Status.SENT and req.invitation.code in last_mail(req.email).body


def test_reject_notifies_and_issues_nothing(client, muni, admin_a):
    ask(client, id_number="00000001R")
    req = AppRequest.objects.get()
    client.force_login(admin_a)
    client.post(f"/c/concello-a/xestion/altas/{req.pk}/resolver/", {"action": "reject"})
    req.refresh_from_db()
    assert req.status == AppRequest.Status.REJECTED and req.invitation is None
    assert ResidencyInvitation.objects.count() == 0


def test_non_resident_gets_app_without_code(client, muni):
    ask(client, resident="")
    req = AppRequest.objects.get()
    assert req.invitation is None and req.status == AppRequest.Status.SENT
    assert "/app/instalar/" in last_mail(req.email).body


def test_install_page_keeps_code_and_shows_both_platforms(client, muni):
    r = client.get(
        "/c/concello-a/app/instalar/?codigo=ABCD-2345",
        HTTP_USER_AGENT="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
    )
    html = r.content.decode()
    assert "ABCD-2345" in html and "Android" in html and "Engadir á pantalla de inicio" in html
    assert client.session["residency_code"] == "ABCD-2345"


def test_first_open_asks_code_prefilled_then_family(client, muni):
    ask(client)
    inv = AppRequest.objects.get().invitation
    client.get(f"/c/concello-a/app/instalar/?codigo={inv.code}")
    # Sen sesión, a primeira apertura pide entrar
    r = client.get("/c/concello-a/app/benvida/")
    assert r.status_code == 302 and "/acceso/" in r["Location"]
    user = User.objects.create_user("proba.app@example.org")
    client.force_login(user)
    html = client.get("/c/concello-a/app/benvida/").content.decode()
    assert f'value="{inv.code}"' in html
    r = client.post("/c/concello-a/app/benvida/", {"code": inv.code})
    assert r["Location"].endswith("?paso=familia")
    assert user.is_resident(muni)
    html = client.get(r["Location"]).content.decode()
    assert "Tes fillos ou persoas ao teu cargo?" in html


def test_code_sent_to_an_email_only_works_for_that_account(client, muni):
    ask(client)
    inv = AppRequest.objects.get().invitation
    other = User.objects.create_user("outra@example.org")
    client.force_login(other)
    r = client.post("/c/concello-a/app/benvida/", {"code": inv.code})
    assert r.status_code == 200 and not other.is_resident(muni)
    inv.refresh_from_db()
    assert inv.used_at is None


def test_code_accepts_lowercase_and_no_dash(client, muni, outsider):
    inv = ResidencyInvitation.issue(muni)
    client.force_login(outsider)
    client.post("/c/concello-a/app/benvida/", {"code": inv.code.replace("-", "").lower()})
    assert outsider.is_resident(muni)


def test_app_home_asks_about_family(client, muni, citizen):
    client.force_login(citizen)
    html = client.get("/c/concello-a/app/").content.decode()
    assert "Tes fillos ou persoas ao teu cargo?" in html


def test_counter_signup_prints_sheet_with_qr(client, muni, admin_a):
    client.force_login(admin_a)
    r = client.post(
        "/c/concello-a/xestion/altas/",
        {
            "c-name": "Persoa Maior",
            "c-email": "",
            "c-birth_year": 1948,
            "c-postcode": "15999",
            "c-checked": "on",
        },
    )
    req = AppRequest.objects.get()
    assert req.channel == AppRequest.Channel.COUNTER and req.invitation
    assert r["Location"].endswith(f"/xestion/altas/{req.pk}/folla/")
    html = client.get(r["Location"]).content.decode()
    assert "<svg" in html and req.invitation.code in html and "data-print" in html
    assert f"instalar/?codigo={req.invitation.code}" in html


def test_counter_requires_padron_check(client, muni, admin_a):
    client.force_login(admin_a)
    client.post(
        "/c/concello-a/xestion/altas/",
        {"c-name": "Sen comprobar", "c-birth_year": 1948, "c-postcode": "15999"},
    )
    assert not AppRequest.objects.exists()


def test_signups_admin_only(client, muni, citizen, operator_a):
    for u in (citizen, operator_a):
        client.force_login(u)
        assert client.get("/c/concello-a/xestion/altas/").status_code == 403


# ---------------------------------------------------------------- monitor


@pytest.fixture
def group(muni):
    monitor = User.objects.create_user("monitora@example.org")
    Membership.objects.create(user=monitor, municipality=muni, role=Role.MONITOR)
    a = Activity.objects.create(municipality=muni, name="Fútbol")
    g = Group.objects.create(
        municipality=muni,
        activity=a,
        name="Benxamín",
        monitor=monitor,
        min_age=8,
        max_age=10,
        places=10,
        fee_cents=0,
        weekdays="0,1,2,3,4,5,6",
        start_time=dt.time(17),
    )
    g.monitor_user = monitor
    return g


def test_monitor_adds_pending_name_and_concello_validates(client, group, admin_a):
    session = Session.objects.create(
        municipality=group.municipality,
        group=group,
        date=timezone.localdate(),
        start_time=dt.time(17),
    )
    client.force_login(group.monitor_user)
    year = timezone.localdate().year - 9
    client.post(
        f"/c/concello-a/monitor/sesion/{session.pk}/engadir/",
        {"first_name": "Lúa", "birth_year": year, "guardian_email": "familia.lua@example.org"},
    )
    p = PendingParticipant.objects.get()
    assert p.status == PendingParticipant.Status.PENDING and p.added_by == group.monitor_user
    html = client.get(f"/c/concello-a/monitor/sesion/{session.pk}/asistencia/").content.decode()
    assert "Lúa" in html and "Pendente" in html
    assert not Enrollment.objects.exists()
    # O monitor non pode validar
    assert (
        client.post(
            f"/c/concello-a/xestion/actividades/pendentes/{p.pk}/", {"action": "validate"}
        ).status_code
        == 403
    )
    # O concello: sen autorización en papel non se valida un menor
    client.force_login(admin_a)
    client.post(f"/c/concello-a/xestion/actividades/pendentes/{p.pk}/", {"action": "validate"})
    p.refresh_from_db()
    assert p.status == PendingParticipant.Status.PENDING
    client.post(
        f"/c/concello-a/xestion/actividades/pendentes/{p.pk}/",
        {"action": "validate", "paper_consent": "1", "guardian_email": "familia.lua@example.org"},
    )
    p.refresh_from_db()
    assert p.status == PendingParticipant.Status.VALIDATED
    e = p.enrollment
    assert e.dependent.first_name == "Lúa" and e.user.email == "familia.lua@example.org"
    assert e.status == Enrollment.Status.ACTIVE
    assert e.dependent.consents.get(kind=Consent.Kind.DATA).text_version == "papel"
    assert "Lúa" in last_mail("familia.lua@example.org").body


def test_monitor_cannot_add_to_other_groups(client, group, muni):
    other = User.objects.create_user("outra-monitora@example.org")
    Membership.objects.create(user=other, municipality=muni, role=Role.MONITOR)
    session = Session.objects.create(
        municipality=muni, group=group, date=timezone.localdate(), start_time=dt.time(17)
    )
    client.force_login(other)
    r = client.post(f"/c/concello-a/monitor/sesion/{session.pk}/engadir/", {"first_name": "X"})
    assert r.status_code == 404 and not PendingParticipant.objects.exists()


def test_request_form_shows_layered_privacy(client, muni):
    html = client.get("/c/concello-a/app/solicitar/").content.decode()
    assert "Que facemos con estes datos" in html and re.search(r"Responsable", html)
