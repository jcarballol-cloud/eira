# SPDX-License-Identifier: EUPL-1.2
"""v1.1 · E2E do rexistro de limpeza: QR sen conexión, só as súas tarefas, aviso e exportación."""

import datetime as dt
import time

import pytest
from django.utils import timezone

from apps.maintenance.models import CleaningLog, CleaningZone

from .conftest import DESKTOP, MOBILE

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]
C = "/c/vilardeiras"
NOELA = "noela@demo.eira.example"


def _until(page, js, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        if page.evaluate(js):
            return True
        time.sleep(0.25)
    raise AssertionError(f"Non se cumpriu: {js}")


def test_qr_checklist_works_without_signal(new_page, base):
    zone = CleaningZone.objects.get(facility__municipality__slug="vilardeiras", name="Vestiario 2")
    before = CleaningLog.objects.filter(zone=zone).count()
    page = new_page(viewport=MOBILE, persona=NOELA)
    logs = []
    page.on("pageerror", lambda e: logs.append(str(e)))
    page.goto(f"{base}{C}/operario/")
    assert "Tarefas" in page.locator(".tabbar").inner_text()
    assert page.locator(".zone-card.overdue").count() >= 1  # os aseos van atrasados
    # O service worker controla a páxina e garda as zonas para abrilas sen cobertura
    _until(page, "async () => !!(await navigator.serviceWorker.ready).active")
    page.reload()
    _until(page, "() => !!navigator.serviceWorker.controller")
    url = f"{C}/operario/limpeza/{zone.token}/"
    _until(
        page,
        f"async () => {{ for (const k of await caches.keys()) {{ if (await (await caches.open(k))"
        f".match('{base}{url}', {{ ignoreVary: true }})) return true; }} return false; }}",
    )
    page.context.set_offline(True)
    page.goto(base + url)  # «escanear o QR» sen cobertura: ábrese desde o móbil
    assert "Rexistrar limpeza" in page.locator("main").inner_text()
    page.uncheck("#z-1")
    page.fill("#id_notes", "Feito sen cobertura")
    saved_at = timezone.now()
    page.click("main button.btn-lg")
    page.wait_for_selector("[data-offline-note]:not([hidden])", timeout=5000)
    assert page.locator("[data-queue-count] [data-n]").inner_text() == "1"
    assert CleaningLog.objects.filter(zone=zone).count() == before
    page.wait_for_timeout(1500)  # que pase tempo entre gardar e sincronizar
    page.context.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    _until(page, "() => document.querySelector('[data-queue-count]').hidden === true")
    log = CleaningLog.objects.filter(zone=zone).latest("created_at")
    assert log.notes == "Feito sen cobertura" and log.user.email == NOELA
    assert len(log.done_items()) == len(log.items) - 1
    # A hora do rexistro é a de cando se gardou sen conexión, non a da sincronización
    assert abs((log.done_at - saved_at).total_seconds()) < 1.5
    assert log.created_at - log.done_at > dt.timedelta(seconds=1)
    assert not logs, logs


def test_cleaning_staff_only_has_their_tool(new_page, base):
    page = new_page(viewport=MOBILE, persona=NOELA)
    assert page.url.endswith(f"{C}/operario/")
    text = page.locator("main").inner_text()
    assert "Tarefas de limpeza" in text and "Revisión de seguridade" not in text
    for path in ("/xestion/", "/xestion/limpeza/", "/app/", "/reservas/"):
        assert page.goto(f"{base}{C}{path}").status == 403


def test_council_sees_overdue_zone_and_exports_the_log(new_page, base):
    page = new_page(viewport=DESKTOP, persona="admin@vilardeiras.demo.eira.example")
    page.goto(f"{base}{C}/xestion/")
    assert "Limpeza atrasada" in page.locator("main").inner_text()
    page.click("main a:has-text('Ver o rexistro de limpeza')")
    main = page.locator("main").inner_text()
    assert "Aseos" in main and "Limpezas Brillo do Val" in main
    page.select_option("#id_x-fmt", "pdf")
    with page.expect_download() as dl:
        page.click("form[action$='/limpeza/rexistro/'] button[type=submit]")
    assert dl.value.suggested_filename.startswith("rexistro-limpeza-")
    assert dl.value.suggested_filename.endswith(".pdf")
    page.select_option("#id_x-fmt", "csv")
    with page.expect_download() as dl:
        page.click("form[action$='/limpeza/rexistro/'] button[type=submit]")
    with open(dl.value.path(), encoding="utf-8-sig") as fh:
        head = fh.readline()
    assert head.startswith("data,hora,instalacion,zona,persoa,empresa")


def test_facility_page_shows_last_cleaning_to_everyone(new_page, base):
    zone = CleaningZone.objects.get(facility__municipality__slug="vilardeiras", name="Aseos")
    page = new_page(viewport=MOBILE)
    page.goto(f"{base}{C}/instalacions/{zone.facility.pk}/")
    assert "Última limpeza:" in page.locator(".facility-trust").inner_text()
