# SPDX-License-Identifier: EUPL-1.2
"""Fase 5: as teselas do mapa cargan (200) co Referer correcto e a CSP permite a súa orixe.
Auditoría RXPD: e só despois de pulsar «Ver mapa»; antes non se pide ningunha.

Necesita conexión a internet (servidor de teselas de OpenStreetMap)."""

from pathlib import Path

import pytest
from django.conf import settings

from .conftest import DESKTOP

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]
OUT = Path(settings.BASE_DIR) / "docs" / "capturas" / "v2"


def test_osm_tiles_load_with_referer(new_page, base):
    page = new_page(viewport=DESKTOP)
    tiles = []
    page.on("response", lambda r: tiles.append(r) if "tile.openstreetmap.org" in r.url else None)
    violations = []
    page.on(
        "console",
        lambda m: violations.append(m.text) if "Content Security Policy" in m.text else None,
    )
    page.goto(base + "/c/vilardeiras/?vista=mapa")
    page.wait_for_load_state("networkidle")
    assert tiles == [], "pediuse unha tesela antes de pulsar «Ver mapa»"
    assert page.locator("#map").is_hidden()
    assert "OpenStreetMap" in page.locator("#map-note").inner_text()
    page.get_by_role("button", name="Ver mapa").click()
    assert page.evaluate("document.activeElement.id") == "map"
    page.wait_for_selector(".leaflet-tile-loaded", timeout=20000)
    page.wait_for_timeout(1500)
    statuses = [t.status for t in tiles]
    assert statuses, "non se pediu ningunha tesela"
    assert 403 not in statuses and statuses.count(200) >= 1, statuses
    referer = tiles[0].request.headers.get("referer", "")
    assert referer.startswith(base) and "/c/vilardeiras" not in referer  # só a orixe, sen a ruta
    assert not violations, violations
    assert "OpenStreetMap" in page.locator(".leaflet-control-attribution").inner_text()
    OUT.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT / "mapa-teselas.png"))


def test_no_tile_request_without_clicking(new_page, base):
    """Sen rede externa: abórtanse as teselas e só se mira que non se piden antes do botón."""
    page = new_page(viewport=DESKTOP)
    asked = []

    def block(route):
        asked.append(route.request.url)
        route.abort()

    page.route(
        "**/*", lambda r: block(r) if "openstreetmap.org" in r.request.url else r.continue_()
    )
    page.goto(base + "/c/vilardeiras/?vista=mapa")
    page.wait_for_load_state("networkidle")
    assert asked == []
    page.reload()
    page.wait_for_load_state("networkidle")
    assert asked == []  # non se lembra: cada visita pide pulsar
    page.keyboard.press("Tab")  # o botón é accesible co teclado
    page.get_by_role("button", name="Ver mapa").press("Enter")
    page.wait_for_function("() => document.querySelector('.leaflet-tile') !== null")
    assert asked, "ao pulsar «Ver mapa» non se pediu ningunha tesela"
