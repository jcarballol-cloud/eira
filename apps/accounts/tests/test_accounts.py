# SPDX-License-Identifier: EUPL-1.2
import json
import re

import pytest

from apps.accounts.models import AuditLog, Consent, LoginCode, ResidencyInvitation, User
from apps.bookings.models import Booking
from apps.bookings.services import create_booking
from apps.integrations.models import DevMail
from conftest import next_slot

pytestmark = pytest.mark.django_db


def last_code(email):
    mail = DevMail.objects.filter(to=email).first()
    return re.search(r"\b(\d{6})\b", mail.body).group(1)


def test_passwordless_login_flow(client):
    r = client.post("/acceso/", {"email": "Nova@Example.org"})
    assert r.status_code == 302 and r["Location"].endswith("/acceso/codigo/")
    code = last_code("nova@example.org")
    assert not LoginCode.objects.filter(code_hash__contains=code).exists()  # só se garda o HMAC
    r = client.post("/acceso/codigo/", {"code": code})
    assert r.status_code == 302
    user = User.objects.get(email="nova@example.org")
    assert not user.has_usable_password()
    assert client.get("/conta/").status_code == 200


def test_wrong_code_and_attempt_limit(client, settings):
    client.post("/acceso/", {"email": "a@example.org"})
    code = last_code("a@example.org")
    for _ in range(settings.EIRA_LOGIN_CODE_MAX_ATTEMPTS):
        r = client.post("/acceso/codigo/", {"code": "000000" if code != "000000" else "111111"})
        assert "incorrecto" in r.content.decode()
    r = client.post("/acceso/codigo/", {"code": code})  # bloqueado tras o máximo de intentos
    assert "incorrecto" in r.content.decode()


def test_code_is_single_use(client):
    client.post("/acceso/", {"email": "b@example.org"})
    code = last_code("b@example.org")
    assert LoginCode.verify("b@example.org", code)
    assert not LoginCode.verify("b@example.org", code)


def test_rate_limit_on_sending_codes(client, settings):
    settings.EIRA_LOGIN_RATE_LIMIT = 3
    for _ in range(3):
        client.post("/acceso/", {"email": "c@example.org"})
    r = client.post("/acceso/", {"email": "c@example.org"})
    assert "Demasiados intentos" in r.content.decode()
    assert DevMail.objects.filter(to="c@example.org").count() == 3


def test_fake_clave_flow(client):
    r = client.get("/acceso/clave/")
    assert r.status_code == 302 and "/dev/clave/" in r["Location"]
    state = r["Location"].split("state=")[1]
    r = client.post("/acceso/clave/volta/", {"state": state, "identity": "proba-1"})
    assert r.status_code == 302
    user = User.objects.get(email="clave.proba1@example.org")
    assert user.identity_subject and "proba" not in user.identity_subject  # identificador opaco


def test_clave_rejects_bad_state(client):
    client.get("/acceso/clave/")
    client.post("/acceso/clave/volta/", {"state": "manipulado", "identity": "proba-1"})
    assert not User.objects.filter(email="clave.proba1@example.org").exists()


def test_open_redirect_blocked(client):
    client.post(
        "/acceso/?next=https://malicioso.example/",
        {"email": "d@example.org", "next": "https://malicioso.example/"},
    )
    r = client.post("/acceso/codigo/", {"code": last_code("d@example.org")})
    assert r["Location"] == "/"


def test_residency_invitation(client, citizen, muni_b):
    inv = ResidencyInvitation.issue(muni_b)
    client.force_login(citizen)
    client.post("/conta/empadroamento/", {"code": inv.code.lower()})
    assert citizen.is_resident(muni_b)
    inv.refresh_from_db()
    assert inv.used_by == citizen
    other = User.objects.create_user("outra@example.org")
    client.force_login(other)
    client.post("/conta/empadroamento/", {"code": inv.code})
    assert not other.is_resident(muni_b)


