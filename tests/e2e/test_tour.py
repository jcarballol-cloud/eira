# SPDX-License-Identifier: EUPL-1.2
"""v1.5.1: guía paso a paso. Percorrido completo, teclado e foco, axe coa guía aberta (tema claro
e escuro), 360 px con texto grande e que os elementos de cada paso existen nas súas pantallas."""

import pytest
from axe_playwright_python.sync_playwright import Axe

from apps.tenants.tours import TOURS, target_selector

from .conftest import DESKTOP, MOBILE, TABLET
from .test_accessibility import RULES, format_violations

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]

AXE = Axe()
PERSONAS = {
    "neighbour": ("uxia@demo.eira.example", MOBILE),
    "operator": ("brais@demo.eira.example", MOBILE),
    "cleaning": ("noela@demo.eira.example", MOBILE),
    "monitor": ("antia@demo.eira.example", TABLET),
    "admin": ("admin@vilardeiras.demo.eira.example", DESKTOP),
    "region": ("deputacion@demo.eira.example", DESKTOP),
}
NARROW = {"width": 360, "height": 740}
OPEN = "dialog#tour[open]"


def boxes_overlap(a, b):
    return (
        a["x"] < b["x"] + b["width"]
        and a["x"] + a["width"] > b["x"]
        and a["y"] < b["y"] + b["height"]
        and a["y"] + a["height"] > b["y"]
    )


def walk(page, kind):
    """Percorre a guía con «Seguinte» comprobando o indicador, o anuncio e que non tapa o paso."""
    total = len(TOURS[kind]["steps"])
    for i in range(total):
        assert page.locator("#tour-step").inner_text() == f"Paso {i + 1} de {total}"
        page.wait_for_function(
            "(s) => document.getElementById('tour-live').textContent.startsWith(s)",
            arg=f"Paso {i + 1} de {total}",
        )
        target = page.locator("dialog#tour").get_attribute("data-target")
        if target:
            el = page.locator(target).locator("visible=true").first
            box, panel = el.bounding_box(), page.locator(".tour__panel").bounding_box()
            # Un elemento moi alto (o panel do día) non cabe: abonda con que se vexa a súa cabeza
            head = {**box, "height": min(box["height"], 120)}
            assert box and not boxes_overlap(head, panel), f"{kind} paso {i + 1} tapa {target}"
        assert page.evaluate("document.getElementById('tour').contains(document.activeElement)")
        page.locator("[data-tour-next]").click()
    assert page.locator(OPEN).count() == 0


@pytest.mark.parametrize("kind", ["neighbour", "admin"])
@pytest.mark.parametrize("viewport", [DESKTOP, MOBILE], ids=["escritorio", "movil"])
def test_full_tour_neighbour_and_admin(new_page, kind, viewport):
    email, _v = PERSONAS[kind]
    page = new_page(viewport=viewport, persona=email, tour=True)
    page.locator(OPEN).wait_for()
    walk(page, kind)
    # O foco volve á páxina e a guía non sae de novo ao recargar
    assert page.evaluate("document.activeElement.id") == "main"
    page.reload()
    page.wait_for_load_state("networkidle")
    assert page.locator(OPEN).count() == 0


@pytest.mark.parametrize("kind", ["operator", "cleaning", "monitor", "region"])
def test_every_profile_tour_opens_and_ends(new_page, kind):
    email, viewport = PERSONAS[kind]
    page = new_page(viewport=viewport, persona=email, tour=True)
    page.locator(OPEN).wait_for()
    walk(page, kind)


@pytest.mark.parametrize("kind", list(PERSONAS))
def test_step_targets_exist_on_their_screens(new_page, kind):
    """Se alguén cambia unha pantalla e quita o elemento dun paso, este test avisa."""
    email, viewport = PERSONAS[kind]
    page = new_page(viewport=viewport, persona=email)
    missing = [
        t
        for t, _title, _body in TOURS[kind]["steps"]
        if t and page.locator(target_selector(t)).count() == 0
    ]
    assert not missing, f"{kind}: faltan {missing} en {page.url}"


