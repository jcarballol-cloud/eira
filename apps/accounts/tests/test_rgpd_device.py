# SPDX-License-Identifier: EUPL-1.2
"""Auditoría RXPD (14/11/2026): ao saír ou cambiar de persoa non quedan páxinas con datos
persoais na caché do dispositivo (o E2E comproba a Cache API)."""

from django.urls import reverse


def test_logout_clears_the_browser_cache(client, citizen):
    client.force_login(citizen)
    resp = client.post(reverse("accounts:logout"))
    assert resp.status_code == 302 and resp["Clear-Site-Data"] == '"cache"'


def test_pages_say_whose_cache_it_is(client, citizen, muni_a):
    html = client.get("/").content.decode()
    assert 'data-cache-owner=""' in html
    client.force_login(citizen)
    html = client.get("/c/concello-a/app/").content.decode()
    assert f'data-cache-owner="{citizen.pk}"' in html


def test_eira_js_forgets_cached_pages_of_someone_else():
    from pathlib import Path

    from django.conf import settings

    js = (Path(settings.BASE_DIR) / "static/js/eira.js").read_text(encoding="utf-8")
    assert "forgetOtherPeoplesPages();" in js and 'indexOf("eira-pages-")' in js
