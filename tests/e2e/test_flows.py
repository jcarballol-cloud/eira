# SPDX-License-Identifier: EUPL-1.2
"""Percorridos completos no navegador."""

import json
import re

import pytest
from django.utils import timezone

from apps.bookings.models import Booking
from apps.facilities.models import Facility
from apps.maintenance.models import WorkOrder

from .conftest import MOBILE, demo_url

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]


def test_keyboard_skip_link_and_lang(new_page, base):
    page = new_page()
    page.goto(base + "/c/vilardeiras/")
    assert page.locator("html").get_attribute("lang") == "gl"
    page.keyboard.press("Tab")
    focused = page.evaluate("document.activeElement.className")
    assert "skip-link" in focused
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.id") == "main"


def test_email_login_and_booking_with_offline_code(new_page, base):
    """Acceso por código (bandexa simulada) → reserva → pago simulado → código → pechadura abre."""
    page = new_page(viewport=MOBILE)
    page.goto(base + "/acceso/")
    page.fill("#id_email", "nova.vecina@example.org")
    page.click("main button[type=submit]")
    page.goto(base + "/dev/mailbox/?para=nova.vecina@example.org")
    code = re.search(r"\b(\d{6})\b", page.locator(".mail__body").first.inner_text()).group(1)
    page.goto(base + "/acceso/codigo/")
    page.fill("#id_code", code)
    page.click("main button[type=submit]")
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    page.goto(f"{base}/c/vilardeiras/instalacions/{padel.pk}/")
    # Primeira franxa libre na vista móbil (lista por días)
    page.locator(".daypanel:not([hidden]) a.pill[data-pick]").first.click()
    page.click("[data-picksum-go]")
    page.check("#id_accept_rules")
    page.click("button.btn-lg")
    assert "/dev/tpv/" in page.url
    page.click("button[value=ok]")
    page.wait_for_load_state()
    page.click("text=Ver o acceso e a reserva")
    page.wait_for_load_state()
    access_code = page.locator(".access-code").inner_text().strip()
    assert re.fullmatch(r"\d{6}", access_code)
    booking = Booking.objects.get(user__email="nova.vecina@example.org")
    assert booking.status == "confirmed"
    # Simulador: o reloxo vai á hora de inicio e o código abre
    page.click("text=Probalo no simulador de pechadura")
    page.fill("#code", access_code)
    page.click("text=Probar código")
    assert "ABERTO" in page.locator(".lock-screen").inner_text()
    # Fóra da xanela: denegado
    late = timezone.localtime(booking.end + timezone.timedelta(minutes=20)).strftime(
        "%Y-%m-%dT%H:%M"
    )
    page.fill("#at", late)
    page.click("text=Aplicar")
    page.fill("#code", access_code)
    page.click("text=Probar código")
    assert "DENEGADO" in page.locator(".lock-screen").inner_text()


def test_health_data_never_leaves_device(new_page, base):
    page = new_page()
    sent = []
    page.on("request", lambda r: sent.append((r.method, r.url, r.post_data or "")))
    page.goto(base + "/saude/")
    page.fill("#h-age", "71")
    page.fill("#h-weight", "83.5")
    page.fill("#h-minutes", "95")
    page.fill("#h-session", "75")
    page.click("text=Gardar e ver consellos")
    page.wait_for_timeout(300)
    stored = json.loads(page.evaluate("localStorage.getItem('eira-health-v1')"))
    assert stored["weight"] == "83.5"
    assert (
        "415–585" in page.locator("#h-advice").inner_text()
        or "400" in page.locator("#h-advice").inner_text()
    )
    page.reload()
    page.wait_for_load_state("networkidle")
    assert page.input_value("#h-age") == "71"
    for method, url, body in sent:
        assert method == "GET", (method, url)
        assert "83.5" not in url and "83.5" not in body and "71" not in url.split("/")[-1]


def test_htmx_week_navigation_announces(new_page, base):
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    page = new_page(bypass_csp=True)  # wait_for_function avalía JS
    page.goto(f"{base}/c/vilardeiras/instalacions/{padel.pk}/")
    page.click("a[aria-label='Semana seguinte']")
    page.wait_for_function("document.getElementById('live').textContent.length > 0")
    assert "Semana" in page.locator("#live").text_content()
    assert "semana=" in page.url
    # despois do intercambio HTMX, a tira de días volve funcionar
    page.wait_for_selector(".daystrip:not([hidden])")
    assert page.locator(".daypanel:not([hidden])").count() == 1


def test_operator_offline_queue_syncs(new_page, base):
    order = (
        WorkOrder.objects.filter(
            municipality__slug="vilardeiras", assigned_to__email="brais@demo.eira.example"
        )
        .exclude(status="done")
        .first()
    )
    page = new_page(viewport=MOBILE, persona="brais@demo.eira.example", bypass_csp=True)
    logs = []
    page.on("console", lambda m: logs.append(m.text))
    page.on("pageerror", lambda e: logs.append(str(e)))
    page.goto(f"{base}/c/vilardeiras/operario/orde/{order.pk}/")
    page.wait_for_load_state("networkidle")
    page.context.set_offline(True)
    page.fill("#id_closing_notes", "Feito sen cobertura")
    page.click("button[value=close]")
    page.wait_for_selector("[data-offline-note]:not([hidden])", timeout=5000) if not logs else None
    assert not logs, logs
    assert page.locator("[data-queue-count] [data-n]").inner_text() == "1"
    order.refresh_from_db()
    assert order.status != "done"
    page.context.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    page.wait_for_function(
        "document.querySelector('[data-queue-count]').hidden === true", timeout=10000
    )
    order.refresh_from_db()
    assert order.status == "done" and order.closing_notes == "Feito sen cobertura"


