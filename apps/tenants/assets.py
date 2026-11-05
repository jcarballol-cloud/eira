# SPDX-License-Identifier: EUPL-1.2
"""Versionado dos estáticos (v4.1).

En produción úsase `CompressedManifestStaticFilesStorage` (nomes con hash). En desenvolvemento e
nos tests os ficheiros sérvense co seu nome, así que `{% asset %}` engade `?v=<hash do contido>`:
cando cambia o CSS cambia o URL e ningunha caché (do navegador ou do service worker) serve o vello.
A versión do service worker depende destes hashes, polo que cada cambio de CSS/JS crea cachés novas
e borra as antigas.
"""

import hashlib

from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

# Ficheiros que o service worker garda para funcionar sen conexión
PRECACHE = [
    "css/eira.css",
    "js/eira.js",
    "js/health.js",
    "js/health-engine.js",
    "js/listen-core.js",  # v1.5 · A: «Escoitar» sen conexión
    "js/listen.js",
    "vendor/htmx/htmx.min.js",
    "img/eira.svg",
    "img/icons.svg",
]
_cache = {}


def hashed_storage():
    return "Manifest" in settings.STORAGES["staticfiles"]["BACKEND"]


def file_hash(path):
    """Hash curto do contido; recalcúlase se cambia a data de modificación (desenvolvemento)."""
    found = finders.find(path)
    if not found:
        return ""
    import os

    mtime = os.stat(found).st_mtime_ns
    hit = _cache.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    with open(found, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()[:10]
    _cache[path] = (mtime, digest)
    return digest


def asset_url(path):
    url = static(path)
    if hashed_storage():
        return url  # o nome xa leva o hash
    h = file_hash(path)
    return f"{url}?v={h}" if h else url


def version():
    """Versión do service worker: cambia con calquera cambio nos ficheiros precacheados."""
    joined = "|".join(asset_url(p) + ":" + file_hash(p) for p in PRECACHE)
    return "eira-" + hashlib.sha256(joined.encode()).hexdigest()[:12]
