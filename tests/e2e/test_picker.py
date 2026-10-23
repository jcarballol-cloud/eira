# SPDX-License-Identifier: EUPL-1.2
"""v3: selector de franxas (tira de días, pastillas, resumo fixo), accesible e con texto grande."""

import pytest

from apps.facilities.models import Facility

from .conftest import DESKTOP, MOBILE

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]


def open_padel(new_page, base, viewport=MOBILE, prefs=None):
    page = new_page(viewport=viewport, persona="uxia@demo.eira.example")
    if prefs:
        page.context.add_cookies([{"name": "eira_prefs", "value": prefs, "url": base}])
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    page.goto(f"{base}/c/vilardeiras/instalacions/{padel.pk}/")
    page.wait_for_selector(".daystrip:not([hidden])")
    return page


@pytest.mark.parametrize("viewport", [MOBILE, DESKTOP], ids=["movil", "escritorio"])
def test_daystrip_pills_and_sticky_summary(new_page, base, viewport):
    page = open_padel(new_page, base, viewport)
    assert page.locator(".daychip").count() == 7
    assert page.locator(".daypanel:not([hidden])").count() == 1
    sw, cw = page.evaluate(
        "[document.documentElement.scrollWidth, document.documentElement.clientWidth]"
    )
    assert sw <= cw
    # A palabra «Recomendada» xa non vai dentro do botón; o estado vai na etiqueta accesible
    pill = page.locator(".daypanel:not([hidden]) a.pill[data-pick]").first
    label = pill.get_attribute("aria-label")
    assert "libre" in label and "€" in label and "Recomendada" not in pill.inner_text()
    for el in page.locator(".daypanel:not([hidden]) .pill").all():
        box, inner = el.evaluate("e => [e.clientWidth, e.scrollWidth]")
        assert inner <= box + 1, "o contido da pastilla non pode saír fóra"
    pill.click()
    summary = page.locator("[data-picksum]")
    assert summary.is_visible() and "Reservar" in summary.inner_text()
    assert pill.get_attribute("aria-current") == "true"
    page.click("[data-picksum-go]")
    page.wait_for_url("**/reservar/?inicio=**")


def test_keyboard_moves_between_days(new_page, base):
    page = open_padel(new_page, base)
    selected = page.locator(".daychip[aria-selected=true]")
    first_id = selected.get_attribute("id")
    selected.focus()
    page.keyboard.press("ArrowRight")
    now = page.locator(".daychip[aria-selected=true]")
    assert now.get_attribute("id") != first_id
    assert page.evaluate("document.activeElement.getAttribute('role')") == "tab"
    panel = page.locator(f"#{now.get_attribute('aria-controls')}")
    assert panel.is_visible()


def test_recommended_and_busy_not_only_colour(new_page, base):
    page = open_padel(new_page, base)
    for day in page.locator(".daychip").all():
        day.click()
        rec = page.locator(".daypanel:not([hidden]) a.pill-recommended")
        if rec.count():
            assert rec.first.locator(".pill__star").inner_text() == "★"
            assert "recomendada" in rec.first.get_attribute("aria-label")
            assert rec.first.locator(".pill__price s").count() == 1  # prezo sen desconto tachado
            break
    else:
        pytest.skip("Esta semana non hai franxas recomendadas na demo")


def test_large_text_two_columns(new_page, base):
    page = open_padel(new_page, base, prefs="large_text")
    cols = page.evaluate(
        "getComputedStyle(document.querySelector('.daypanel:not([hidden]) .pills')).gridTemplateColumns.split(' ').length"
    )
    assert cols <= 2
    small = open_padel(new_page, base)
    assert (
        small.locator(".daypanel:not([hidden]) .pill").first.bounding_box()["height"]
        < page.locator(".daypanel:not([hidden]) .pill").first.bounding_box()["height"]
    )


def test_without_js_pills_link_to_confirmation(new_page, base):
    page = new_page(viewport=MOBILE, persona="uxia@demo.eira.example", java_script_enabled=False)
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    page.goto(f"{base}/c/vilardeiras/instalacions/{padel.pk}/")
    assert page.locator(".daypanel").count() == 7  # todos os días seguidos
    page.locator("a.pill[data-pick]").first.click()
    page.wait_for_url("**/reservar/?inicio=**")
