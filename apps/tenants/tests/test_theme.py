# SPDX-License-Identifier: EUPL-1.2
"""v4.1: botón «Día / Noite» da demo (tema na sesión), catálogo de ilustracións e configuración."""

import pytest

from apps.tenants.prefs import THEME_KEY

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


def test_theme_saved_in_session_and_rendered(client, citizen):
    client.force_login(citizen)
    html = client.get(f"{C}/app/").content.decode()
    assert "data-theme=" not in html.split("<head>")[0]  # sen escoller: segue o sistema
    assert 'action="/dev/tema/"' in html and 'aria-pressed="false"' in html
    r = client.post("/dev/tema/", {"tema": "dark", "next": f"{C}/app/"})
    assert r.status_code == 302 and r["Location"] == f"{C}/app/"
    assert client.session[THEME_KEY] == "dark"
    head = client.get(f"{C}/app/").content.decode().split("<head>")[0]
    assert 'data-theme="dark"' in head and "theme-dark" in head
    # Con JS: 204 e sen redirección; «system» borra a escolla
    assert client.post("/dev/tema/", {"tema": "light"}, HTTP_X_EIRA_THEME="1").status_code == 204
    assert client.session[THEME_KEY] == "light"
    client.post("/dev/tema/", {"tema": "system"}, HTTP_X_EIRA_THEME="1")
    assert THEME_KEY not in client.session


def test_theme_next_must_be_local(client, citizen):
    client.force_login(citizen)
    r = client.post("/dev/tema/", {"tema": "dark", "next": "https://example.com/"})
    assert not r["Location"].startswith("https://example.com")


def test_illustrations_catalog(client):
    html = client.get("/dev/ilustracions/").content.decode()
    for name in (
        "cabecera-eira-",
        "cabecera-eira-noite-",
        "baleiro-reservas",
        "baleiro-avisos",
        "baleiro-mantemento",
        "eira-icono-baleiro",
    ):
        assert name in html
    assert "operario/?dia=manha" in html and 'name="tema" value="dark"' in html


def test_settings_padron_note_once_and_side_column(client, admin_a):
    client.force_login(admin_a)
    html = client.get(f"{C}/xestion/configuracion/").content.decode()
    assert html.count("as altas automáticas usan o padrón cargado en CSV") == 1
    assert 'id="cfg-modulos"' in html and "settings-section--mapa" in html
    # Contacto do DPD nunha caixa de varias liñas (non se corta)
    assert '<textarea name="dpo_contact"' in html
