# SPDX-License-Identifier: EUPL-1.2
"""v1.5: percorridos de B a F co navegador real, sobre a demo."""

import pytest

from apps.accounts.models import Membership, User
from apps.activities.models import Group, MinorsAccreditation
from apps.legal.models import LegalAcceptance
from apps.safety.models import Alert

from .conftest import DESKTOP, MOBILE, TABLET

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]

C = "/c/vilardeiras"
ADMIN = "admin@vilardeiras.demo.eira.example"
UXIA = "uxia@demo.eira.example"


@pytest.mark.parametrize(
    "persona,viewport",
    [
        ("brais@demo.eira.example", MOBILE),
        ("noela@demo.eira.example", MOBILE),
        ("antia@demo.eira.example", MOBILE),
        ("antia@demo.eira.example", TABLET),
        (ADMIN, DESKTOP),
        (ADMIN, MOBILE),
    ],
)
def test_alert_button_on_each_profile(new_page, base, persona, viewport):
    page = new_page(viewport=viewport, persona=persona)
    assert page.locator(".alert-pill").is_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator(".alert-pill").click()
    page.wait_for_load_state()
    assert "/seguridade/alerta/" in page.url
    assert page.get_by_role("button", name="Accidente deportivo").is_visible()


def test_operator_raises_alert_and_sees_location_and_aed(new_page, base):
    before = Alert.objects.filter(origin="operator").count()
    page = new_page(viewport=MOBILE, persona="brais@demo.eira.example")
    page.locator(".alert-pill").click()
    page.wait_for_load_state()
    if page.locator("#alert-facility").count():
        page.locator("#alert-facility").select_option(index=0)
        page.get_by_role("button", name="Escoller").click()
        page.wait_for_load_state()
    assert page.locator(".location-112").is_visible()
    page.get_by_role("button", name="Emerxencia de seguridade").click()
    page.wait_for_load_state()
    assert page.locator(".location-112").is_visible()
    assert page.locator("a[href='tel:112']").first.is_visible()
    assert Alert.objects.filter(origin="operator").count() == before + 1


def test_legal_flow_accept_and_withdraw(new_page, base):
    page = new_page(viewport=MOBILE, persona=UXIA)
    banner = page.locator(".legal-banner")
    assert banner.is_visible()
    banner.click()
    page.wait_for_load_state()
    assert "MODELO DE EXEMPLO" in page.locator(".legal-example").first.inner_text()
    user = User.objects.get(email=UXIA)
    before = LegalAcceptance.objects.filter(user=user).count()
    page.locator("label[for=legal-accept]").click()
    page.get_by_role("button", name="Aceptar").click()
    page.wait_for_load_state()
    assert LegalAcceptance.objects.filter(user=user).count() == before + 1
    page.goto(base + "/conta/documentos/")
    assert page.locator("main .card").count() > 1
    active = LegalAcceptance.objects.filter(
        user=user, version__document__kind="health", withdrawn_at__isnull=True
    ).first()
    assert active
    page.locator(f"form[action$='/{active.pk}/retirar/'] button").click()
    page.wait_for_load_state()
    active.refresh_from_db()
    assert active.withdrawn_at


def test_register_csv_from_manage(new_page, base):
    page = new_page(viewport=DESKTOP, persona=ADMIN)
    page.goto(base + f"{C}/xestion/legal/")
    assert "MODELO DE EXEMPLO" in page.locator(".legal-example").first.inner_text()
    with page.expect_download() as info:
        page.get_by_role("link", name="Rexistro de aceptacións").click()
    assert info.value.suggested_filename == "rexistro-aceptacions.csv"


def test_accreditation_blocks_then_allows(new_page, base):
    group = Group.objects.get(name="Grupo novo (sen monitora)")
    sabela = User.objects.get(email="sabela@demo.eira.example")
    assert not MinorsAccreditation.objects.filter(user=sabela).exists()
    page = new_page(viewport=DESKTOP, persona=ADMIN)
    page.goto(base + f"{C}/xestion/actividades/grupo/{group.pk}/")
    page.locator("#monitor-select").select_option(str(sabela.pk))
    page.locator("#monitora button[type=submit]").click()
    page.wait_for_load_state()
    assert "falta marcar a acreditación" in page.locator(".messages").inner_text()
    group.refresh_from_db()
    assert group.monitor_id is None
    member = Membership.objects.get(user=sabela, role="monitor")
    page.goto(base + f"{C}/xestion/actividades/acreditacions/")
    page.locator(f"label[for=acc-{member.pk}]").click()
    page.locator(f"#persoa-{member.pk} button[type=submit]").first.click()
    page.wait_for_load_state()
    page.goto(base + f"{C}/xestion/actividades/grupo/{group.pk}/")
    page.locator("#monitor-select").select_option(str(sabela.pk))
    page.locator("#monitora button[type=submit]").click()
    page.wait_for_load_state()
    group.refresh_from_db()
    assert group.monitor == sabela


def test_provenance_panel_and_region_view(new_page, base):
    page = new_page(viewport=DESKTOP, persona=ADMIN)
    page.goto(base + f"{C}/xestion/procedencia/")
    assert page.locator(".flow-map svg").first.is_visible()
    assert page.locator(".flow-map__line").count() >= 2
    assert "Bustelo" in page.locator("main table").inner_text()
    assert "outras procedencias" in page.locator("main table").inner_text()
    numbers = page.locator(
        "main table tbody tr:not(.flow-others) td.num:nth-child(4)"
    ).all_inner_texts()
    assert numbers and all(int(n) >= 10 for n in numbers)
    region = new_page(viewport=DESKTOP, persona="deputacion@demo.eira.example")
    region.goto(base + "/rexion/marismas/mobilidade/")
    assert "Pontedouro" in region.locator("main").inner_text()
    assert region.locator(".flow-map__line").count() >= 2


def test_neighbour_sees_parish_and_distances(new_page, base):
    page = new_page(viewport=MOBILE, persona=UXIA)
    page.goto(base + f"{C}/app/proximos/")
    section = page.locator("#onde-estou")
    assert "Bustelo" in section.inner_text() and "km" in section.inner_text()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_leeme_linked_from_admin_help(new_page, base):
    page = new_page(viewport=DESKTOP, persona=ADMIN)
    page.locator(".help-pop summary").click()
    page.get_by_role("link", name="Uso e requisitos legais").click()
    page.wait_for_load_state()
    assert "Requisitos legais para despregala" in page.locator("main").inner_text()
    assert "MODELO" not in page.title()
