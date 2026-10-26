# SPDX-License-Identifier: EUPL-1.2
"""Alta asistida de instalacións (plantillas) e alta de concello en tres pasos desde a deputación."""

import pytest

from apps.accounts.models import Membership, RegionMembership, User
from apps.facilities.models import Facility
from apps.tenants.models import Municipality, Region

pytestmark = pytest.mark.django_db


def test_facility_wizard_with_template(client, admin_a, muni_a):
    client.force_login(admin_a)
    assert "Piscina" in client.get("/c/concello-a/xestion/instalacions/nova/").content.decode()
    r = client.post(
        "/c/concello-a/xestion/instalacions/nova/",
        {
            "plantilla": "pool",
            "name": "Piscina nova",
            "kind": "pool",
            "capacity": 20,
            "slot_minutes": 60,
            "access_level": 3,
            "indoor": "on",
            "lighting": "on",
        },
    )
    f = Facility.objects.get(name="Piscina nova")
    assert r["Location"].endswith(f"/xestion/instalacions/{f.pk}/revisar/")
    assert not f.is_published
    assert f.opening_hours.count() == 6 and f.tariffs.count() == 4 and f.current_rules()
    plan = f.maintenance_plans.exclude(tasks__kind="cleaning").get()
    assert plan.tasks.count() == 3 and f.lock.kind == "connected"
    # v1.1: a plantilla da piscina trae tamén as súas zonas de limpeza
    assert f.cleaning_zones.count() == 3
    client.post(f"/c/concello-a/xestion/instalacions/{f.pk}/revisar/")
    f.refresh_from_db()
    assert f.is_published


def test_level1_requires_key_holder(client, admin_a, muni_a):
    client.force_login(admin_a)
    client.post(
        "/c/concello-a/xestion/instalacions/nova/",
        {
            "plantilla": "sports_hall",
            "name": "Pavillón sen chave",
            "kind": "sports_hall",
            "capacity": 1,
            "slot_minutes": 60,
            "access_level": 1,
        },
    )
    assert not Facility.objects.filter(name="Pavillón sen chave").exists()


def test_municipality_wizard_six_steps_with_invitation(client, region):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.integrations.models import DevMail

    dep = User.objects.create_user("dep@example.org")
    RegionMembership.objects.create(user=dep, region=region)
    client.force_login(dep)
    url = "/rexion/proba/novo-concello/"
    # Non se pode saltar pasos
    assert client.get(url + "?paso=4")["Location"].endswith("?paso=1")
    steps = [
        {"name": "Concello Novo", "slug": "novo", "population": 900, "postcodes": "15990"},
        {
            "admin_name": "Persoa Responsable",
            "admin_email": "alcaldia@novo.example",
            "admin_phone": "981 111 111",
        },
        {
            "modules": ["bookings", "access", "incidents"],
            "cancellation_hours": 12,
            "max_advance_days": 10,
        },
        {
            "accent_color": "#2E6A4F",
            "coat_of_arms": SimpleUploadedFile("escudo.png", _png(), content_type="image/png"),
        },
        {"template": "gym", "facility_name": "Ximnasio da Vila", "parish": "A Vila"},
    ]
    for n, data in enumerate(steps, 1):
        r = client.post(url, {"step": n, **data})
        assert r.status_code == 302 and r["Location"].endswith(f"?paso={n + 1}"), (
            n,
            r.context and r.context["form"].errors,
        )
    html = client.get(url + "?paso=6").content.decode()
    assert "Persoa Responsable" in html and "Invitación para xestionar" in html
    r = client.post(url, {"step": 6, "send_invitation": "on"})
    m = Municipality.objects.get(slug="novo")
    assert m.region == region and m.cancellation_hours == 12 and m.postcodes == "15990"
    assert m.module_enabled("bookings") and not m.module_enabled("activities")
    assert m.coat_of_arms and m.contact_phone == "981 111 111"
    admin = Membership.objects.get(municipality=m, role="admin").user
    assert admin.email == "alcaldia@novo.example" and admin.display_name == "Persoa Responsable"
    f = Facility.objects.get(municipality=m)
    assert f.name == "Ximnasio da Vila" and f.parish.name == "A Vila" and not f.is_published
    mail = DevMail.objects.get(to="alcaldia@novo.example")
    assert "/acceso/?next=/c/novo/xestion/" in mail.body
    assert r["Location"] == "/c/novo/xestion/"


def test_wizard_rejects_low_contrast_colour(client, region):
    dep = User.objects.create_user("dep@example.org")
    RegionMembership.objects.create(user=dep, region=region)
    client.force_login(dep)
    url = "/rexion/proba/novo-concello/"
    client.post(url, {"step": 1, "name": "X", "slug": "x"})
    client.post(url, {"step": 2, "admin_name": "A", "admin_email": "a@x.example"})
    client.post(url, {"step": 3, "cancellation_hours": 1, "max_advance_days": 1})
    r = client.post(url, {"step": 4, "accent_color": "#F5E663"})
    assert r.status_code == 200 and "pouco contraste" in r.content.decode()


def test_region_dashboard_compares_and_resends_invitation(client, region, muni_a, muni_b, admin_a):
    from apps.integrations.models import DevMail

    dep = User.objects.create_user("dep@example.org")
    RegionMembership.objects.create(user=dep, region=region)
    client.force_login(dep)
    html = client.get("/rexion/proba/").content.decode()
    assert "Satisfacción" in html and "Concello A" in html and "Reenviar invitación" in html
    assert "Concello B" in client.get("/rexion/proba/?csv=1").content.decode()
    client.post("/rexion/proba/concello/concello-a/reenviar-invitacion/")
    assert DevMail.objects.filter(to=admin_a.email).exists()
    # Un concello doutra rede non
    other = Region.objects.create(name="Outra", slug="outra")
    Municipality.objects.create(name="Alleo", slug="alleo", region=other)
    assert client.post("/rexion/proba/concello/alleo/reenviar-invitacion/").status_code == 404


def _png():
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (46, 106, 79)).save(buf, "PNG")
    return buf.getvalue()
