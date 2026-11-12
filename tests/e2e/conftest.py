# SPDX-License-Identifier: EUPL-1.2
"""E2E: servidor en vivo con os datos de demostración e navegador Chromium (Playwright)."""

import os

import pytest
from django.core.management import call_command

# Playwright síncrono usa un bucle asyncio no mesmo fío que a proba.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

MOBILE = {"width": 390, "height": 844}
DESKTOP = {"width": 1280, "height": 900}
TABLET = {"width": 820, "height": 1180}  # tableta vertical (iPad Air)


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("seed_demo", verbosity=0)


@pytest.fixture(autouse=True)
def _clean_state():  # sobrescribe o autouse do conftest raíz (non usa tmp media nin settings)
    yield


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def base(live_server):
    from apps.tenants.models import Municipality

    # live_server baleira a BD tras cada proba (transaccional): volve cargar a demo se fai falla
    if not Municipality.objects.exists():
        call_command("seed_demo", verbosity=0)
    return live_server.url


def tours_seen_script():
    """v1.5.1: marca todas as guías paso a paso como vistas nesta sesión (para que non tapen as
    pantallas). Non usa «Non volver amosar», que se garda no perfil."""
    from apps.tenants.tours import TOURS, VERSION

    sets = ";".join(f"sessionStorage.setItem('eira-tour-seen-{k}-v{VERSION}','1')" for k in TOURS)
    return f"try{{{sets}}}catch(e){{}}"


@pytest.fixture
def new_page(browser, base):
    contexts = []

    def make(viewport=DESKTOP, persona=None, tour=False, **kw):
        ctx = browser.new_context(viewport=viewport, locale="gl-ES", **kw)
        if not tour:
            ctx.add_init_script(tours_seen_script())
        contexts.append(ctx)
        page = ctx.new_page()
        if persona:
            login_as(page, base, persona)
        return page

    yield make
    for ctx in contexts:
        ctx.close()


def demo_url(base, email):
    """Portada da demo no paso onde está o botón dese perfil (paso 2 do seu concello)."""
    from apps.integrations.demo import BY_EMAIL

    tenant = BY_EMAIL[email]["tenant"]
    return f"{base}/?concello={tenant}" if tenant else f"{base}/"


def login_as(page, base, email):
    page.goto(demo_url(base, email))
    page.locator(f"form:has(input[value='{email}']) button").click()
    page.wait_for_load_state()