def test_spanish_interface(new_page, base):
    page = new_page()
    page.goto(base + "/c/vilardeiras/")
    page.click("button[lang=es]")
    page.wait_for_load_state()
    assert page.locator("html").get_attribute("lang") == "es"
    assert page.locator("h1").inner_text() == "Instalaciones deportivas"


def test_pitch_script(new_page, base):
    """O guión de docs/demo/guion-demo.md: checklist «non» → incidencia → orde → peche → aviso."""
    from apps.incidents.models import Incident
    from apps.notifications.models import Notification

    uxia = new_page(viewport=MOBILE, persona="uxia@demo.eira.example")
    uxia.goto(base + "/c/vilardeiras/reservas/")
    uxia.click("text=Checklist de peche")
    uxia.check("#id_door_ok_1")  # «Non»
    uxia.check("#id_all_ok_0")
    uxia.click("main button[type=submit]")
    assert "Creamos a incidencia" in uxia.locator(".messages").inner_text()
    inc = Incident.objects.filter(
        source="checklist", reporter__email="uxia@demo.eira.example"
    ).latest("created_at")

    admin = new_page(persona="admin@vilardeiras.demo.eira.example")
    admin.goto(base + "/c/vilardeiras/xestion/")
    admin.click(f"a[href$='/xestion/incidencias/{inc.pk}/']")
    admin.click("button:has-text('Validar')")
    admin.select_option("#id_assigned_to", label="Brais (mantemento)")
    admin.click("button:has-text('Crear orde')")
    inc.refresh_from_db()
    assert inc.status == "work_order"

    brais = new_page(viewport=MOBILE, persona="brais@demo.eira.example")
    brais.goto(base + "/c/vilardeiras/operario/")
    brais.click(f"text=Incidencia #{inc.pk}")
    brais.locator("input[name=done]").first.check()
    brais.click("button[value=close]")
    inc.refresh_from_db()
    assert inc.status == "resolved"
    assert Notification.objects.filter(
        user__email="uxia@demo.eira.example", title__startswith="Arranxado"
    ).exists()

    admin.goto(base + "/c/vilardeiras/xestion/indicadores/")
    assert admin.locator(".hbar-fill").count() > 0


def test_request_app_by_email_install_and_first_open(new_page, base):
    """v2 F2: solicitar a app → correo con ligazón e código → instalar → entrar → código xa cuberto."""
    email = "solicitude.e2e@example.org"
    page = new_page(viewport=MOBILE)
    page.goto(base + "/c/vilardeiras/")
    page.click("text=Solicita a app de deportes")
    page.fill("#id_name", "Persoa E2E")
    page.fill("#id_email", email)
    page.fill("#id_birth_year", "1991")
    page.fill("#id_postcode", "15999")
    page.check("#id_resident")
    page.click("main button[type=submit]")
    page.wait_for_selector("text=Mira o teu correo")
    page.goto(base + f"/dev/mailbox/?para={email}")
    body = page.locator(".mail__body").first.inner_text()
    link = re.search(r"(http\S+/app/instalar/\?codigo=(\S+))", body)
    code = link.group(2)
    page.goto(link.group(1))
    assert code in page.locator("main").inner_text()
    page.get_by_role("link", name="Abrir a app").click()
    # Primeira apertura: entrar co correo
    page.fill("#id_email", email)
    page.click("main button[type=submit]")
    page.goto(base + f"/dev/mailbox/?para={email}")
    otp = re.search(r"\b(\d{6})\b", page.locator(".mail__body").first.inner_text()).group(1)
    page.goto(base + "/acceso/codigo/")
    page.fill("#id_code", otp)
    page.click("main button[type=submit]")
    page.wait_for_url("**/app/benvida/**")
    assert page.input_value("#code") == code
    page.click("main button[type=submit]")
    page.wait_for_selector("text=Tes fillos ou persoas ao teu cargo?")


def test_booking_shows_personal_recommendations_computed_on_device(new_page, base):
    """v2 F6: dentro da reserva, consellos concretos co perfil do dispositivo e sen enviar o peso."""
    upcoming = (
        Booking.objects.filter(
            user__email="uxia@demo.eira.example", status="confirmed", start__gt=timezone.now()
        )
        .order_by("start")
        .first()
    )
    page = new_page(viewport=MOBILE)
    sent = []
    page.on("request", lambda r: sent.append((r.url, r.post_data or "")))
    page.goto(demo_url(base, "uxia@demo.eira.example"))
    page.locator("form:has(input[value='uxia@demo.eira.example']) button").click()
    page.wait_for_load_state("networkidle")
    page.evaluate(
        """localStorage.setItem('eira-health-v1', JSON.stringify({age: '27', weight: '61.5', minutes: '60'}))"""
    )
    page.goto(f"{base}/c/vilardeiras/reservas/{upcoming.pk}/")
    box = page.locator("[data-health-booking]")
    box.locator(".rec").first.wait_for()
    text = box.inner_text()
    assert "Auga antes" in text and "300–450 ml" in text and "Bebe arredor das" in text
    assert "A túa semana" in text and "Fonte: ACSM 2007" in text
    assert box.locator("[data-health-cta]").is_hidden()
    for url, body in sent:
        assert "61.5" not in url and "61.5" not in body
