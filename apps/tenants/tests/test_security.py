# SPDX-License-Identifier: EUPL-1.2
import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

pytestmark = pytest.mark.django_db

TEMPLATES = Path(settings.BASE_DIR) / "templates"


def test_security_headers(client, padel_a):
    r = client.get("/c/concello-a/")
    csp = r["Content-Security-Policy"]
    assert "script-src 'self'" in csp and "unsafe-inline" not in csp
    assert "frame-ancestors 'none'" in csp
    assert r["X-Frame-Options"] == "DENY"
    assert r["X-Content-Type-Options"] == "nosniff"
    assert "Permissions-Policy" in r


def test_no_inline_scripts_or_styles_in_templates():
    """A CSP sen unsafe-inline obriga a non ter <script> nin style= en liña."""
    for path in TEMPLATES.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(
            r"<script(?![^>]*\bsrc=)(?![^>]*type=\"application/json\")[^>]*>", text
        ), path
        assert " style=" not in text, path
        assert "hx-on" not in text, path


def test_csrf_enforced_on_login(db):
    c = Client(enforce_csrf_checks=True)
    assert c.post("/acceso/", {"email": "a@example.org"}).status_code == 403


def test_lang_attribute_and_skip_link(client, padel_a):
    html = client.get("/c/concello-a/").content.decode()
    assert '<html lang="gl"' in html
    assert 'href="#main"' in html and 'id="main"' in html


def test_spanish_lang(client, padel_a):
    client.cookies["django_language"] = "es"  # escollido no selector (o navegador non conta)
    html = client.get("/c/concello-a/").content.decode()
    assert '<html lang="es"' in html


def test_dev_tools_disabled_in_production_settings():
    """Sen EIRA_DEMO_TOOLS as rutas /dev/ non se rexistran (comprobado no URLconf)."""
    import importlib

    import eira.urls

    settings_demo = settings.EIRA_DEMO_TOOLS
    try:
        settings.EIRA_DEMO_TOOLS = False
        mod = importlib.reload(eira.urls)
        assert not any(str(p.pattern).startswith("dev/") for p in mod.urlpatterns)
    finally:
        settings.EIRA_DEMO_TOOLS = settings_demo
        importlib.reload(eira.urls)


def test_audit_log_on_sensitive_actions(client, admin_a, padel_a):
    from apps.accounts.models import AuditLog

    client.force_login(admin_a)
    client.post(
        f"/c/concello-a/xestion/instalacions/{padel_a.pk}/normas/", {"text": "- Nova norma"}
    )
    assert AuditLog.objects.filter(action="facility.rules", actor=admin_a).exists()


def test_tile_provider_per_municipality_goes_to_csp(client, padel_a):
    from apps.tenants.models import tile_settings

    assert tile_settings(None)["origin"] == "https://tile.openstreetmap.org"
    muni = padel_a.municipality
    muni.tile_url = "https://{s}.teselas.deputacion.example/{z}/{x}/{y}.png"
    muni.tile_attribution = "Deputación de proba · OSM"
    muni.save()
    assert tile_settings(muni)["origin"] == "https://*.teselas.deputacion.example"
    r = client.get("/c/concello-a/?vista=mapa")
    assert "https://*.teselas.deputacion.example" in r["Content-Security-Policy"]
    assert "de proba" in r.content.decode()  # o JSON do mapa escapa os non ASCII
    assert r["Referrer-Policy"] == "same-origin"  # a política global non se relaxa