def test_export_my_data(client, citizen, padel_a):
    create_booking(padel_a, next_slot(padel_a), citizen, rules_version=padel_a.current_rules())
    client.force_login(citizen)
    r = client.get("/conta/os-meus-datos.json")
    data = json.loads(r.content)
    assert data["user"]["email"] == citizen.email
    assert len(data["bookings"]) == 1 and data["bookings"][0]["rules_version"] == 1
    assert AuditLog.objects.filter(action="account.export").exists()


def test_delete_account_anonymises_bookings(client, citizen, padel_a):
    b = create_booking(padel_a, next_slot(padel_a), citizen, rules_version=padel_a.current_rules())
    client.force_login(citizen)
    client.post("/conta/eliminar/", {"confirm": "on"})
    assert not User.objects.filter(pk=citizen.pk).exists()
    b.refresh_from_db()
    assert b.user is None and b.holder_name == ""
    assert Booking.objects.filter(pk=b.pk).exists()


def test_household_and_revocable_consents(client, citizen):
    client.force_login(citizen)
    from django.utils import timezone

    year = timezone.localdate().year - 9
    client.post("/conta/familia/", {"first_name": "Noa", "birth_year": year, "consent_data": "on"})
    dep = citizen.household.dependents.get()
    assert dep.has_consent(Consent.Kind.DATA) and not dep.has_consent(Consent.Kind.IMAGE)
    client.post(f"/conta/familia/{dep.pk}/consentimento/image/")
    assert dep.has_consent(Consent.Kind.IMAGE)
    client.post(f"/conta/familia/{dep.pk}/consentimento/image/")
    assert not dep.has_consent(Consent.Kind.IMAGE)
    assert dep.consents.filter(
        kind="image", revoked_at__isnull=False
    ).exists()  # queda rexistro con data


def test_adults_cannot_be_added_as_dependents(client, citizen):
    client.force_login(citizen)
    client.post(
        "/conta/familia/", {"first_name": "Adulta", "birth_year": 1980, "consent_data": "on"}
    )
    assert not hasattr(citizen, "household") or not citizen.household.dependents.exists()


def test_cannot_touch_others_dependents(client, citizen, outsider):
    from apps.accounts.models import Dependent, Household

    hh = Household.objects.create(responsible=outsider)
    dep = Dependent.objects.create(household=hh, first_name="X", birth_year=2018)
    client.force_login(citizen)
    assert client.post(f"/conta/familia/{dep.pk}/consentimento/image/").status_code == 404


def test_clave_with_another_session_keeps_next(client, muni_a, citizen):
    """v3: con outra sesión aberta, login() baleiraba a sesión e perdíase o destino."""
    client.force_login(citizen)
    client.get("/acceso/clave/?next=/c/concello-a/")
    state = client.session["identity_state"]
    r = client.post("/acceso/clave/volta/", {"state": state, "identity": "proba-1"})
    assert r.status_code == 302 and r["Location"] == "/c/concello-a/"


def test_clave_without_next_returns_to_last_visited_tenant(client, muni_a, muni_b):
    client.get("/acceso/")  # crea a sesión
    client.get("/c/concello-b/")
    client.get("/acceso/clave/")
    state = client.session["identity_state"]
    r = client.post("/acceso/clave/volta/", {"state": state, "identity": "proba-2"})
    assert r["Location"] == "/c/concello-b/app/"


def test_clave_reused_state_explains_and_keeps_next(client, muni_a):
    client.get("/acceso/clave/?next=/c/concello-a/")
    state = client.session["identity_state"]
    client.post("/acceso/clave/volta/", {"state": state, "identity": "proba-1"})
    client.logout()
    client.get("/acceso/clave/?next=/c/concello-a/")
    r = client.post("/acceso/clave/volta/", {"state": state + "x", "identity": "proba-1"})
    assert r["Location"] == "/acceso/?next=/c/concello-a/"
