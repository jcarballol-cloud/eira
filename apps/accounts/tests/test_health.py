# SPDX-License-Identifier: EUPL-1.2
"""v2 F6: datos de saúde. No dispositivo por defecto; na conta só con consentimento art. 9;
nunca visibles para o persoal, nas exportacións do concello nin no observatorio."""

import datetime as dt
import io
import zipfile

import pytest
from django.contrib import admin
from django.utils import timezone

from apps.accounts.models import AuditLog, HealthProfile
from apps.bookings.models import Booking

pytestmark = pytest.mark.django_db
WEIGHT = "123.4"


def store(client, consent=True):
    data = {"age": "41", "weight": WEIGHT, "minutes": "90"}
    if consent:
        data["consent"] = "1"
    return client.post("/saude/", data)


def test_health_page_works_without_account_and_sends_nothing(client):
    html = client.get("/saude/").content.decode()
    assert 'id="health-form"' in html and "health-engine.js" in html
    # o formulario local non ten name nin action: non hai nada que enviar
    start = html.index('<form id="health-form"')
    form = html[start : html.index("</form>", start)]
    assert 'name="' not in form and "action=" not in form


def test_store_requires_explicit_consent(client, citizen):
    client.force_login(citizen)
    r = store(client, consent=False)
    assert r.status_code == 200 and not HealthProfile.objects.exists()
    store(client)
    hp = HealthProfile.objects.get(user=citizen)
    assert (
        str(hp.weight_kg) == WEIGHT
        and hp.age == 41
        and hp.consent_version == HealthProfile.CONSENT_VERSION
    )
    assert AuditLog.objects.filter(action="health.store", actor=citizen).exists()
    client.post("/saude/", {"action": "forget"})
    assert not HealthProfile.objects.exists()


def test_owner_sees_profile_in_booking_but_staff_never(
    client, citizen, admin_a, padel_a, operator_a
):
    client.force_login(citizen)
    store(client)
    start = timezone.now() + dt.timedelta(days=1)
    b = Booking.objects.create(
        municipality=padel_a.municipality,
        facility=padel_a,
        user=citizen,
        start=start,
        end=start + dt.timedelta(hours=1),
        status=Booking.Status.CONFIRMED,
    )
    html = client.get(f"/c/concello-a/reservas/{b.pk}/").content.decode()
    assert 'id="h-account"' in html and WEIGHT in html and "data-health-booking" in html
    client.force_login(admin_a)
    for url in [
        f"/c/concello-a/xestion/reservas/{b.pk}/",
        "/c/concello-a/xestion/",
        "/c/concello-a/xestion/axenda/",
        "/c/concello-a/actividades/observatorio/",
    ]:
        page = client.get(url).content.decode()
        assert WEIGHT not in page and 'id="h-account"' not in page, url
    # exportación íntegra do concello (portabilidade)
    raw = client.get("/c/concello-a/xestion/portabilidade/exportar.zip").content
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        blob = " ".join(zf.read(n).decode("utf-8", "ignore") for n in zf.namelist())
    assert WEIGHT not in blob and "weight_kg" not in blob and "health_profile" not in blob


def test_health_not_in_admin_site():
    assert not admin.site.is_registered(HealthProfile)


def test_personal_export_includes_own_health(client, citizen):
    client.force_login(citizen)
    assert client.get("/conta/os-meus-datos.json").json()["health"] is None
    store(client)
    data = client.get("/conta/os-meus-datos.json").json()
    assert data["health"]["weight"] == float(WEIGHT) and data["health"]["consent_at"]


def test_account_deletion_removes_health(client, citizen):
    client.force_login(citizen)
    store(client)
    citizen.delete()
    assert not HealthProfile.objects.exists()
