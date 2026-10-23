# SPDX-License-Identifier: EUPL-1.2
"""v3: ferramentas de demo independentes do perfil (correo e pechadura) e fluxo de Cl@ve."""

import re

import pytest
from django.utils import timezone

from apps.bookings.models import Booking

from .conftest import DESKTOP, MOBILE

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]


def login_as(page, base, email):
    page.goto(base + "/")
    page.locator(f"form:has(input[value='{email}']) button").click()
    page.wait_for_load_state("networkidle")


def assert_standalone(page):
    cls = page.evaluate("document.body.className")
    assert "devtool" in cls and "framed" not in cls and "layout-app" not in cls
    assert page.locator(".tabbar, .sidebar, .shell").count() == 0
    sw, cw = page.evaluate(
        "[document.documentElement.scrollWidth, document.documentElement.clientWidth]"
    )
    assert sw <= cw, (sw, cw)


@pytest.mark.parametrize("viewport", [MOBILE, DESKTOP], ids=["movil", "escritorio"])
@pytest.mark.parametrize("logged", [True, False], ids=["con-sesion", "sen-sesion"])
def test_mailbox_standalone_wraps_and_links(new_page, base, viewport, logged):
    page = new_page(viewport=viewport)
    if logged:
        login_as(page, base, "uxia@demo.eira.example")
    email = "unha.direccion.moi.longa.para.probar.o.salto@example.org"
    page.goto(base + "/c/vilardeiras/app/solicitar/")
    page.fill("#id_name", "Proba Correo")
    page.fill("#id_email", email)
    page.fill("#id_birth_year", "1990")
    page.fill("#id_postcode", "15999")
    page.check("#id_resident")
    page.click("main button[type=submit]")
    page.goto(f"{base}/dev/mailbox/?para={email}")
    assert_standalone(page)
    body = page.locator(".mail__body").first
    assert body.evaluate("e => getComputedStyle(e).whiteSpace") == "pre-wrap"
    link = body.locator("a[href*='/app/instalar/?codigo=']")
    assert link.count() == 1
    link.click()
    page.wait_for_url("**/app/instalar/**")


@pytest.mark.parametrize("viewport", [MOBILE, DESKTOP], ids=["movil", "escritorio"])
@pytest.mark.parametrize("logged", [True, False], ids=["con-sesion", "sen-sesion"])
def test_lock_simulator_standalone_opens_with_code(new_page, base, viewport, logged):
    booking = (
        Booking.objects.filter(
            user__email="uxia@demo.eira.example",
            facility__lock__kind="offline",
            status="confirmed",
            end__gt=timezone.now(),
        )
        .order_by("start")
        .first()
    )
    code = booking.facility.lock.code_for_booking(booking)
    page = new_page(viewport=viewport)
    if logged:
        login_as(page, base, "uxia@demo.eira.example")
        page.goto(base + "/dev/lock-simulator/")  # sen parámetros: preselecciona a súa reserva
    else:
        at = timezone.localtime(booking.start).strftime("%Y-%m-%dT%H:%M")
        page.goto(f"{base}/dev/lock-simulator/?device={booking.facility.lock.pk}&at={at}")
    assert_standalone(page)
    if viewport == DESKTOP:
        pad = page.locator(".lock-sim").bounding_box()
        how = page.locator("#how-title").bounding_box()
        assert how["x"] >= pad["x"] + pad["width"], "«Como funciona» non pode ir enriba do teclado"
    for digit in code:
        page.locator(f".keypad button[data-key='{digit}']").click()
    page.click("text=Probar código")
    page.wait_for_load_state("networkidle")
    assert "ABERTO" in page.locator(".lock-screen .state").inner_text()


def test_demo_bar_opens_tools_in_new_tab(new_page, base):
    page = new_page(viewport=DESKTOP)
    login_as(page, base, "uxia@demo.eira.example")
    for name in ("Correo simulado", "Pechadura"):
        link = page.locator(".demo-bar a", has_text=name).first
        assert link.get_attribute("target") == "_blank"


def test_clave_end_to_end_from_tenant_with_other_session(new_page, base):
    page = new_page(viewport=MOBILE)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    login_as(page, base, "irene@demo.eira.example")
    page.goto(base + "/c/vilardeiras/reservas/")
    page.goto(base + "/acceso/?next=/c/vilardeiras/")
    page.click("text=Acceder con Cl@ve")
    page.wait_for_load_state("networkidle")
    assert_standalone(page)
    page.check("#id-proba-2")
    page.click("text=Identificarme")
    page.wait_for_load_state("networkidle")
    assert re.search(r"/c/vilardeiras/$", page.url), page.url
    assert not errors
    # Sen next: volve ao último concello visitado (Pontedouro), non a un calquera
    page.context.clear_cookies()
    page.goto(base + "/acceso/")  # crea a sesión
    page.goto(base + "/c/pontedouro/")
    page.goto(base + "/acceso/")
    page.click("text=Acceder con Cl@ve")
    page.click("text=Identificarme")
    page.wait_for_load_state("networkidle")
    assert "/c/pontedouro/" in page.url, page.url