def test_keyboard_focus_escape_and_help_button(new_page):
    page = new_page(viewport=MOBILE, persona=PERSONAS["neighbour"][0])
    assert page.locator(OPEN).count() == 0  # xa vista (localStorage)
    # «?» → «Ver a guía» ábrea nesta pantalla; ao pechar, o foco volve ao «?»
    page.locator(".app-header .help-pop__btn").click()
    page.locator(".app-header [data-tour-open]").click()
    page.locator(OPEN).wait_for()
    assert page.evaluate("document.activeElement.id") == "tour-title"
    page.keyboard.press("ArrowRight")
    assert page.locator("#tour-step").inner_text().startswith("Paso 2 ")
    page.keyboard.press("ArrowLeft")
    assert page.locator("#tour-step").inner_text().startswith("Paso 1 ")
    for _ in range(8):  # o tabulador dá a volta sen saír do diálogo
        page.keyboard.press("Tab")
        assert page.evaluate("document.getElementById('tour').contains(document.activeElement)")
    page.keyboard.press("Shift+Tab")
    assert page.evaluate("document.getElementById('tour').contains(document.activeElement)")
    page.keyboard.press("Escape")
    assert page.locator(OPEN).count() == 0
    assert page.evaluate("document.activeElement.closest('.help-pop') !== null")  # volve ao «?»
    # Tamén con ?guia=1, e despois desaparece da URL
    page.goto(page.url.split("?")[0] + "?guia=1")
    page.locator(OPEN).wait_for()
    page.locator("[data-tour-close]").click()
    assert "guia=1" not in page.url


def test_hidden_target_falls_back_to_centred(new_page):
    """No móbil o menú da xestión está recollido: eses pasos van centrados e a guía segue."""
    page = new_page(viewport=MOBILE, persona=PERSONAS["admin"][0], tour=True)
    page.locator(OPEN).wait_for()
    page.locator("[data-tour-next]").click()  # paso 2: Instalacións (no menú recollido)
    assert page.locator("dialog#tour.tour--center").count() == 1
    assert page.locator(".tour__ring").is_hidden()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_axe_with_tour_open(new_page, scheme):
    failures = []
    for kind in ("neighbour", "admin", "monitor"):
        email, viewport = PERSONAS[kind]
        page = new_page(viewport=viewport, persona=email, tour=True, color_scheme=scheme)
        page.locator(OPEN).wait_for()
        for _ in range(3):  # un paso centrado e pasos con elemento
            results = AXE.run(page, options=RULES)
            if results.violations_count:
                step = page.locator("#tour-step").inner_text()
                failures.append(f"[{kind} · {scheme} · {step}]\n{format_violations(results)}")
            page.locator("[data-tour-next]").click()
    assert not failures, "\n\n".join(failures)


def test_360px_large_text_no_horizontal_scroll(new_page):
    page = new_page(viewport=NARROW, persona=PERSONAS["neighbour"][0], tour=True)
    page.locator(OPEN).wait_for()
    page.evaluate("document.documentElement.classList.add('pref-large-text','pref-high-contrast')")
    total = len(TOURS["neighbour"]["steps"])
    for _ in range(total):
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        box = page.locator(".tour__panel").bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= NARROW["width"]
        assert box["y"] >= 0 and box["y"] + box["height"] <= NARROW["height"]
        page.locator("[data-tour-next]").click()


def test_reduced_motion_has_no_transition(new_page):
    page = new_page(
        viewport=MOBILE, persona=PERSONAS["neighbour"][0], tour=True, reduced_motion="reduce"
    )
    page.locator(OPEN).wait_for()
    assert (
        page.evaluate("getComputedStyle(document.querySelector('.tour__ring')).transitionDuration")
        == "0s"
    )
