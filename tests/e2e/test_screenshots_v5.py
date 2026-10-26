# SPDX-License-Identifier: EUPL-1.2
"""v5 · Capturas de cada bloque (A–H) en móbil e escritorio → docs/capturas/v5/.

    pytest tests/e2e/test_screenshots_v5.py -m video

Non forma parte da CI (marca `video`)."""

from pathlib import Path

import pytest
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import DataBreach
from apps.bookings.models import Booking
from apps.bookings.services import slot_starts
from apps.facilities.models import Facility
from apps.maintenance.models import WorkOrder

from .conftest import DESKTOP, MOBILE

pytestmark = [pytest.mark.e2e, pytest.mark.video, pytest.mark.django_db(transaction=False)]
OUT = Path(settings.BASE_DIR) / "docs" / "capturas" / "v5"
V, P = "/c/vilardeiras", "/c/pontedouro"


def shots():
    pon_padel = Facility.objects.get(name="Pista de pádel 1 da Ribeira")
    vil_padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    night = next(
        s
        for d in range(2, 9)
        for s in slot_starts(pon_padel, timezone.localdate() + timezone.timedelta(days=d))
        if timezone.localtime(s).hour >= 20
    )
    approval = Booking.objects.filter(
        status="pending_approval", municipality__slug="vilardeiras"
    ).first()
    states = Booking.objects.filter(start_state_ok=False).first()
    upcoming = (
        Booking.objects.filter(
            user__email="uxia@demo.eira.example", status="confirmed", start__gt=timezone.now()
        )
        .order_by("start")
        .first()
    )
    review = WorkOrder.objects.filter(kind="safety_review", facility=vil_padel).first()
    breach = DataBreach.objects.filter(municipality__slug="vilardeiras").first()
    uxia, admin = "uxia@demo.eira.example", "admin@vilardeiras.demo.eira.example"
    book = f"{P}/instalacions/{pon_padel.pk}/reservar/?inicio=" + night.isoformat().replace(
        "+", "%2B"
    )
    return [
        ("A-1-selector-concello", uxia, f"{V}/"),
        ("A-2-concellos-proximos", uxia, f"{V}/app/proximos/"),
        ("A-3-reserva-pontedouro-tarifa-e-luz", uxia, book),
        ("A-4-avisos-concellos-proximos", uxia, f"{V}/avisos/"),
        ("B-1-ficha-seguridade", None, f"{V}/instalacions/{vil_padel.pk}/"),
        ("B-2-cartel-porta", admin, f"{V}/xestion/instalacions/{vil_padel.pk}/qr/"),
        ("C-1-desglose-luz-e-formas-de-pagamento", uxia, book),
        ("C-2-para-aprobar", admin, f"{V}/xestion/reservas/{approval.pk}/"),
        ("C-3-conciliacion-por-forma-de-pagamento", admin, f"{V}/xestion/cobros/"),
        ("C-4-bonos", uxia, f"{V}/reservas/bonos/"),
        ("D-1-estado-ao-entrar", uxia, f"{V}/reservas/{upcoming.pk}/estado-inicial/"),
        ("D-2-estado-entrar-e-sair", admin, f"{V}/xestion/reservas/{states.pk}/"),
        ("E-1-seguridade-112", uxia, f"{V}/seguridade/"),
        ("E-2-guia-axuda", uxia, "/axuda/"),
        ("E-3-menu-basico", admin, f"{V}/xestion/"),
        ("F-1-quen-custodia-os-datos", None, f"{V}/privacidade/datos/"),
        ("F-2-rexistro-brechas", admin, f"{V}/xestion/privacidade/brechas/"),
        (
            "F-3-comunicacion-brecha",
            admin,
            f"{V}/xestion/privacidade/brechas/{breach.pk}/comunicacion/",
        ),
        ("G-1-indice-panel", admin, f"{V}/xestion/"),
        ("G-2-indice-deputacion", "deputacion@demo.eira.example", "/rexion/marismas/"),
        ("H-1-revision-seguridade", admin, f"{V}/xestion/ordes/{review.pk}/"),
    ]


@pytest.mark.parametrize("viewport,label", [(MOBILE, "movil"), (DESKTOP, "escritorio")])
def test_v5_screenshots(new_page, base, viewport, label):
    OUT.mkdir(parents=True, exist_ok=True)
    pages = {}
    for name, persona, path in shots():
        page = pages.get(persona)
        if page is None:
            page = pages[persona] = new_page(viewport=viewport, persona=persona)
        page.goto(f"{base}{path}{'&' if '?' in path else '?'}marco=0")
        page.wait_for_load_state("networkidle")
        if name == "E-2-guia-axuda":
            page.locator(".help-pop > summary").first.click()
        # A app desprázase dentro de .shell-main: amplíase a xanela ao alto do contido
        height = page.evaluate(
            "Math.max(document.documentElement.scrollHeight,"
            " (document.querySelector('.shell-main')||{}).scrollHeight||0)"
        )
        page.set_viewport_size({"width": viewport["width"], "height": min(int(height) + 120, 6000)})
        page.screenshot(path=OUT / f"{name}-{label}.png", full_page=True)
        page.set_viewport_size(viewport)
