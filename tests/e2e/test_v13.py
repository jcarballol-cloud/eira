# SPDX-License-Identifier: EUPL-1.2
"""v1.3 · E2E: dobre factor (activación, códigos de recuperación e segundo paso ao entrar), rexistro
de auditoría e resumo da avaliación de impacto. axe en claro e escuro nas pantallas novas."""

import re

import pyotp
import pytest
from axe_playwright_python.sync_playwright import Axe

from apps.accounts.models import AuditLog, Membership, Role, TwoFactorDevice, User
from apps.tenants.models import Municipality

from .conftest import DESKTOP, MOBILE
from .test_accessibility import RULES, format_violations

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]
AXE = Axe()
C = "/c/vilardeiras"
ADMIN = "admin@vilardeiras.demo.eira.example"
PON_ADMIN = "admin@pontedouro.demo.eira.example"


def _axe(page, label, failures):
    page.wait_for_load_state("networkidle")
    results = AXE.run(page, options=RULES)
    if results.violations_count:
        failures.append(f"{label}\n{format_violations(results)}")


def _email_login(page, base, email):
    page.goto(base + "/acceso/")
    page.fill("#id_email", email)
    page.click("main button[type=submit]")
    page.goto(base + f"/dev/mailbox/?para={email}")
    code = re.search(r"\b(\d{6})\b", page.locator(".mail__body").first.inner_text()).group(1)
    page.goto(base + "/acceso/codigo/")
    page.fill("#id_code", code)
    page.click("main button[type=submit]")
    page.wait_for_load_state()


def test_two_factor_setup_recovery_and_login(new_page, base):
    email = "xestora.2fa@example.org"
    muni = Municipality.objects.get(slug="vilardeiras")
    user, _c = User.objects.get_or_create(email=email, defaults={"display_name": "Xestora 2FA"})
    Membership.objects.get_or_create(user=user, municipality=muni, role=Role.ADMIN)
    TwoFactorDevice.objects.filter(user=user).delete()
    failures = []
    page = new_page(viewport=DESKTOP)
    _email_login(page, base, email)
    assert "/xestion/" in page.url  # sen dobre factor, entra coma sempre
    page.goto(base + "/conta/seguridade/")
    _axe(page, "/conta/seguridade/ (sen activar)", failures)
    page.get_by_role("button", name="Activar o dobre factor").click()
    page.wait_for_load_state()
    assert page.locator(".qr-box svg").is_visible()
    _axe(page, "/conta/seguridade/ (QR)", failures)
    secret = page.locator("[data-secret]").inner_text().replace(" ", "")
    page.fill("#id_code", pyotp.TOTP(secret).now())
    page.get_by_role("button", name="Confirmar e activar").click()
    page.wait_for_load_state()
    assert page.url.endswith("/conta/seguridade/codigos/")
    codes = page.locator(".recovery-codes code").all_inner_texts()
    assert len(codes) == 10
    _axe(page, "/conta/seguridade/codigos/", failures)
    # Saír e volver entrar: agora pide o segundo paso
    page.goto(base + "/conta/")
    page.locator("form[action='/acceso/sair/'] button").first.click()
    _email_login(page, base, email)
    assert page.url.endswith("/acceso/dobre-factor/")
    _axe(page, "/acceso/dobre-factor/", failures)
    page.goto(base + f"{C}/xestion/")
    assert page.url.endswith("/acceso/dobre-factor/")  # bloqueado ata o segundo paso
    page.fill("#id_code", codes[0])
    page.click("main form:not([action]) button[type=submit]")
    page.wait_for_load_state()
    assert "/xestion/" in page.url
    assert "código de recuperación" in page.locator("main").inner_text()
    # O rexistro de auditoría mostra o que pasou
    page.goto(base + f"{C}/xestion/privacidade/auditoria/?categoria=contas")
    text = page.locator("main").inner_text()
    assert "Dobre factor activado" in text and "Segundo factor correcto" in text
    # Tema escuro nas pantallas da conta e no segundo paso
    dark = new_page(viewport=MOBILE, color_scheme="dark")
    _email_login(dark, base, email)
    _axe(dark, "/acceso/dobre-factor/ (escuro)", failures)
    dark.fill("#id_code", codes[1])
    dark.click("main form:not([action]) button[type=submit]")
    dark.goto(base + "/conta/seguridade/")
    _axe(dark, "/conta/seguridade/ (escuro, activado)", failures)
    assert not failures, "\n\n".join(failures)


def test_council_requires_two_factor_for_admin(new_page, base):
    muni = Municipality.objects.get(slug="pontedouro")
    muni.require_2fa_admin = True
    muni.save(update_fields=["require_2fa_admin"])
    try:
        page = new_page(viewport=DESKTOP, persona=PON_ADMIN)
        page.goto(base + "/c/pontedouro/xestion/")
        assert "/conta/seguridade/?obrigatorio=1" in page.url
        assert "Pontedouro" in page.locator("div.alert-warn").inner_text()
    finally:
        muni.require_2fa_admin = False
        muni.save(update_fields=["require_2fa_admin"])


def test_audit_log_records_downloads(new_page, base):
    page = new_page(viewport=DESKTOP, persona=ADMIN)
    before = AuditLog.objects.filter(action="export.download").count()
    resp = page.request.get(base + f"{C}/xestion/indicadores/?csv=ocupacion")
    assert resp.status == 200
    assert AuditLog.objects.filter(action="export.download").count() == before + 1
    page.goto(base + f"{C}/xestion/privacidade/auditoria/?categoria=exportacions")
    assert "ocupacion.csv" in page.locator("main").inner_text()
    page.select_option("#categoria", "tarifas")
    page.get_by_role("button", name="Filtrar").click()
    assert "categoria=tarifas" in page.url


def test_dpia_summary_from_custody_page(new_page, base):
    page = new_page(viewport=MOBILE)
    page.goto(base + f"{C}/privacidade/datos/")
    page.get_by_role("link", name="Ver a avaliación de impacto (EIPD)").click()
    page.wait_for_load_state()
    assert page.url.endswith("/privacidade/avaliacion-impacto/")
    assert page.locator(".custody-item").count() == 6
