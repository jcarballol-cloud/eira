# SPDX-License-Identifier: EUPL-1.2
"""v3: tableta da monitora co grupo de 40 persoas ficticias (abecedario → nome → entrada/saída → grazas)."""

import pytest
from django.utils import timezone
from playwright.sync_api import expect

from apps.activities.models import Attendance, Group
from apps.activities.services import sessions_for_day

from .conftest import DESKTOP

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]


def open_kiosk(new_page, base):
    group = Group.objects.get(name="Grupo grande (40)")
    session = sessions_for_day([group], timezone.localdate())[0]
    page = new_page(viewport=DESKTOP, persona="antia@demo.eira.example")
    page.goto(f"{base}/c/vilardeiras/monitor/sesion/{session.pk}/rexistro/")
    page.wait_for_selector(".kiosk__letter")
    return page, session


def test_forty_people_in_and_some_out_with_rpe(new_page, base):
    page, session = open_kiosk(new_page, base)
    letters = page.locator(".kiosk__letter.has-people")
    total = sum(int(b.locator(".kiosk__count").inner_text()) for b in letters.all())
    assert total == 40
    # Entrada: todas as persoas, letra a letra
    for L in [b.get_attribute("data-letter") for b in letters.all()]:
        while True:
            page.locator(f".kiosk__letter[data-letter='{L}']").click()
            pending = page.locator(".kiosk__name:not(.is-in)")
            if not pending.count():
                page.click("text=← Volver")
                break
            pending.first.click()
            page.wait_for_selector(".kiosk__thanks")
            page.click("text=Seguinte persoa")
    assert "Entraron 40 de 40" in page.locator("[data-stat-in]").inner_text()
    expect(page.locator("[data-sync]")).to_contain_text("Todo gardado", timeout=20000)
    assert Attendance.objects.filter(session=session, present=True).count() == 40
    # Saída: busca global e escala RPE; volta soa ao abecedario aos 3 s
    page.click("[data-mode=out]")
    for q, rpe in (("Álvarez", 3), ("ñeiro", 7)):
        page.fill(".kiosk__search", q)
        page.locator(".kiosk__results .kiosk__name").first.click()
        page.locator(f".kiosk__rpebtn[data-rpe='{rpe}']").click()
        page.wait_for_selector(".kiosk__thanks")
        assert "Grazas" in page.locator(".kiosk__thanks-title").inner_text()
        page.wait_for_selector(".kiosk__letter", timeout=5000)  # volta automática
    expect(page.locator("[data-sync]")).to_contain_text("Todo gardado", timeout=20000)
    assert sorted(
        Attendance.objects.filter(session=session).exclude(rpe=None).values_list("rpe", flat=True)
    ) == [3, 7]
    # Quen falta: en modo saída, as que entraron e aínda non rexistraron o esforzo
    page.click("[data-missing-toggle]")
    assert page.locator(".kiosk__missing-list li").count() == 38


def test_photo_icons_and_accented_search(new_page, base):
    page, _s = open_kiosk(new_page, base)
    page.fill(".kiosk__search", "alvarez")  # sen acento atopa «Álvarez»
    results = page.locator(".kiosk__results .kiosk__name")
    assert results.count() >= 1
    assert results.first.locator(".kiosk__photo .icon").count() == 1
    page.locator(".kiosk__letter[data-letter='Ñ']").click()
    assert page.locator(".kiosk__name").count() >= 1


def test_offline_queue_syncs_when_back_online(new_page, base):
    page, session = open_kiosk(new_page, base)
    page.context.set_offline(True)
    for L in ("A", "B", "C"):
        page.locator(f".kiosk__letter[data-letter='{L}']").click()
        page.locator(".kiosk__name").first.click()
        page.click("text=Seguinte persoa")
    assert "Sen conexión" in page.locator("[data-sync]").inner_text()
    assert not Attendance.objects.filter(session=session, present=True).exists()
    page.context.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    expect(page.locator("[data-sync]")).to_contain_text("Todo gardado", timeout=20000)
    assert Attendance.objects.filter(session=session, present=True).count() == 3
