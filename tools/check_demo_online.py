#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
"""Comproba unha demo pública desde fóra, cun navegador de verdade (ver docs/despregamento-demo.md).

python tools/check_demo_online.py https://eira.engramlab.es
python tools/check_demo_online.py https://localhost:18443 --insecure   # certificado local de Caddy
Con --rate-limit gasta o límite de inicio de sesión da IP que fai a proba durante unha hora.
"""

import argparse
import json
import re
import socket
import ssl
import sys
import tempfile
from urllib.parse import urlparse

from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import sync_playwright

MOBILE = {"width": 390, "height": 844}
DESKTOP = {"width": 1280, "height": 900}
TOWNS = ("vilardeiras", "pontedouro")
AXE_RULES = {"runOnly": {"type": "tag", "values": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]}}
results = []


def report(name, ok, detail=""):
    results.append(ok)
    print(f"[{'OK' if ok else 'FALLO'}] {name}{f' · {detail}' if detail else ''}", flush=True)


def check(name, fn):
    """Un fallo nunha comprobación queda no informe e non impide as seguintes."""
    try:
        fn()
    except Exception as exc:
        report(name, False, f"{type(exc).__name__}: {str(exc).splitlines()[0][:200]}")


def check_certificate(base):
    url = urlparse(base)
    context = ssl.create_default_context()
    with socket.create_connection((url.hostname, url.port or 443), timeout=15) as sock:
        with context.wrap_socket(sock, server_hostname=url.hostname) as tls:
            cert = tls.getpeercert()
    issuer = dict(item[0] for item in cert["issuer"]).get("organizationName", "?")
    report("Certificado válido (candado)", True, f"emisor {issuer}, ata {cert['notAfter']}")


def personas(page, base):
    found = []
    for town in TOWNS:
        page.goto(f"{base}/?concello={town}")
        for email in page.locator("form input[name=email]").evaluate_all(
            "e => e.map(i => i.value)"
        ):
            if email not in found:
                found.append(email)
    return found


# v1.5.1: as guías paso a paso márcanse como vistas para que non tapen as pantallas que se proban
TOURS_SEEN = (
    "try{['neighbour','operator','cleaning','monitor','admin','region'].forEach(function(k){"
    "localStorage.setItem('eira-tour-'+k+'-v1','1')})}catch(e){}"
)


def new_page(browser, viewport, insecure, tour=False):
    context = browser.new_context(viewport=viewport, locale="gl-ES", ignore_https_errors=insecure)
    if not tour:
        context.add_init_script(TOURS_SEEN)
    page = context.new_page()
    page.csp_errors = []
    page.on(
        "console",
        lambda m: page.csp_errors.append(m.text) if "Content Security Policy" in m.text else None,
    )
    return page


def login(page, base, email):
    town = "pontedouro" if "pontedouro" in email or email.split("@")[0] in ("rosa", "tino") else ""
    page.goto(f"{base}/?concello={town or 'vilardeiras'}")
    page.locator(f"form:has(input[value='{email}']) button").click()
    page.wait_for_load_state()


def check_profiles(browser, base, insecure):
    page = new_page(browser, DESKTOP, insecure)
    emails = personas(page, base)
    page.context.close()
    report("Perfís atopados na portada", len(emails) >= 10, str(len(emails)))
    for email in emails:
        page = new_page(browser, DESKTOP, insecure)
        login(page, base, email)
        logged = page.locator(".demo-bar__who").count() == 1
        report(f"Entrar como {email}", logged and not page.csp_errors, urlparse(page.url).path)
        page.context.close()


def check_tour(browser, base, insecure):
    """v1.5.1: a guía sae soa a primeira vez con Uxía e non volve saír ao recargar."""
    page = new_page(browser, MOBILE, insecure, tour=True)
    login(page, base, "uxia@demo.eira.example")
    dialog = page.locator("dialog#tour[open]")
    dialog.wait_for(timeout=5000)
    steps = page.locator("#tour-step").inner_text()
    report("Guía de Uxía á primeira entrada", dialog.count() == 1, steps)
    page.locator("[data-tour-close]").click()
    page.reload()
    page.wait_for_load_state()
    report("A guía non volve saír ao recargar", page.locator("dialog#tour[open]").count() == 0)
    page.context.close()


def check_booking(browser, base, insecure):
    page = new_page(browser, MOBILE, insecure)
    page.goto(f"{base}/c/vilardeiras/")
    link = page.locator("main a[href*='/instalacions/']", has_text="pádel").first
    href = link.get_attribute("href")
    login(page, base, "uxia@demo.eira.example")
    page.goto(base + href)
    page.locator(".daypanel:not([hidden]) a.pill[data-pick]").first.click()
    page.click("[data-picksum-go]")
    page.check("#id_accept_rules")
    page.click("main button.btn-lg")
    page.wait_for_load_state()
    if "/dev/tpv/" in page.url:
        page.click("button[value=ok]")
        page.wait_for_load_state()
    page.click("text=Ver o acceso e a reserva")
    page.wait_for_load_state()
    digits = page.locator(".access-code__digits").text_content().replace(" ", "")
    report(
        "Reserva completa (franxa → pago simulado → código)", bool(re.fullmatch(r"\d{6}", digits))
    )
    page.context.close()


