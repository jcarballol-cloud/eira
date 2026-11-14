# SPDX-License-Identifier: EUPL-1.2
"""v5 · E2E: reserva noutro concello da rede con luz, axuda «?», seguridade, aprobación e oficina."""

import pytest

from apps.bookings.models import Booking
from apps.integrations.models import FakePayment

from .conftest import DESKTOP, MOBILE

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]
C = "/c/vilardeiras"


def pick_lit_slot(page):
    """Unha franxa con luz desta semana ou, se xa non quedan (o domingo pola noite só queda ese
    día, e os datos aleatorios da demo poden enchelo: atopado na CI ás 00:05), da seguinte."""
    for _week in range(2):
        for chip in page.locator(".daychip").all():
            chip.click()
            lit = page.locator(".daypanel:not([hidden]) a.pill:has(.pill__light)")
            if lit.count():
                lit.first.click()
                return True
        following = page.locator("#week a[aria-label='Semana seguinte']")
        if not following.count():
            break
        with page.expect_response(lambda r: "semana=" in r.url):
            following.first.click()
        page.wait_for_load_state("networkidle")
    return False


def test_uxia_books_in_pontedouro_with_light(new_page, base):
    page = new_page(viewport=MOBILE, persona="uxia@demo.eira.example")
    page.goto(f"{base}{C}/")
    page.select_option("#town-select", "pontedouro")
    page.click("form.town-switch button[type=submit]")
    assert "/c/pontedouro/" in page.url
    assert "non empadroadas" in page.locator(".network-banner").inner_text()
    # As lapelas seguen sendo as da app de Vilardeiras
    assert page.locator(".tabbar a").first.get_attribute("href").startswith(f"{C}/app/")
    page.click("main a:has-text('Pista de pádel 1 da Ribeira')")
    assert pick_lit_slot(page)
    page.click("[data-picksum-go]")
    summary = page.locator("#price-summary").inner_text()
    assert "luz 1,50 €" in summary and "Total" in summary and "non empadroadas" in summary
    page.fill("#id_participants", "4")
    page.check("#id_accept_rules")
    page.click("main button.btn-lg")
    assert "/dev/tpv/" in page.url
    assert "Concello de Pontedouro" in page.locator("main").inner_text()
    page.click("button[value=ok]")
    page.wait_for_load_state()
    b = Booking.objects.filter(
        user__email="uxia@demo.eira.example", municipality__slug="pontedouro"
    ).latest("created_at")
    assert b.status == "confirmed" and b.lighting_cents == 150 and b.participants == 4
    assert b.tariff_audience == "non_resident" and b.network_origin.slug == "vilardeiras"
    assert "Pontedouro" in FakePayment.objects.get(reference=b.payment_reference).merchant
    page.goto(f"{base}{C}/reservas/")
    assert "Noutros concellos" in page.locator("main").inner_text()


def test_help_button_and_safety_page(new_page, base):
    page = new_page(viewport=MOBILE, persona="uxia@demo.eira.example")
    page.goto(f"{base}{C}/reservas/")
    page.click(".app-header .help-pop > summary")
    panel = page.locator(".app-header .help-pop__panel")
    assert panel.is_visible() and "As miñas reservas" in panel.inner_text()
    assert panel.locator("a[href^='tel:']").count() == 1
    page.click(".app-header a.safety-btn")
    assert page.locator("a.emergency-call[href='tel:112']").is_visible()
    page.click("text=Avisar dun risco")
    assert "Avisar dun risco" in page.locator("h1").inner_text()


def test_admin_approves_and_office_payment(new_page, base):
    admin = new_page(viewport=DESKTOP, persona="admin@vilardeiras.demo.eira.example")
    admin.goto(f"{base}{C}/xestion/")
    first = admin.locator("#appr-title ~ ul a").first
    first.click()
    pk = int(admin.url.rstrip("/").split("/")[-1])
    admin.click("button:has-text('Aprobar')")
    b = Booking.objects.get(pk=pk)
    assert b.approved_at is not None and b.status in ("confirmed", "pending_office")
    # Menú básico por defecto: «Máis ferramentas» recollido; o avanzado ábreo
    assert admin.locator("details.sidenav__more:not([open])").count() == 1
    admin.click("button:has-text('Menú avanzado')")
    assert admin.locator("details.sidenav__more[open]").count() == 1

    uxia = new_page(viewport=MOBILE, persona="uxia@demo.eira.example")
    hall = "Pavillón municipal de Vilardeiras"
    uxia.goto(f"{base}{C}/")
    uxia.click(f"main a:has-text('{hall}')")
    uxia.locator(".daypanel:not([hidden]) a.pill[data-pick]").first.click()
    uxia.click("[data-picksum-go]")
    uxia.check("input[name=payment_method][value=office]")
    uxia.check("#id_accept_rules")
    uxia.click("main button.btn-lg")
    assert "oficina" in uxia.locator("main").inner_text()
    b = Booking.objects.filter(user__email="uxia@demo.eira.example").latest("created_at")
    assert b.status == "pending_office" and b.payment_method == "office"
