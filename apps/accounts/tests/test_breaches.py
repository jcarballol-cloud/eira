# SPDX-License-Identifier: EUPL-1.2
"""v5 · F: rexistro de brechas (só administración do concello e DPD) e «Quen custodia os teus datos»."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.custody import DETAILS, custody_rows, matrix_rows
from apps.accounts.models import DataBreach, Membership, RegionMembership, Role, User
from apps.tenants.models import SupportAccess

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


@pytest.fixture
def dpo_a(muni_a):
    u = User.objects.create_user("dpd-a@example.org", display_name="DPD")
    Membership.objects.create(user=u, municipality=muni_a, role=Role.DPO)
    return u


@pytest.fixture
def breach(muni_a):
    return DataBreach.objects.create(
        municipality=muni_a,
        detected_at=timezone.now() - dt.timedelta(hours=10),
        description="Correo enviado con destinatarios á vista",
        data_affected="Correos electrónicos",
        people_affected="23 persoas",
        risk=DataBreach.Risk.RISK,
    )


def test_admin_and_dpo_can_use_the_register(client, admin_a, dpo_a, breach):
    for user in (admin_a, dpo_a):
        client.force_login(user)
        assert client.get(f"{C}/xestion/privacidade/brechas/").status_code == 200
        assert client.get(f"{C}/xestion/privacidade/brechas/{breach.pk}/").status_code == 200
        r = client.get(f"{C}/xestion/privacidade/brechas/{breach.pk}/comunicacion/")
        assert r.status_code == 200 and "www.aepd.es" in r.content.decode()


@pytest.mark.parametrize("role", [Role.CITIZEN, Role.MAINTENANCE, Role.MONITOR])
def test_other_roles_get_403(client, muni_a, breach, role):
    u = User.objects.create_user(f"{role}@example.org")
    Membership.objects.create(user=u, municipality=muni_a, role=role)
    client.force_login(u)
    assert client.get(f"{C}/xestion/privacidade/brechas/").status_code == 403
    assert client.get(f"{C}/xestion/privacidade/brechas/{breach.pk}/").status_code == 403


def test_region_never_sees_it_even_with_support_access(client, region, muni_a, breach):
    dep = User.objects.create_user("dep@example.org")
    RegionMembership.objects.create(user=dep, region=region)
    SupportAccess.objects.create(
        municipality=muni_a,
        region=region,
        reason="proba",
        expires_at=timezone.now() + dt.timedelta(hours=2),
    )
    client.force_login(dep)
    assert client.get(f"{C}/xestion/privacidade/brechas/").status_code == 403


def test_admin_of_another_town_cannot_see_it(client, admin_b, breach):
    client.force_login(admin_b)
    assert client.get(f"{C}/xestion/privacidade/brechas/").status_code == 403
    client.force_login(admin_b)
    assert client.get(f"/c/concello-b/xestion/privacidade/brechas/{breach.pk}/").status_code == 404


def test_anonymous_is_sent_to_login(client, breach):
    r = client.get(f"{C}/xestion/privacidade/brechas/")
    assert r.status_code == 302 and "/acceso/" in r["Location"]


def test_risk_requires_aepd_or_a_reason_and_72h_deadline(client, admin_a):
    client.force_login(admin_a)
    detected = timezone.localtime() - dt.timedelta(hours=80)
    data = {
        "detected_at": detected.strftime("%Y-%m-%dT%H:%M"),
        "description": "Portátil perdido coa exportación",
        "data_affected": "Nomes e reservas",
        "people_affected": "120",
        "risk": "high",
        "status": "open",
    }
    r = client.post(f"{C}/xestion/privacidade/brechas/nova/", data)
    assert r.status_code == 200 and not DataBreach.objects.exists()
    data.update(
        {"aepd_notified": "on", "aepd_notified_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M")}
    )
    r = client.post(f"{C}/xestion/privacidade/brechas/nova/", data)
    b = DataBreach.objects.get()
    assert r.status_code == 302 and b.created_by == admin_a
    assert b.aepd_on_time is False  # notificada despois das 72 h
    html = client.get(f"{C}/xestion/privacidade/brechas/").content.decode()
    assert "Fóra de prazo" in html


def test_custody_page_is_generated_from_the_matrix(client, citizen):
    rows = matrix_rows()
    assert len(rows) >= 13
    missing = [dato for dato, _s, _r in rows if dato not in DETAILS]
    assert not missing, missing  # cada fila da matriz ten explicación sinxela
    custody = {r["data"]: r for r in custody_rows()}
    who = dict(custody["Correo e teléfono"]["recipients"])
    assert who["Concello"] == "reservas, altas" and "Operario/a" not in who
    # Pública e na app
    html = client.get(f"{C}/privacidade/datos/").content.decode()
    assert (
        "Quen custodia os teus datos" in html
        and "Para que" in html
        and "Como pedir que se borre" in html
    )
    client.force_login(citizen)
    assert client.get(f"{C}/privacidade/datos/").status_code == 200
