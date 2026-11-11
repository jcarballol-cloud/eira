# SPDX-License-Identifier: EUPL-1.2
"""v1.5.1: declaración de accesibilidade (RD 1112/2018, art. 15) e ligazón no pé de todas as pantallas."""

import datetime as dt
import io
import json
import re
import zipfile

import pytest

from apps.accounts.models import Membership, Role, User
from apps.accounts.tests.test_v14 import _settings_form_data
from apps.tenants.accessibility import AXE_PAGES, AXE_SIZES, EVALUATED_ON

C = "/c/concello-a"
STATEMENT = f'href="{C}/accesibilidade/"'


@pytest.fixture
def monitor_a(muni_a):
    u = User.objects.create_user("monitora@example.org", display_name="Monitora")
    Membership.objects.create(user=u, municipality=muni_a, role=Role.MONITOR)
    return u


def footer(html):
    found = re.findall(r"<footer\b.*?</footer>", html, re.S)
    assert found, "a páxina non ten pé"
    return found[-1]


@pytest.mark.parametrize(
    "who,path,layout",
    [
        (None, f"{C}/", "public"),
        ("citizen", f"{C}/app/", "app"),
        ("operator_a", f"{C}/operario/", "app"),
        ("admin_a", f"{C}/xestion/", "desk"),
        ("monitor_a", f"{C}/monitor/", "tablet"),
    ],
)
def test_footer_links_statement_in_every_layout(client, request, muni_a, who, path, layout):
    if who:
        client.force_login(request.getfixturevalue(who))
    response = client.get(path, follow=True)
    assert response.status_code == 200
    html = response.content.decode()
    assert f"layout-{layout}" in html
    assert STATEMENT in footer(html)


def test_footer_without_municipality_links_global_statement(client, db):
    html = client.get("/").content.decode()
    assert 'href="/accesibilidade/"' in footer(html)


def test_global_statement_lists_each_municipality(client, muni_a, muni_b):
    html = client.get("/accesibilidade/").content.decode()
    assert "parcialmente conforme" in html
    assert STATEMENT in html and 'href="/c/concello-b/accesibilidade/"' in html


def test_statement_follows_official_model(client, muni_a):
    html = client.get(f"{C}/accesibilidade/").content.decode()
    for heading in (
        "Situación de cumprimento",
        "Contido non accesible",
        "Preparación desta declaración",
        "Observacións e datos de contacto",
        "Procedemento de aplicación",
    ):
        assert f">{heading}</h2>" in html
    assert "parcialmente conformes" in html
    assert f"en {AXE_PAGES} pantallas × {AXE_SIZES} tamaños" in html
    assert "revisión manual co teclado" in html
    assert "lectores de pantalla reais" in html  # o motivo da conformidade parcial


def test_contact_falls_back_to_municipality_contact(client, muni_a):
    muni_a.contact_email = "deportes@concello-a.example"
    muni_a.contact_phone = "981 000 000"
    muni_a.save()
    html = client.get(f"{C}/accesibilidade/").content.decode()
    assert "mailto:deportes@concello-a.example" in html and "981 000 000" in html
    assert "Presenta a reclamación no rexistro do concello." in html


def test_admin_edits_statement_contact_in_settings(client, admin_a, muni_a):
    client.force_login(admin_a)
    form = _settings_form_data(client)
    form.update(
        {
            "accessibility_unit": "Servizo de Deportes",
            "accessibility_email": "accesibilidade@concello-a.example",
            "accessibility_phone": "981 111 111",
            "accessibility_complaint_url": "https://sede.concello-a.example/",
            "accessibility_reviewed_on": "2026-12-01",
        }
    )
    response = client.post(f"{C}/xestion/configuracion/", form)
    assert response.status_code == 302
    muni_a.refresh_from_db()
    assert muni_a.accessibility_unit == "Servizo de Deportes"
    assert muni_a.accessibility_reviewed_on == dt.date(2026, 12, 1)
    client.logout()
    html = client.get(f"{C}/accesibilidade/").content.decode()
    assert "Servizo de Deportes" in html
    assert "mailto:accesibilidade@concello-a.example" in html and "981 111 111" in html
    assert 'href="https://sede.concello-a.example/"' in html
    assert EVALUATED_ON.year == 2026 and "2026" in html


def test_statement_in_spanish(client, muni_a):
    client.cookies["django_language"] = "es"
    html = client.get(f"{C}/accesibilidade/", HTTP_ACCEPT_LANGUAGE="es").content.decode()
    assert "Declaración de accesibilidad" in html and "Procedimiento de aplicación" in html


def test_statement_contact_in_portability_export(muni_a):
    from apps.tenants.portability import export_municipality

    muni_a.accessibility_unit = "Servizo de Deportes"
    muni_a.accessibility_reviewed_on = dt.date(2026, 12, 1)
    muni_a.save()
    raw = export_municipality(muni_a)
    raw = raw if isinstance(raw, bytes) else raw.getvalue()
    data = json.loads(zipfile.ZipFile(io.BytesIO(raw)).read("eira.json"))
    assert data["municipality"]["accessibility_unit"] == "Servizo de Deportes"
    assert data["municipality"]["accessibility_reviewed_on"] == "2026-12-01"
