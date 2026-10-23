# SPDX-License-Identifier: EUPL-1.2
"""v3: a deputación só ve datos agregados; os persoais, con acceso de soporte do concello (24 h)."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import AuditLog, RegionMembership, User
from apps.notifications.models import Notification
from apps.tenants.models import SupportAccess

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


@pytest.fixture
def dep(region, muni_a):
    u = User.objects.create_user("deputacion@example.org")
    RegionMembership.objects.create(user=u, region=region)
    return u


def grant(client, admin_a, reason="Revisar cobros"):
    client.force_login(admin_a)
    return client.post(f"{C}/xestion/persoal/", {"action": "support_grant", "reason": reason})


def test_aggregate_always_personal_needs_support_then_expires(client, dep, admin_a, muni_a):
    client.force_login(dep)
    assert client.get(f"{C}/xestion/indicadores/").status_code == 200  # agregados: sempre
    r = client.get(f"{C}/xestion/")
    assert r.status_code == 403 and "acceso de soporte" in r.content.decode()
    # o concello autoriza
    grant(client, admin_a)
    access = SupportAccess.objects.get()
    assert access.expires_at - access.granted_at == dt.timedelta(hours=24)
    assert AuditLog.objects.filter(action="support.grant").exists()
    client.force_login(dep)
    r = client.get(f"{C}/xestion/")
    assert r.status_code == 200 and "acceso de soporte ata" in r.content.decode()
    log = AuditLog.objects.filter(action="support.view", actor=dep)
    assert log.count() == 1 and log.first().detail["path"] == f"{C}/xestion/"
    # aviso ao concello no primeiro uso (unha soa vez)
    client.get(f"{C}/xestion/axenda/")
    assert (
        Notification.objects.filter(user=admin_a, title__icontains="acceso de soporte").count() == 1
    )
    # caduca: 403 de novo
    SupportAccess.objects.update(expires_at=timezone.now() - dt.timedelta(seconds=1))
    assert client.get(f"{C}/xestion/").status_code == 403


def test_revoke_and_still_read_only(client, dep, admin_a, padel_a):
    grant(client, admin_a)
    client.force_login(dep)
    assert client.get(f"{C}/xestion/").status_code == 200
    assert client.post(f"{C}/xestion/peches/alerta/").status_code == 403  # só lectura
    # a deputación non se pode autorizar a si mesma
    assert (
        client.post(f"{C}/xestion/persoal/", {"action": "support_grant", "reason": "x"}).status_code
        == 403
    )
    client.force_login(admin_a)
    client.post(f"{C}/xestion/persoal/", {"action": "support_revoke"})
    client.force_login(dep)
    assert client.get(f"{C}/xestion/").status_code == 403


def test_access_is_per_municipality(client, dep, admin_a, muni_b):
    grant(client, admin_a)
    client.force_login(dep)
    assert client.get("/c/concello-b/xestion/").status_code == 403


def test_region_can_request_access_and_concello_is_notified(client, dep, admin_a):
    client.force_login(dep)
    client.post(
        "/rexion/proba/concello/concello-a/solicitar-soporte/", {"reason": "Incidencia de cobro"}
    )
    n = Notification.objects.get(user=admin_a)
    assert "solicita" in n.title and "Incidencia de cobro" in n.body
    assert not SupportAccess.objects.exists()  # solicitar non dá acceso


def test_personal_export_needs_support(client, dep, admin_a):
    client.force_login(dep)
    assert client.get(f"{C}/xestion/portabilidade/exportar.zip").status_code == 403
    grant(client, admin_a)
    client.force_login(dep)
    assert client.get(f"{C}/xestion/portabilidade/exportar.zip").status_code == 200
