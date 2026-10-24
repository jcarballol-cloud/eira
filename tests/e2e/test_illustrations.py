# SPDX-License-Identifier: EUPL-1.2
"""v4.1: a ilustración da cabeceira da app carga de inmediato só alí, o texto vai superposto na
zona despexada e, con texto grande, a ilustración pasa debaixo do saúdo."""

import pytest

from .conftest import MOBILE

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]

INFO = """() => {
  const box = document.querySelector('.app-hello--art');
  const img = box.querySelector('img'), h1 = box.querySelector('h1');
  const b = box.getBoundingClientRect(), i = img.getBoundingClientRect(), t = h1.getBoundingClientRect();
  return { loading: img.getAttribute('loading'), alt: img.getAttribute('alt'),
           src: img.currentSrc, overlay: t.top >= i.top && t.bottom <= i.bottom,
           textLeft: t.right <= b.left + b.width * 0.7, eager: document.querySelectorAll('img[loading=eager]').length,
           below: i.top >= t.bottom - 1 };
}"""


def test_app_header_illustration(new_page, base):
    page = new_page(viewport=MOBILE, persona="uxia@demo.eira.example")
    page.goto(base + "/c/vilardeiras/app/?marco=0")
    page.wait_for_load_state("networkidle")
    info = page.evaluate(INFO)
    assert info["loading"] == "eager" and info["alt"] == "" and info["eager"] == 1
    assert info["src"].endswith((".avif", ".webp")) and "cabecera-eira" in info["src"]
    assert info["overlay"] and info["textLeft"], info


def test_large_text_moves_illustration_below(new_page, base):
    page = new_page(viewport=MOBILE, persona="manuel@demo.eira.example")
    page.context.add_cookies([{"name": "eira_prefs", "value": "large_text", "url": base}])
    page.goto(base + "/c/vilardeiras/app/?marco=0")
    page.wait_for_load_state("networkidle")
    assert page.evaluate(INFO)["below"]