def check_videos(browser, base, insecure):
    page = new_page(browser, DESKTOP, insecure)
    external = []
    origin = urlparse(base).netloc
    page.on(
        "request",
        lambda r: external.append(r.url) if urlparse(r.url).netloc not in (origin, "") else None,
    )
    page.goto(base + "/")
    videos = page.locator(".demo-video video")
    report("Aviso na portada", "Restáurase cada noite" in page.locator("main").inner_text())
    report("Hai dous vídeos", videos.count() == 2)
    for i in range(videos.count()):
        video = videos.nth(i)
        video.scroll_into_view_if_needed()
        video.evaluate("v => { v.muted = true; return v.play(); }")
        page.wait_for_function(
            "v => v.currentTime > 0.5", arg=video.element_handle(), timeout=20000
        )
        state = video.evaluate(
            "v => ({src: v.currentSrc, duration: v.duration, width: v.videoWidth})"
        )
        report(
            f"Vídeo {i + 1} reprodúcese",
            state["width"] > 0,
            f"{urlparse(state['src']).path}, {state['duration']:.0f} s",
        )
        video.evaluate("v => v.pause()")
    report("Portada sen peticións externas", not external, ", ".join(external[:3]))
    page.context.close()


def check_pwa(playwright, base, insecure):
    args = ["--ignore-certificate-errors"] if insecure else []
    with tempfile.TemporaryDirectory() as profile:
        context = playwright.chromium.launch_persistent_context(
            profile, viewport=MOBILE, ignore_https_errors=insecure, args=args
        )
        page = context.pages[0]
        page.goto(base + "/")
        manifest = json.loads(context.request.get(base + "/manifest.webmanifest").text())
        sizes = {icon.get("sizes") for icon in manifest.get("icons", [])}
        report(
            "Manifesto da PWA",
            manifest.get("display") == "standalone" and {"192x192", "512x512"} <= sizes,
            f"{manifest.get('name')}, {sorted(sizes)}",
        )
        scope = page.evaluate(
            "async () => (await navigator.serviceWorker.ready).scope", None
        )  # espera a que se active
        report("Service worker activo", bool(scope), scope)
        page.reload()
        cdp = context.new_cdp_session(page)
        errors = cdp.send("Page.getInstallabilityErrors")["installabilityErrors"]
        names = [e["errorId"] for e in errors]
        report("Chromium dá a PWA por instalable", not names, ", ".join(names))
        context.close()


def check_axe(browser, base, insecure):
    axe = Axe()
    screens = [
        ("Portada con vídeos", DESKTOP, None, "/"),
        ("Portada en móbil", MOBILE, None, "/"),
        ("Concello", MOBILE, None, "/c/vilardeiras/"),
        ("As miñas reservas", MOBILE, "uxia@demo.eira.example", "/c/vilardeiras/reservas/"),
        (
            "Panel de xestión",
            DESKTOP,
            "admin@vilardeiras.demo.eira.example",
            "/c/vilardeiras/xestion/",
        ),
        ("Operario", MOBILE, "brais@demo.eira.example", "/c/vilardeiras/operario/"),
    ]
    for name, viewport, persona, path in screens:
        page = new_page(browser, viewport, insecure)
        if persona:
            login(page, base, persona)
        page.goto(base + path)
        violations = axe.run(page, options=AXE_RULES).response["violations"]
        ids = [f"{v['id']} ({len(v['nodes'])})" for v in violations]
        report(f"axe: {name}", not violations, ", ".join(ids))
        page.context.close()


def check_rate_limit(browser, base, insecure):
    page = new_page(browser, DESKTOP, insecure)
    blocked_at = None
    for i in range(1, 30):
        page.goto(base + "/acceso/")
        page.fill("#id_email", f"limite{i}@demo.eira.example")
        page.click("main button[type=submit]")
        page.wait_for_load_state()
        if "Demasiados intentos" in page.locator("main").inner_text():
            blocked_at = i
            break
    report("Límite no inicio de sesión", blocked_at is not None, f"bloquea no envío {blocked_at}")
    page.context.close()
    context = browser.new_context(
        ignore_https_errors=insecure, extra_http_headers={"X-Forwarded-For": "198.51.100.7"}
    )
    page = context.new_page()
    page.goto(base + "/acceso/")
    page.fill("#id_email", "falsificada@demo.eira.example")
    page.click("main button[type=submit]")
    page.wait_for_load_state()
    report(
        "Falsificar X-Forwarded-For non o evita",
        "Demasiados intentos" in page.locator("main").inner_text(),
    )
    context.close()


def check_real_mail_rejected(browser, base, insecure):
    page = new_page(browser, DESKTOP, insecure)
    page.goto(base + "/acceso/")
    page.fill("#id_email", "alguen@correo.test")
    page.click("main button[type=submit]")
    page.wait_for_load_state()
    report("Rexeita correos reais", "correo real" in page.locator("main").inner_text())
    page.context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base")
    parser.add_argument("--insecure", action="store_true", help="acepta o certificado local")
    parser.add_argument("--rate-limit", action="store_true", help="proba tamén o límite de acceso")
    options = parser.parse_args()
    base, insecure = options.base.rstrip("/"), options.insecure

    if not insecure:
        check("Certificado válido (candado)", lambda: check_certificate(base))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        check("Perfís", lambda: check_profiles(browser, base, insecure))
        check("Guía", lambda: check_tour(browser, base, insecure))
        check("Reserva completa", lambda: check_booking(browser, base, insecure))
        check("Vídeos", lambda: check_videos(browser, base, insecure))
        check("PWA", lambda: check_pwa(playwright, base, insecure))
        check("axe", lambda: check_axe(browser, base, insecure))
        check("Correos reais", lambda: check_real_mail_rejected(browser, base, insecure))
        if options.rate_limit:
            check("Límite", lambda: check_rate_limit(browser, base, insecure))
        browser.close()
    print(f"\n{sum(results)} de {len(results)} comprobacións correctas")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
