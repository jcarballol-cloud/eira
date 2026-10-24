# SPDX-License-Identifier: EUPL-1.2
"""v4.1: en produción os estáticos levan hash no nome (manifesto). Todas as referencias deben
existir no manifesto (senón a páxina falla) e o service worker debe precachear eses nomes."""

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.utils.functional import empty

from apps.tenants import assets

pytestmark = pytest.mark.django_db

MANIFEST = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
}


@pytest.fixture
def manifest(tmp_path):
    with override_settings(STATIC_ROOT=tmp_path, STORAGES=MANIFEST):
        from django.contrib.staticfiles.storage import staticfiles_storage

        staticfiles_storage._wrapped = empty  # recrear o almacenamento coa configuración nova
        call_command("collectstatic", "--noinput", "-v0")
        yield
    from django.contrib.staticfiles.storage import staticfiles_storage

    staticfiles_storage._wrapped = empty


def test_pages_render_with_hashed_static_names(client, manifest, muni_a, padel_a):
    for url in ("/", "/c/concello-a/", "/creditos/", "/saude/", "/sw.js", "/manifest.webmanifest"):
        r = client.get(url)
        assert r.status_code == 200, url
    html = client.get("/").content.decode()
    assert "/static/css/eira.css" not in html  # vai co hash no nome
    sw = client.get("/sw.js").content.decode()
    assert assets.asset_url("css/eira.css") in sw and "?v=" not in sw


def test_dev_urls_carry_content_hash():
    url = assets.asset_url("css/eira.css")
    assert url.startswith("/static/css/eira.css?v=") and len(url.split("?v=")[1]) == 10
    assert assets.version().startswith("eira-")
