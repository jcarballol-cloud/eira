# SPDX-License-Identifier: EUPL-1.2
"""v4.1: tema escuro da app (veciñanza, operario e tableta) e botón «Día / Noite» da demo.

axe sen violacións WCAG 2.1 AA en modo escuro e o botón cambia a ilustración da cabeceira."""

import pytest
from axe_playwright_python.sync_playwright import Axe

from apps.integrations.demo import NEW_NEIGHBOUR

from .conftest import DESKTOP, MOBILE, TABLET
from .test_accessibility import RULES, format_violations, page_sets

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]

AXE = Axe()
C = "/c/vilardeiras"
# Perfís que usan a app móbil ou a tableta (o escritorio do concello non ten tema escuro)
APP_PERSONAS = {
    "uxia@demo.eira.example": MOBILE,
    "brais@demo.eira.example": MOBILE,
    NEW_NEIGHBOUR: MOBILE,
    "antia@demo.eira.example": TABLET,
}


def dark_page_sets():
    sets = page_sets()
    return {
        "uxia@demo.eira.example": sets["uxia@demo.eira.example"],
        "brais@demo.eira.example": sets["brais@demo.eira.example"],
        NEW_NEIGHBOUR: [*sets[NEW_NEIGHBOUR], f"{C}/actividades/"],
        "antia@demo.eira.example": sets["antia@demo.eira.example"],
    }


def test_axe_dark_theme(new_page, base):
    failures, checked = [], 0
    for persona, paths in dark_page_sets().items():
        page = new_page(viewport=APP_PERSONAS[persona], persona=persona, color_scheme="dark")
        for path in paths:
            resp = page.goto(base + path)
            assert resp.status == 200, f"{path} → {resp.status}"
            page.wait_for_load_state("networkidle")
            assert page.evaluate("document.documentElement.classList.contains('theme-dark')")
            results = AXE.run(page, options=RULES)
            checked += 1
            if results.violations_count:
                failures.append(f"[{persona}] {path}\n{format_violations(results)}")
    assert not failures, f"{len(failures)} páxinas con violacións de {checked}:\n\n" + "\n\n".join(
        failures
    )


VISIBLE = """() => {
  const swap = document.querySelector('.app-hello .illus-swap');
  const shown = [...swap.querySelectorAll('.illus')].find(p => getComputedStyle(p).opacity === '1');
  const img = shown && shown.querySelector('img');
  return img && img.complete ? img.currentSrc : null;
}"""


def test_day_night_toggle_swaps_illustration(new_page, base):
    page = new_page(viewport=DESKTOP, persona="uxia@demo.eira.example", color_scheme="light")
    page.goto(base + f"{C}/app/?marco=1")
    page.wait_for_load_state("networkidle")
    html = page.locator("html")
    assert "theme-dark" not in (html.get_attribute("class") or "")
    page.wait_for_function(VISIBLE)
    assert "noite" not in page.evaluate(VISIBLE)

    # Botón enriba do marco: tema escuro ao momento e ilustración nocturna (crossfade)
    frame_btn = page.locator(".theme-toggle--frame button")
    assert frame_btn.is_visible() and frame_btn.get_attribute("aria-pressed") == "false"
    with page.expect_response(lambda r: "/dev/tema/" in r.url) as saved:
        frame_btn.click()
    assert saved.value.status == 204
    assert html.get_attribute("data-theme") == "dark"
    assert frame_btn.get_attribute("aria-pressed") == "true"
    page.wait_for_function(f"() => ({VISIBLE})() && ({VISIBLE})().includes('noite')")
    assert page.evaluate(
        "getComputedStyle(document.querySelector('.illus--night')).transitionDuration"
    ) not in ("0s", "")

    # Gárdase na sesión: ao recargar segue de noite, servido xa polo servidor
    page.reload()
    page.wait_for_load_state("networkidle")
    assert html.get_attribute("data-theme") == "dark"
    page.wait_for_function(f"() => ({VISIBLE})() && ({VISIBLE})().includes('noite')")

    # O botón da barra de demo volve ao día
    page.locator(".demo-bar .theme-toggle button").click()
    assert html.get_attribute("data-theme") == "light"
    page.wait_for_function(f"() => ({VISIBLE})() && !({VISIBLE})().includes('noite')")


def test_dark_theme_follows_system_and_reduced_motion(new_page, base):
    page = new_page(
        viewport=MOBILE, persona=NEW_NEIGHBOUR, color_scheme="dark", reduced_motion="reduce"
    )
    page.goto(base + f"{C}/app/?marco=0")
    page.wait_for_load_state("networkidle")
    assert page.locator("html").get_attribute("data-theme") is None
    page.wait_for_function(f"() => ({VISIBLE})() && ({VISIBLE})().includes('noite')")
    assert (
        page.evaluate(
            "getComputedStyle(document.querySelector('.illus--night')).transitionDuration"
        )
        == "0s"
    )
    # Veciño novo: estado baleiro de reservas co seu debuxo
    assert page.locator(".empty-art img").count() >= 1
