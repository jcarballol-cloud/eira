# SPDX-License-Identifier: EUPL-1.2
"""Auditoría RXPD (14/11/2026): o mapa non pide teselas ata que a persoa pulsa «Ver mapa», cun
aviso dunha liña sobre o servidor de teselas e a IP (o E2E comproba as peticións)."""

from apps.facilities.views import tile_provider_name


def test_map_waits_for_the_button_and_warns_about_the_ip(client, padel_a):
    html = client.get("/c/concello-a/?vista=mapa").content.decode()
    assert "Ver mapa" in html and "data-map-load" in html
    assert (
        "O mapa carga imaxes de OpenStreetMap: ese servidor verá o enderezo IP do teu navegador."
        in html
    )
    # O contedor do mapa empeza oculto: sen JS nin pulsar o botón non se carga nada
    assert 'data-map="facilities-geo" role="region" tabindex="-1"' in html
    assert html.count("hidden></div>") >= 1


def test_own_tile_server_is_named_in_the_warning(client, padel_a):
    muni = padel_a.municipality
    muni.tile_url = "https://{s}.teselas.deputacion.example/{z}/{x}/{y}.png"
    muni.save()
    html = client.get("/c/concello-a/?vista=mapa").content.decode()
    assert "O mapa carga imaxes de teselas.deputacion.example" in html


def test_provider_names():
    assert tile_provider_name("https://tile.openstreetmap.org/{z}/{x}/{y}.png") == "OpenStreetMap"
    assert tile_provider_name("https://mapas.example.org/{z}/{x}/{y}.png") == "mapas.example.org"


def test_map_js_only_loads_on_click():
    from pathlib import Path

    from django.conf import settings

    js = (Path(settings.BASE_DIR) / "static/js/map.js").read_text(encoding="utf-8")
    assert 'addEventListener("click"' in js and "init(el)" in js
    assert 'document.addEventListener("DOMContentLoaded", setup)' in js


def test_privacy_page_explains_transfers(client, muni_a):
    html = client.get("/c/concello-a/privacidade/").content.decode()
    assert "Os teus datos non saen da Unión Europea, salvo se vinculas Telegram" in html
    assert "só se carga se pulsas «Ver mapa»" in html
