# SPDX-License-Identifier: EUPL-1.2
"""Idioma (14/11/2026): cun navegador en castelán (es-ES) a demo ábrese en galego; só cambia ao
escoller «ES» no selector, e a escolla mantense ao recargar, ao navegar e ao entrar cunha persoa."""

import pytest

from .conftest import MOBILE, login_as

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]

SPANISH_BROWSER = {"locale": "es-ES", "extra_http_headers": {"Accept-Language": "es-ES,es;q=0.9"}}


def html_lang(page):
    return page.evaluate("document.documentElement.lang")


def test_spanish_browser_starts_in_galician(new_page, base):
    page = new_page(viewport=MOBILE, **SPANISH_BROWSER)
    assert page.evaluate("navigator.language") == "es-ES"
    for path in ("/", "/c/vilardeiras/", "/acceso/", "/c/vilardeiras/accesibilidade/"):
        page.goto(base + path)
        assert html_lang(page) == "gl", path
    page.goto(base + "/c/vilardeiras/")
    assert page.locator("h1").first.inner_text() == "Instalacións"


def test_choosing_spanish_is_kept(new_page, base):
    page = new_page(viewport=MOBILE, **SPANISH_BROWSER)
    page.goto(base + "/c/vilardeiras/")
    with page.expect_navigation():
        page.locator(".lang-form button[value=es]").first.click()
    assert html_lang(page) == "es"
    assert page.locator("h1").first.inner_text() == "Instalaciones"
    assert page.locator(".lang-form button[value=es]").first.get_attribute("aria-current") == "true"
    page.reload()
    assert html_lang(page) == "es"
    page.goto(base + "/acceso/")
    assert html_lang(page) == "es"
    # Ao entrar cunha persoa, a escolla pasa ao perfil e segue en castelán
    login_as(page, base, "uxia@demo.eira.example")
    assert html_lang(page) == "es"
    page.goto(base + "/conta/")
    field = page.locator("#id_preferred_language")
    assert field.input_value() == "es"
    # Deixámolo como estaba (a conta de Uxía úsana outros tests): «O do concello»
    field.select_option("")
    with page.expect_navigation():
        page.locator("main form[novalidate] button[type=submit]").first.click()
    assert page.locator("#id_preferred_language").input_value() == ""


def test_a_new_spanish_browser_still_starts_in_galician_after_someone_chose_spanish(new_page, base):
    first = new_page(viewport=MOBILE, **SPANISH_BROWSER)
    first.goto(base + "/c/vilardeiras/")
    with first.expect_navigation():
        first.locator(".lang-form button[value=es]").first.click()
    assert html_lang(first) == "es"
    other = new_page(viewport=MOBILE, **SPANISH_BROWSER)
    other.goto(base + "/c/vilardeiras/")
    assert html_lang(other) == "gl"
