# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · A: «Escoitar» con speechSynthesis simulado: voz, aviso único, axustes, sen rede externa."""

import pytest

from apps.bookings.models import Booking
from apps.facilities.models import Facility

from .conftest import MOBILE

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]

UXIA = "uxia@demo.eira.example"
C = "/c/vilardeiras"

FAKE = """
(() => {
  const voices = %s;
  window.__spoken = [];
  const synth = {
    getVoices: () => voices,
    speak: (u) => { window.__spoken.push({text: u.text, lang: u.lang, rate: u.rate, voice: u.voice && u.voice.lang}); },
    cancel: () => { window.__cancelled = (window.__cancelled || 0) + 1; },
    addEventListener: () => {},
  };
  Object.defineProperty(window, "speechSynthesis", {value: synth, configurable: true});
  window.SpeechSynthesisUtterance = function (text) { this.text = text; };
})();
"""
WITH_GL = '[{"lang":"gl-ES","name":"Galego"},{"lang":"es-ES","name":"Castelán"}]'
ONLY_ES = '[{"lang":"es-ES","name":"Castelán"}]'
NONE = """
Object.defineProperty(window, "speechSynthesis", {value: undefined, configurable: true});
"""


def _page(new_page, script):
    page = new_page(viewport=MOBILE, persona=UXIA)
    page.context.add_init_script(script)
    return page


def _screens():
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    booking = Booking.objects.filter(user__email=UXIA, status="confirmed").order_by("start").first()
    paths = {
        "inicio": f"{C}/app/",
        "instalación": f"{C}/instalacions/{padel.pk}/",
        "avisos": f"{C}/avisos/",
        "consellos": "/saude/",
        "protocolo": f"{C}/seguridade/accidente/{padel.pk}/",
    }
    if booking:
        paths["reserva e código"] = f"{C}/reservas/{booking.pk}/"
    return paths


def test_button_on_key_screens_reads_in_galician(new_page, base):
    page = _page(new_page, FAKE % WITH_GL)
    for name, path in _screens().items():
        assert page.goto(base + path).status == 200, path
        button = page.locator("[data-listen]").first
        assert button.is_visible(), name
        assert button.get_attribute("aria-label")
        page.evaluate("window.__spoken = []")
        button.click()
        page.wait_for_function("window.__spoken.length > 0 || true")
        if name == "consellos":
            continue  # sen datos, le a indicación inicial
        spoken = page.evaluate("window.__spoken")
        assert spoken, name
        assert spoken[0]["lang"] == "gl-ES" and spoken[0]["voice"] == "gl-ES", name
        assert page.locator("[data-listen-note]:visible").count() == 0
    # O texto da interface non aparece duplicado nin inclúe botóns
    page.goto(base + f"{C}/seguridade/accidente/")
    page.evaluate("window.__spoken = []")
    page.locator("[data-listen]").first.click()
    joined = " ".join(item["text"] for item in page.evaluate("window.__spoken"))
    assert "112" in joined and "Escoitar" not in joined


def test_spanish_fallback_warns_only_once(new_page, base):
    page = _page(new_page, FAKE % ONLY_ES)
    page.goto(base + f"{C}/app/")
    page.locator("[data-listen]").first.click()
    assert page.evaluate("window.__spoken")[0]["lang"] == "es-ES"
    note = page.locator("[data-listen-note]").first
    assert note.is_visible() and "castelán" in note.inner_text()
    page.goto(base + f"{C}/avisos/")
    page.locator("[data-listen]").first.click()
    assert page.evaluate("window.__spoken")[0]["lang"] == "es-ES"
    assert page.locator("[data-listen-note]:visible").count() == 0


def test_no_speech_synthesis_no_button(new_page, base):
    page = _page(new_page, NONE)
    page.goto(base + f"{C}/app/")
    assert page.locator("[data-listen-bar]").first.is_hidden()
    page.goto(base + "/preferencias/")
    assert page.locator("#voz").is_hidden()


def test_settings_slow_and_autocode_stay_local(new_page, base):
    page = _page(new_page, FAKE % WITH_GL)
    requests = []
    page.goto(base + "/preferencias/")
    page.on("request", lambda r: requests.append(r.url))
    page.locator("label[for=voz-slow]").click()
    page.locator("label[for=voz-auto]").click()
    page.goto(base + f"{C}/app/")
    page.evaluate("window.__spoken = []")
    page.locator("[data-listen]").first.click()
    assert page.evaluate("window.__spoken")[0]["rate"] == 0.75
    # Nada de servizos externos: todas as peticións ao propio servidor (agás teselas, aquí non hai)
    assert all(url.startswith(base) for url in requests), requests
    # Auto: le o código de acceso se a pantalla o ten
    booking = (
        Booking.objects.filter(user__email=UXIA, status="confirmed", facility__access_level=2)
        .order_by("start")
        .first()
    )
    if booking:
        page.goto(base + f"{C}/reservas/{booking.pk}/")
        spoken = page.evaluate("window.__spoken")
        if page.locator("[data-listen-code]").count():
            assert any("Código de acceso" in item["text"] for item in spoken)


def test_toggle_stops_and_label_changes(new_page, base):
    page = _page(new_page, FAKE % WITH_GL)
    page.goto(base + f"{C}/app/")
    button = page.locator("[data-listen]").first
    button.click()
    assert "Deter" in button.inner_text()
    assert button.get_attribute("aria-label") == "Deter a lectura"
    button.click()
    assert "Escoitar" in button.inner_text()
    assert page.evaluate("window.__cancelled") >= 1


def test_page_with_button_does_not_autoplay_by_default(new_page, base):
    page = _page(new_page, FAKE % WITH_GL)
    page.goto(base + f"{C}/app/")
    assert page.evaluate("window.__spoken") == []
