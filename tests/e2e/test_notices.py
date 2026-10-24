# SPDX-License-Identifier: EUPL-1.2
"""v4: o concello redacta un aviso, ve a vista previa por canle e envíao; a veciña velo na app."""

import pytest

from .conftest import DESKTOP, MOBILE

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]


def test_compose_preview_send_and_read(new_page, base):
    page = new_page(viewport=DESKTOP, persona="admin@vilardeiras.demo.eira.example")
    page.goto(base + "/c/vilardeiras/xestion/avisos/novo/")
    page.select_option("#id_category", "news")
    page.fill("#id_title", "Proba E2E: novo horario do rocódromo")
    page.fill("#id_body", "Desde o luns, o rocódromo abre ata as 22:00.")
    page.get_by_role("button", name="Vista previa").click()
    page.wait_for_load_state()
    assert "Chegaríalle a" in page.locator("aside[aria-labelledby=pv-title]").inner_text()
    assert page.locator(".push-banner").count() == 1 and page.locator(".tg-bubble").count() == 1
    page.get_by_role("button", name="Enviar ou programar").click()
    page.wait_for_load_state()
    assert "Enviado" in page.locator("main").inner_text()

    uxia = new_page(viewport=MOBILE, persona="uxia@demo.eira.example")
    uxia.goto(base + "/c/vilardeiras/avisos/?categoria=news")
    assert "Proba E2E: novo horario do rocódromo" in uxia.locator("main").inner_text()
    uxia.goto(base + "/c/vilardeiras/avisos/?categoria=closure")
    assert "Proba E2E" not in uxia.locator("main").inner_text()
