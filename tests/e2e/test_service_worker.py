# SPDX-License-Identifier: EUPL-1.2
"""v4.1: un service worker dunha versión anterior, coa súa caché de estáticos vella, non pode
deixar a portada sen estilos. Antes, a versión era fixa («eira-v1») e o CSS servíase da caché
primeiro e cun URL sen versión, así que despois dun cambio de CSS a portada víase sen formato
(listas con viñetas) ata forzar a recarga."""

import time

import pytest

from apps.tenants import assets

from .conftest import DESKTOP

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]

POISON = """async (name) => {
  const c = await caches.open(name);
  const urls = [...document.querySelectorAll('link[rel=stylesheet]')].map((l) => l.href)
    .concat([location.origin + '/static/css/eira.css']);
  for (const u of urls) {
    await c.put(u, new Response('/* CSS vello */', { headers: { 'Content-Type': 'text/css' } }));
  }
  return urls.length;
}"""

STYLE = """() => {
  const ul = document.querySelector('.demo-tenants');
  const cs = getComputedStyle(ul);
  return { display: cs.display, list: cs.listStyleType,
           card: getComputedStyle(document.querySelector('.demo-tenant')).display };
}"""


def no_http_cache(page):
    """Sen caché HTTP do navegador: así cada CSS pasa polo service worker, coma tras un reinicio."""
    cdp = page.context.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})


SERVED = """async () => {
  const href = document.querySelector('link[rel=stylesheet]').href;
  return (await (await fetch(href)).text()).slice(0, 40);
}"""


def until(page, js, arg=None, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        value = page.evaluate(js, arg) if arg is not None else page.evaluate(js)
        if value:
            return value
        time.sleep(0.25)
    raise AssertionError(f"Non se cumpriu: {js}")


def test_old_service_worker_cache_does_not_unstyle_home(new_page, base, monkeypatch):
    # 1. Unha versión «anterior» do service worker controla a páxina e ten a súa caché envelenada
    monkeypatch.setattr(assets, "version", lambda: "eira-vella")
    page = new_page(viewport=DESKTOP)
    no_http_cache(page)
    page.goto(base + "/")
    until(page, "async () => !!(await navigator.serviceWorker.ready).active")
    page.reload()
    until(page, "() => !!navigator.serviceWorker.controller")
    assert page.evaluate(POISON, "eira-static-eira-vella") >= 2
    assert page.evaluate(POISON, "eira-static-eira-v1") >= 2  # nome usado ata a v4

    # 2. Publícase unha versión nova: o navegador actualiza o service worker
    monkeypatch.undo()
    page.evaluate(
        "async () => { const r = await navigator.serviceWorker.getRegistration(); await r.update(); }"
    )
    until(
        page,
        "async () => !(await caches.keys()).some((k) => k.includes('vella') || k.endsWith('eira-v1'))",
    )

    # 3. A portada ten estilos: as tarxetas en grella e sen viñetas
    page.goto(base + "/?concello=")
    assert "CSS vello" not in page.evaluate(SERVED)
    style = page.evaluate(STYLE)
    assert style == {"display": "grid", "list": "none", "card": "flex"}, style


def test_stale_css_in_active_cache_is_not_served(new_page, base):
    """O caso real: a caché do service worker activo ten un CSS vello baixo o mesmo URL. Antes
    servíase primeiro da caché; agora o CSS vai á rede primeiro (e en desenvolvemento todo)."""
    page = new_page(viewport=DESKTOP)
    no_http_cache(page)
    page.goto(base + "/")
    until(page, "async () => !!(await navigator.serviceWorker.ready).active")
    page.reload()
    until(page, "() => !!navigator.serviceWorker.controller")
    active = page.evaluate(
        "async () => (await caches.keys()).find((k) => k.startsWith('eira-static-'))"
    )
    assert page.evaluate(POISON, active) >= 2
    page.goto(base + "/?concello=")
    assert "CSS vello" not in page.evaluate(SERVED)
    assert page.evaluate(STYLE)["display"] == "grid"
    # e o CSS vai versionado: o URL cambia cando cambia o contido
    href = page.evaluate(
        "() => document.querySelector('link[rel=stylesheet]').getAttribute('href')"
    )
    assert "?v=" in href or "eira." in href.split("/")[-1].replace("eira.css", "")
