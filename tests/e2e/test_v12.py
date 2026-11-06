# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · E2E das aportacións da terceira rolda: Aviso e Alerta, protocolo, ficha ampliada…"""

import pytest

from apps.facilities.models import Facility
from apps.safety.models import Alert

from .conftest import DESKTOP, MOBILE

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]
C = "/c/vilardeiras"
UXIA = "uxia@demo.eira.example"
ADMIN = "admin@vilardeiras.demo.eira.example"


def test_alert_accident_opens_protocol_with_112_and_aed(new_page, base):
    hall = Facility.objects.get(name="Pavillón municipal de Vilardeiras")
    before = Alert.objects.count()
    page = new_page(viewport=MOBILE, persona=UXIA)
    page.goto(f"{base}{C}/seguridade/")
    notice = page.locator(".big-choice__btn--notice")
    alert = page.locator(".big-choice__btn--alert")
    assert notice.is_visible() and alert.is_visible()
    # Diferenciados por forma (cadrado e octógono) e texto, non só pola cor
    assert page.locator(".big-choice__shape--square").count() >= 1
    assert page.locator(".big-choice__shape--octagon").count() >= 1
    page.goto(f"{base}{C}/seguridade/alerta/?instalacion={hall.pk}")
    page.get_by_role("button", name="Accidente deportivo").click()
    page.wait_for_load_state()
    assert "/seguridade/accidente/" in page.url
    assert page.locator(".protocol__step").count() == 5
    assert page.locator(".protocol a[href='tel:112']").count() >= 1
    assert "Recepción" in page.locator(".aed-box").inner_text()
    assert Alert.objects.count() == before + 1
    # Rexistro mínimo do accidente
    page.get_by_role("link", name="Rexistrar o accidente").click()
    page.check("input[name=kind][value=fall]")
    page.check("input[name=severity][value=mild]")
    page.check("input[name=reporter_role][value=user]")
    page.get_by_role("button", name="Rexistrar").click()
    assert "Accidente rexistrado" in page.locator("main").inner_text()


def test_security_emergency_shows_big_112(new_page, base):
    page = new_page(viewport=MOBILE, persona=UXIA)
    page.goto(f"{base}{C}/seguridade/alerta/")
    page.get_by_role("button", name="Emerxencia de seguridade").click()
    page.wait_for_load_state()
    big = page.locator(".emergency-call--huge")
    assert big.is_visible() and big.get_attribute("href") == "tel:112"
    assert "Avisamos ao concello" in page.locator("main").inner_text()


def test_facility_sheet_filters_and_detail(new_page, base):
    page = new_page(viewport=DESKTOP)
    page.goto(f"{base}{C}/?aed=on")
    names = page.locator(".facility-card h3").all_inner_texts()
    assert names == ["Pavillón municipal de Vilardeiras"]
    page.goto(f"{base}{C}/?full_access=on")
    assert "Pista de pádel da Pereira" not in page.locator("main").inner_text()
    hall = Facility.objects.get(name="Pavillón municipal de Vilardeiras")
    page.goto(f"{base}{C}/instalacions/{hall.pk}/")
    text = page.locator("main").inner_text()
    for word in ("Accesibilidade detallada", "Mobilidade sostible", "DESA (desfibrilador)"):
        assert word in text


def test_annual_survey_answer(new_page, base):
    from apps.surveys.models import SurveyResponse

    before = SurveyResponse.objects.count()
    page = new_page(viewport=MOBILE, persona=UXIA)
    page.goto(f"{base}{C}/app/")
    page.get_by_role("link", name="Enquisa de satisfacción").first.click()
    page.locator("label[for=id_nps_9]").click()
    page.locator("label[for=id_cleanliness_3]").click()
    page.get_by_role("button", name="Enviar").click()
    assert "Xa respondiches" in page.locator("main").inner_text()
    assert SurveyResponse.objects.count() == before + 1


def test_busy_slot_offers_waitlist(new_page, base):
    page = new_page(viewport=MOBILE, persona=UXIA)
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    page.goto(f"{base}{C}/instalacions/{padel.pk}/")
    assert page.locator(".how-to-book li").count() == 3
    entry = uxia_waitlist_entry()
    page.goto(f"{base}{C}/reservas/")
    assert "Listas de espera" in page.locator("main").inner_text()
    page.get_by_role("link", name=padel.name).last.click()
    assert f"/lista-de-espera/{entry.pk}/" in page.url


def test_open_game_join_request(new_page, base):
    from apps.bookings.models import GameJoin, OpenGame

    game = OpenGame.objects.filter(municipality__slug="vilardeiras", joins__isnull=True).first()
    page = new_page(viewport=MOBILE, persona=UXIA)
    page.goto(f"{base}{C}/reservas/partidas/{game.pk}/")
    assert "@" not in page.locator("main").inner_text()  # nunca correos
    page.check("#g-consent")
    page.get_by_role("button", name="Quero unirme").click()
    assert GameJoin.objects.filter(game=game, user__email=UXIA, status="pending").exists()


def test_member_card_qr_and_reader(new_page, base):
    from apps.members.models import MemberCard
    from apps.members.services import live_token

    page = new_page(viewport=MOBILE, persona=UXIA)
    page.goto(f"{base}{C}/carne/")
    assert page.locator(".card-qr__code svg").count() == 1
    assert "Abono xeral" in page.locator(".member-card").inner_text()
    card = MemberCard.objects.get(user__email=UXIA, municipality__slug="vilardeiras")
    desk = new_page(viewport=DESKTOP, persona=ADMIN)
    desk.goto(f"{base}{C}/xestion/carne/")
    desk.fill("#qr", live_token(card))
    desk.get_by_role("button", name="Ler").click()
    assert "Abono xeral" in desk.locator(".card-status").inner_text()
