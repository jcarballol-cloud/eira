# SPDX-License-Identifier: EUPL-1.2
"""Auditoría RXPD (14/11/2026): «Protección de datos: primeiros pasos» (teclado, auditoría, axe en
claro e escuro, 360 px) e que o dispositivo esquece as páxinas gardadas ao saír ou cambiar de
persoa."""

import pytest
from axe_playwright_python.sync_playwright import Axe

from .conftest import DESKTOP, MOBILE, login_as
from .test_accessibility import RULES, format_violations

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]

AXE = Axe()
ADMIN = "admin@vilardeiras.demo.eira.example"
STEPS = "/c/vilardeiras/xestion/privacidade/primeiros-pasos/"
DOC = "/c/vilardeiras/xestion/privacidade/documentos/rexistro/"
NARROW = {"width": 360, "height": 740}


def test_mark_a_step_with_the_keyboard_and_it_is_audited(new_page, base):
    page = new_page(viewport=DESKTOP, persona=ADMIN)
    page.goto(base + STEPS)
    assert page.locator("h1").inner_text() == "Protección de datos: primeiros pasos"
    step = page.locator("#paso-retention")
    assert "Pendente" in step.locator("h2").inner_text()
    step.get_by_role("button", name="Marcar como feito").focus()
    with page.expect_navigation():
        page.keyboard.press("Enter")
    assert "Feito" in page.locator("#paso-retention h2").inner_text()
    assert "1 de 7 pasos feitos" in page.locator("#steps-progress").inner_text()
    page.goto(base + "/c/vilardeiras/xestion/privacidade/auditoria/?categoria=rxpd")
    assert page.get_by_text("Paso de protección de datos feito").count() >= 1


def test_document_opens_from_its_step(new_page, base):
    page = new_page(viewport=MOBILE, persona=ADMIN)
    page.goto(base + STEPS)
    page.locator("#paso-rat").get_by_role("link", name="Ler o documento").click()
    page.wait_for_load_state()
    assert "MODELO DE EXEMPLO" in page.locator("article").inner_text()
    assert page.get_by_role("link", name="Descargar (Markdown)").count() == 1


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_axe_on_steps_and_document(new_page, base, scheme):
    failures = []
    for viewport in (DESKTOP, MOBILE):
        page = new_page(viewport=viewport, persona=ADMIN, color_scheme=scheme)
        for path in (STEPS, DOC):
            page.goto(base + path)
            results = AXE.run(page, options=RULES)
            if results.violations_count:
                failures.append(
                    f"[{path} · {scheme} · {viewport['width']}]\n{format_violations(results)}"
                )
    assert not failures, "\n\n".join(failures)


def test_360px_without_horizontal_scroll(new_page, base):
    page = new_page(viewport=NARROW, persona=ADMIN)
    for path in (STEPS, DOC):
        page.goto(base + path)
        page.evaluate("document.documentElement.classList.add('pref-large-text')")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), path


CACHED = """async () => {
  const c = await caches.open('eira-pages-proba');
  await c.put('/c/vilardeiras/reservas/', new Response('as miñas reservas'));
  return (await caches.keys()).filter(k => k.startsWith('eira-pages-')).length;
}"""
LEFT = "async () => (await caches.keys()).filter(k => k.startsWith('eira-pages-')).length"


def owner_known(page):
    """Agarda a que eira.js anote de quen é a caché (a primeira vez bórraa: sería doutra persoa)."""
    page.wait_for_function("() => !!localStorage.getItem('eira-cache-owner')", timeout=5000)


def wait_cache_empty(page):
    page.wait_for_function(
        "async () => (await caches.keys()).every(k => !k.startsWith('eira-pages-'))", timeout=5000
    )


def test_cached_pages_are_forgotten_on_logout(new_page, base):
    page = new_page(viewport=MOBILE, persona="uxia@demo.eira.example")
    owner_known(page)
    assert page.evaluate(CACHED) >= 1
    page.reload()  # mesma persoa: a caché queda para usala sen rede
    page.wait_for_load_state("networkidle")
    assert page.evaluate(LEFT) >= 1
    page.locator(".logout-form button").first.click()
    page.wait_for_load_state()
    wait_cache_empty(page)


def test_cached_pages_are_forgotten_when_someone_else_signs_in(new_page, base):
    page = new_page(viewport=MOBILE, persona="uxia@demo.eira.example")
    owner_known(page)
    assert page.evaluate(CACHED) >= 1
    login_as(page, base, "manuel@demo.eira.example")
    wait_cache_empty(page)
