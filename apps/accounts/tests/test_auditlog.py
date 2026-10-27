# SPDX-License-Identifier: EUPL-1.2
"""v1.3 · C: rexistro de auditoría (só administración e DPD) e accións sensibles que se rexistran."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.auditlog import category_of
from apps.accounts.models import AuditLog, Membership, RegionMembership, Role, User, audit
from apps.tenants.models import SupportAccess

pytestmark = pytest.mark.django_db
C = "/c/concello-a"
URL = f"{C}/xestion/privacidade/auditoria/"


@pytest.fixture
def dpo_a(muni_a):
    u = User.objects.create_user("dpd-a@example.org", display_name="DPD")
    Membership.objects.create(user=u, municipality=muni_a, role=Role.DPO)
    return u


def test_admin_and_dpo_see_it(client, admin_a, dpo_a, muni_a):
    audit("facility.tariffs", admin_a, muni_a, admin_a)
    for user in (admin_a, dpo_a):
        client.force_login(user)
        r = client.get(URL)
        assert r.status_code == 200 and "Cambio de tarifas" in r.content.decode()


@pytest.mark.parametrize("role", [Role.CITIZEN, Role.MAINTENANCE, Role.MONITOR, Role.CLEANING])
def test_other_roles_cannot(client, muni_a, role):
    u = User.objects.create_user(f"{role}@example.org")
    Membership.objects.create(user=u, municipality=muni_a, role=role)
    client.force_login(u)
    assert client.get(URL).status_code == 403


def test_region_cannot_even_with_support_access(client, region, muni_a, admin_a):
    u = User.objects.create_user("dep@example.org")
    RegionMembership.objects.create(user=u, region=region)
    SupportAccess.objects.create(
        municipality=muni_a,
        region=region,
        reason="Proba",
        granted_by=admin_a,
        expires_at=timezone.now() + dt.timedelta(hours=2),
    )
    client.force_login(u)
    assert client.get(URL).status_code == 403


def test_only_own_council(client, admin_a, muni_a, muni_b):
    audit("breach.save", admin_a, muni_b)
    client.force_login(admin_a)
    assert "Brecha rexistrada" not in client.get(URL).content.decode()


def test_filters_by_category_and_date(client, admin_a, muni_a):
    audit("facility.tariffs", admin_a, muni_a)
    audit("accident.register", admin_a, muni_a)
    old = audit("support.grant", admin_a, muni_a)
    AuditLog.objects.filter(pk=old.pk).update(at=timezone.now() - dt.timedelta(days=40))
    client.force_login(admin_a)
    html = client.get(URL + "?categoria=accidentes").content.decode()
    assert "Accidente rexistrado" in html and "Cambio de tarifas" not in html
    since = (timezone.localdate() - dt.timedelta(days=7)).isoformat()
    html = client.get(URL + f"?desde={since}").content.decode()
    assert "Acceso de soporte autorizado" not in html and "Cambio de tarifas" in html


def test_categories_cover_the_sensitive_actions():
    assert category_of("facility.tariffs") == "tarifas"
    assert category_of("pass_type.create") == "tarifas"
    assert category_of("tenant.staff_add") == "permisos"
    assert category_of("tenant.staff_remove") == "permisos"
    assert category_of("export.download") == "exportacions"
    assert category_of("tenant.export") == "exportacions"
    assert category_of("support.view") == "soporte"
    assert category_of("breach.save") == "brechas"
    assert category_of("accident.register") == "accidentes"
    assert category_of("2fa.reset") == "permisos"
    assert category_of("2fa.enable") == "contas"


def test_staff_logins_without_council_are_shown(client, admin_a, muni_a, citizen):
    audit("auth.login", admin_a, method="email_code")
    audit("auth.login", citizen, method="email_code")  # a veciñanza non aparece
    client.force_login(admin_a)
    html = client.get(URL + "?categoria=contas").content.decode()
    assert html.count("Inicio de sesión") == 1


def test_staff_role_removal_is_audited(client, admin_a, operator_a, muni_a):
    m = Membership.objects.get(user=operator_a, municipality=muni_a)
    client.force_login(admin_a)
    client.post(f"{C}/xestion/persoal/", {"remove": m.pk})
    entry = AuditLog.objects.get(action="tenant.staff_remove")
    assert entry.municipality == muni_a and entry.detail["role"] == Role.MAINTENANCE


def test_staff_downloads_are_audited(client, admin_a, muni_a, citizen):
    client.force_login(admin_a)
    r = client.get(f"{C}/xestion/indicadores/?csv=ocupacion")
    assert r.status_code == 200
    entry = AuditLog.objects.get(action="export.download")
    assert entry.actor == admin_a and entry.municipality == muni_a
    assert entry.detail["file"] == "ocupacion.csv"
    # A descarga dos datos propios dunha veciña non se duplica como exportación do persoal
    client.force_login(citizen)
    client.get("/conta/os-meus-datos.json")
    assert AuditLog.objects.filter(action="export.download").count() == 1


def test_audit_csv_is_itself_audited_once(client, admin_a, muni_a):
    audit("facility.tariffs", admin_a, muni_a)
    client.force_login(admin_a)
    r = client.get(URL + "?formato=csv")
    body = r.content.decode("utf-8-sig")
    assert r.status_code == 200 and "facility.tariffs" in body
    assert AuditLog.objects.filter(action="audit.export").count() == 1
    assert not AuditLog.objects.filter(action="export.download").exists()


def test_dpia_summary_linked_from_custody(client, muni_a):
    html = client.get(f"{C}/privacidade/datos/").content.decode()
    assert f"{C}/privacidade/avaliacion-impacto/" in html
    html = client.get(f"{C}/privacidade/avaliacion-impacto/").content.decode()
    for words in ("Rexistro de accidentes", "texto libre", "10 persoas", "HMAC", "Dobre factor"):
        assert words in html
