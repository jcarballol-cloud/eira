# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · Capturas dos bloques A–H en móbil e escritorio (e en escuro en A, D e H)
→ docs/capturas/v1.2/.

    pytest tests/e2e/test_screenshots_v12.py -m video

Non forma parte da CI (marca `video`)."""

import datetime as dt
from pathlib import Path

import pytest
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import User
from apps.activities.models import Group, Session
from apps.bookings.models import Booking, OpenGame, SlotRelease
from apps.facilities.models import Facility
from apps.members.models import MemberCard
from apps.members.services import live_token
from apps.safety.models import ClosingEscalation
from apps.surveys.models import Survey

from .conftest import DESKTOP, MOBILE

pytestmark = [pytest.mark.e2e, pytest.mark.video, pytest.mark.django_db(transaction=False)]
OUT = Path(settings.BASE_DIR) / "docs" / "capturas" / "v1.2"
V = "/c/vilardeiras"
UXIA = "uxia@demo.eira.example"
ADMIN = "admin@vilardeiras.demo.eira.example"
ANTIA = "antia@demo.eira.example"
DEP = "deputacion@demo.eira.example"


def _uxia_booking(facility, start):
    uxia = User.objects.get(email=UXIA)
    return Booking.objects.create(
        municipality=facility.municipality,
        facility=facility,
        user=uxia,
        start=start,
        end=start + dt.timedelta(minutes=facility.slot_minutes),
        status=Booking.Status.CONFIRMED,
        price_cents=300,
        paid_cents=300,
        rules_version=facility.current_rules(),
        rules_accepted_at=timezone.now(),
    )


def shots():
    hall = Facility.objects.get(name="Pavillón municipal de Vilardeiras")
    court = Facility.objects.get(name="Pista polideportiva de Bustelo")
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    now = timezone.now()
    live = _uxia_booking(court, now - dt.timedelta(minutes=20))  # reserva en curso
    soon = _uxia_booking(hall, now + dt.timedelta(hours=5))  # dentro das 24 h: Confirmo/Cancelo
    esc = ClosingEscalation.objects.filter(municipality__slug="vilardeiras").first()
    released = SlotRelease.objects.filter(municipality__slug="vilardeiras").first()
    surveys = Survey.objects.filter(municipality__slug="vilardeiras").order_by("year")
    game = OpenGame.objects.filter(municipality__slug="vilardeiras", joins__isnull=False).first()
    next_padel = (
        Booking.objects.filter(user__email=UXIA, facility=padel, status="confirmed")
        .exclude(open_game__isnull=False)
        .order_by("start")
        .first()
    )
    card = MemberCard.objects.get(user__email=UXIA, municipality__slug="vilardeiras")
    group = Group.objects.filter(municipality__slug="vilardeiras", monitor__email=ANTIA).first()
    session = Session.objects.filter(group=group).order_by("-date").first()
    return [
        # A · Aviso e Alerta
        ("A1-aviso-e-alerta", UXIA, f"{V}/seguridade/", True),
        ("A2-alerta-duas-opcions", UXIA, f"{V}/seguridade/alerta/?instalacion={hall.pk}", True),
        ("A3-protocolo-accidente", UXIA, f"{V}/seguridade/accidente/{hall.pk}/", True),
        ("A4-emerxencia-112", UXIA, f"{V}/seguridade/emerxencia/", False),
        ("A5-botons-na-reserva-en-curso", UXIA, f"{V}/reservas/{live.pk}/", True),
        ("A6-rexistro-accidentes", ADMIN, f"{V}/xestion/seguridade/accidentes/", False),
        ("A7-tableta-alerta", ANTIA, f"{V}/monitor/sesion/{session.pk}/asistencia/", False),
        # B · Peche sen confirmar
        ("B1-peche-persoa-responsable", None, f"{V}/seguridade/peche/{esc.token}/", False),
        ("B2-alertas-e-peches", ADMIN, f"{V}/xestion/seguridade/", False),
        ("B3-simulador-estado-porta", None, "/dev/lock-simulator/", False),
        # C · Ficha ampliada
        ("C1-ficha-accesibilidade-desa", None, f"{V}/instalacions/{hall.pk}/", False),
        ("C2-busca-accesible-aparcabicis", None, f"{V}/?full_access=on&bikes=on", False),
        ("C3-edicion-ficha", ADMIN, f"{V}/xestion/instalacions/{hall.pk}/", False),
        # D · Rendemento
        ("D1-panel-rendemento", ADMIN, f"{V}/xestion/instalacions/{hall.pk}/rendemento/", True),
        ("D2-rendemento-todas", ADMIN, f"{V}/xestion/rendemento/", True),
        ("D3-comparativa-deputacion", DEP, "/rexion/marismas/", False),
        # E · NPS
        ("E1-enquisa-anual", UXIA, f"{V}/enquisa/", False),
        ("E2-resultados-nps", ADMIN, f"{V}/xestion/enquisas/{surveys[0].pk}/", False),
        ("E3-evolucion-nps", ADMIN, f"{V}/xestion/enquisas/", False),
        # F · Confirmación e lista de espera
        ("F1-como-reservar-e-avisame", UXIA, f"{V}/instalacions/{padel.pk}/", False),
        ("F2-confirmo-cancelo", UXIA, f"{V}/reservas/{soon.pk}/", False),
        ("F3-listas-de-espera", UXIA, f"{V}/reservas/", False),
        (
            "F4-ciclo-lista-espera",
            ADMIN,
            f"{V}/xestion/reservas/{released.released_booking_id}/",
            False,
        ),
        # G · Partidas abertas
        ("G1-partidas-abertas", UXIA, f"{V}/reservas/partidas/", False),
        ("G2-partida", UXIA, f"{V}/reservas/partidas/{game.pk}/", False),
        ("G3-busco-xente", UXIA, f"{V}/reservas/{next_padel.pk}/busco-xente/", False),
        # H · Carné
        ("H1-carne-dixital", UXIA, f"{V}/carne/", True),
        ("H2-lector-carne", ADMIN, f"{V}/xestion/carne/?qr={live_token(card)}", False),
        ("H3-abonos", ADMIN, f"{V}/xestion/abonos/", False),
    ]


def _capture(page, base, path, out, viewport):
    sep = "&" if "?" in path else "?"
    page.goto(f"{base}{path}{sep}marco=0")
    page.wait_for_load_state("networkidle")
    height = page.evaluate(
        "Math.max(document.documentElement.scrollHeight,"
        " (document.querySelector('.shell-main')||{}).scrollHeight||0)"
    )
    page.set_viewport_size({"width": viewport["width"], "height": min(int(height) + 120, 6000)})
    page.screenshot(path=out, full_page=True)
    page.set_viewport_size(viewport)


def test_v12_screenshots(new_page, base):
    OUT.mkdir(parents=True, exist_ok=True)
    items = shots()
    for viewport, label in ((MOBILE, "movil"), (DESKTOP, "escritorio")):
        pages = {}
        for name, persona, path, _dark in items:
            page = pages.get(persona)
            if page is None:
                page = pages[persona] = new_page(viewport=viewport, persona=persona)
            _capture(page, base, path, OUT / f"{name}-{label}.png", viewport)
    # Tema escuro: A e H no móbil, D no escritorio
    dark = {}
    for name, persona, path, is_dark in items:
        if not is_dark:
            continue
        viewport = DESKTOP if name.startswith("D") else MOBILE
        key = (persona, viewport["width"])
        if key not in dark:
            dark[key] = new_page(viewport=viewport, persona=persona, color_scheme="dark")
        label = "escritorio" if viewport is DESKTOP else "movil"
        _capture(dark[key], base, path, OUT / f"{name}-{label}-escuro.png", viewport)
