# SPDX-License-Identifier: EUPL-1.2
"""Capturas automáticas das pantallas clave (móbil, tableta e escritorio) en docs/capturas/v3/pantallas/.
As de v1 quedan en docs/capturas/ como «antes».

python tools/tasks.py screenshots
"""

from pathlib import Path

import pytest
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import AppRequest
from apps.activities.models import Group, Session
from apps.bookings.models import Booking
from apps.facilities.models import Facility
from apps.incidents.models import Incident
from apps.maintenance.models import WorkOrder

from .conftest import DESKTOP, MOBILE, TABLET

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]
OUT = Path(settings.BASE_DIR) / "docs" / "capturas" / "v3" / "pantallas"


def shots():
    c = "/c/vilardeiras"
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    gym = Facility.objects.get(municipality__slug="vilardeiras", kind="gym")
    code_booking = (
        Booking.objects.filter(
            user__email="uxia@demo.eira.example",
            facility=gym,
            status="confirmed",
            end__gt=timezone.now(),
        )
        .order_by("start")
        .first()
    )
    inc = Incident.objects.filter(municipality__slug="vilardeiras", status="work_order").first()
    order = (
        WorkOrder.objects.filter(
            municipality__slug="vilardeiras", assigned_to__email="brais@demo.eira.example"
        )
        .exclude(status="done")
        .first()
    )
    group = Group.objects.filter(municipality__slug="vilardeiras", rpe_scale="omni").first()
    session = Session.objects.filter(group=group, closed_at__isnull=False).order_by("-date").first()
    signup = AppRequest.objects.filter(
        municipality__slug="vilardeiras", invitation__isnull=False
    ).first()
    at = timezone.localtime(code_booking.start + timezone.timedelta(minutes=2)).strftime(
        "%Y-%m-%dT%H:%M"
    )
    return [
        ("01-portada", None, "/"),
        ("02-instalacions", None, f"{c}/"),
        ("03-mapa", None, f"{c}/?vista=mapa"),
        ("04-ficha-grella", "uxia@demo.eira.example", f"{c}/instalacions/{padel.pk}/"),
        (
            "05-reserva-confirmar",
            "uxia@demo.eira.example",
            f"{c}/instalacions/{padel.pk}/reservar/?inicio="
            + (
                timezone.localtime(
                    Booking.objects.filter(facility=padel, status="confirmed")
                    .order_by("-start")
                    .first()
                    .start
                )
                + timezone.timedelta(days=0)
            )
            .isoformat()
            .replace("+", "%2B"),
        ),
        ("06-reserva-codigo", "uxia@demo.eira.example", f"{c}/reservas/{code_booking.pk}/"),
        (
            "07-simulador-pechadura",
            "uxia@demo.eira.example",
            f"/dev/lock-simulator/?device={gym.lock.pk}&at={at}",
        ),
        ("08-as-minas-reservas", "uxia@demo.eira.example", f"{c}/reservas/"),
        ("09-incidencia-nova", "uxia@demo.eira.example", f"{c}/incidencias/nova/"),
        ("10-saude", None, "/saude/"),
        ("11-panel-do-dia", "admin@vilardeiras.demo.eira.example", f"{c}/xestion/"),
        (
            "12-alta-asistida",
            "admin@vilardeiras.demo.eira.example",
            f"{c}/xestion/instalacions/nova/",
        ),
        ("13-indicadores", "admin@vilardeiras.demo.eira.example", f"{c}/xestion/indicadores/"),
        (
            "14-incidencia-xestion",
            "admin@vilardeiras.demo.eira.example",
            f"{c}/xestion/incidencias/{inc.pk}/",
        ),
        (
            "15-calendario-mantemento",
            "admin@vilardeiras.demo.eira.example",
            f"{c}/xestion/mantemento/calendario/",
        ),
        ("16-operario-ordes", "brais@demo.eira.example", f"{c}/operario/"),
        ("17-operario-orde", "brais@demo.eira.example", f"{c}/operario/orde/{order.pk}/"),
        ("18-monitor-hoxe", "antia@demo.eira.example", f"{c}/monitor/"),
        (
            "19-monitor-esforzo",
            "antia@demo.eira.example",
            f"{c}/monitor/sesion/{session.pk}/esforzo/",
        ),
        ("20-observatorio", None, f"{c}/actividades/observatorio/"),
        ("21-deputacion", "deputacion@demo.eira.example", "/rexion/marismas/"),
        ("22-app-inicio", "uxia@demo.eira.example", f"{c}/app/"),
        ("23-solicitar-app", None, f"{c}/app/solicitar/"),
        ("24-instalar-app", None, f"{c}/app/instalar/?codigo=ABCD-2345"),
        ("25-privacidade", "uxia@demo.eira.example", "/conta/privacidade/"),
        ("26-altas-app", "admin@vilardeiras.demo.eira.example", f"{c}/xestion/altas/"),
        (
            "27-folla-qr",
            "admin@vilardeiras.demo.eira.example",
            f"{c}/xestion/altas/{signup.pk}/folla/",
        ),
        ("28-cobros", "admin@vilardeiras.demo.eira.example", f"{c}/xestion/cobros/"),
        ("29-valoracions", "admin@vilardeiras.demo.eira.example", f"{c}/xestion/valoracions/"),
        (
            "30-grupo-fotos",
            "admin@vilardeiras.demo.eira.example",
            f"{c}/xestion/actividades/grupo/{group.pk}/",
        ),
        (
            "31-asistencia-fotos",
            "antia@demo.eira.example",
            f"{c}/monitor/sesion/{session.pk}/asistencia/",
        ),
        ("32-creditos-fotos", None, "/creditos/"),
    ]


@pytest.mark.parametrize(
    "viewport, suffix", [(MOBILE, "movil"), (TABLET, "tableta"), (DESKTOP, "escritorio")]
)
def test_screenshots(new_page, base, viewport, suffix):
    OUT.mkdir(parents=True, exist_ok=True)
    pages = {}
    for name, persona, path in shots():
        if persona not in pages:
            pages[persona] = new_page(viewport=viewport, persona=persona)
        page = pages[persona]
        resp = page.goto(base + path)
        assert resp.status == 200, (name, path, resp.status)
        page.wait_for_load_state("networkidle")
        # Co marco de teléfono ou tableta, a páxina completa engadiría un oco baleiro baixo o marco
        framed = page.evaluate("document.body.classList.contains('framed')")
        page.screenshot(path=str(OUT / f"{name}-{suffix}.png"), full_page=not framed)
    # O momento estrela: o código da reserva abre a pechadura sen conexión
    page = pages["uxia@demo.eira.example"]
    gym = Facility.objects.get(municipality__slug="vilardeiras", kind="gym")
    booking = (
        Booking.objects.filter(
            user__email="uxia@demo.eira.example",
            facility=gym,
            status="confirmed",
            end__gt=timezone.now(),
        )
        .order_by("start")
        .first()
    )
    at = timezone.localtime(booking.start + timezone.timedelta(minutes=2)).strftime(
        "%Y-%m-%dT%H:%M"
    )
    page.goto(f"{base}/dev/lock-simulator/?device={gym.lock.pk}&at={at}")
    page.fill("#code", gym.lock.code_for_booking(booking))
    page.click("text=Probar código")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / f"07b-simulador-aberto-{suffix}.png"), full_page=True)
    for p in pages.values():
        p.close()
