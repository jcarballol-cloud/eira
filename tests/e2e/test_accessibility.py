# SPDX-License-Identifier: EUPL-1.2
"""axe-core: cero violacións WCAG 2.1 A/AA nas páxinas principais, en móbil e escritorio."""

import pytest
from axe_playwright_python.sync_playwright import Axe
from django.utils import timezone

from apps.accounts.models import AppRequest
from apps.activities.models import Group, Session
from apps.bookings.models import Booking
from apps.facilities.models import Facility
from apps.incidents.models import Incident
from apps.maintenance.models import WorkOrder

from .conftest import DESKTOP, MOBILE, TABLET

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]

AXE = Axe()
RULES = {"runOnly": {"type": "tag", "values": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]}}


def page_sets():
    f = Facility.objects.filter(municipality__slug="vilardeiras").order_by("pk").first()
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    uxia_booking = (
        Booking.objects.filter(user__email="uxia@demo.eira.example", facility=padel)
        .order_by("-start")
        .first()
    )
    upcoming = (
        Booking.objects.filter(user__email="uxia@demo.eira.example", status="confirmed")
        .order_by("start")
        .first()
    )
    inc = Incident.objects.filter(municipality__slug="vilardeiras").first()
    order = (
        WorkOrder.objects.filter(municipality__slug="vilardeiras").exclude(status="done").first()
    )
    group = Group.objects.filter(municipality__slug="vilardeiras").first()
    session = Session.objects.filter(group=group, closed_at__isnull=False).order_by("-date").first()
    signup = AppRequest.objects.filter(
        municipality__slug="vilardeiras", invitation__isnull=False
    ).first()
    from apps.activities.services import sessions_for_day

    kiosk_session = sessions_for_day(
        [Group.objects.get(name="Grupo grande (40)")], timezone.localdate()
    )[0]
    c = "/c/vilardeiras"
    return {
        None: [
            "/",
            "/?concello=vilardeiras",
            f"{c}/",
            f"{c}/?vista=mapa",
            f"{c}/instalacions/{f.pk}/",
            "/acceso/",
            "/preferencias/",
            "/saude/",
            f"{c}/privacidade/",
            f"{c}/accesibilidade/",
            f"{c}/datos-abertos/",
            "/dev/lock-simulator/",
            "/dev/mailbox/",
            "/offline/",
            f"{c}/app/solicitar/",
            f"{c}/app/instalar/?codigo=ABCD-2345",
        ],
        "uxia@demo.eira.example": [
            f"{c}/app/",
            f"{c}/app/benvida/?paso=familia",
            f"{c}/reservas/",
            f"{c}/reservas/{upcoming.pk}/",
            f"{c}/reservas/{uxia_booking.pk}/peche/",
            f"{c}/reservas/{uxia_booking.pk}/valorar/",
            f"{c}/incidencias/nova/",
            f"{c}/avisos/",
            "/conta/",
            "/conta/familia/",
            "/conta/privacidade/",
            f"{c}/reservas/{upcoming.pk}/cancelar/",
            f"{c}/actividades/",
            f"{c}/actividades/as-minas/",
            f"{c}/actividades/grupo/{group.pk}/inscribirse/",
            f"{c}/actividades/observatorio/",
        ],
        "admin@vilardeiras.demo.eira.example": [
            f"{c}/xestion/",
            f"{c}/xestion/altas/",
            f"{c}/xestion/valoracions/",
            f"{c}/xestion/actividades/grupo/{group.pk}/?sen_fotos=1",
            f"{c}/actividades/observatorio/?semanas=12",
            f"{c}/xestion/altas/{signup.pk}/folla/",
            f"{c}/xestion/axenda/",
            f"{c}/xestion/axenda/?vista=semana",
            f"{c}/xestion/axenda/?vista=mes",
            f"{c}/xestion/reservar/?instalacion={f.pk}",
            f"{c}/xestion/instalacions/",
            f"{c}/xestion/instalacions/nova/",
            f"{c}/xestion/instalacions/nova/?plantilla=gym",
            f"{c}/xestion/instalacions/{f.pk}/",
            f"{c}/xestion/instalacions/{f.pk}/horario/",
            f"{c}/xestion/instalacions/{f.pk}/tarifas/",
            f"{c}/xestion/instalacions/{f.pk}/normas/",
            f"{c}/xestion/peches/",
            f"{c}/xestion/incidencias/",
            f"{c}/xestion/incidencias/{inc.pk}/",
            f"{c}/xestion/mantemento/",
            f"{c}/xestion/indicadores/",
            f"{c}/xestion/configuracion/",
            f"{c}/xestion/persoal/",
            f"{c}/xestion/portabilidade/",
            f"{c}/xestion/mantemento/calendario/",
            f"{c}/xestion/ordes/",
            f"{c}/xestion/actividades/",
        ],
        "brais@demo.eira.example": [
            f"{c}/operario/",
            f"{c}/operario/orde/{order.pk}/",
            f"{c}/operario/calendario/",
        ],
        "antia@demo.eira.example": [
            f"{c}/monitor/",
            f"{c}/monitor/sesion/{session.pk}/asistencia/",
            f"{c}/monitor/sesion/{kiosk_session.pk}/rexistro/",
            f"{c}/monitor/sesion/{session.pk}/esforzo/",
            f"{c}/monitor/grupo/{group.pk}/probas/",
        ],
        "deputacion@demo.eira.example": [
            "/rexion/marismas/",
            "/rexion/marismas/novo-concello/",
            "/c/pontedouro/xestion/instalacions/",
            "/c/pontedouro/xestion/indicadores/",
        ],
    }


def format_violations(results):
    out = []
    for v in results.response["violations"]:
        targets = [n["target"] for n in v["nodes"][:3]]
        out.append(f"{v['id']} ({v['impact']}): {v['help']} → {targets}")
    return "\n".join(out)


@pytest.mark.parametrize(
    "viewport", [MOBILE, TABLET, DESKTOP], ids=["movil", "tableta", "escritorio"]
)
def test_axe_main_pages(new_page, base, viewport):
    failures = []
    checked = 0
    for persona, paths in page_sets().items():
        page = new_page(viewport=viewport, persona=persona)
        for path in paths:
            resp = page.goto(base + path)
            assert resp.status == 200, f"{path} → {resp.status}"
            page.wait_for_load_state("networkidle")
            results = AXE.run(page, options=RULES)
            checked += 1
            if results.violations_count:
                failures.append(f"[{persona or 'anónima'}] {path}\n{format_violations(results)}")
    assert not failures, f"{len(failures)} páxinas con violacións de {checked}:\n\n" + "\n\n".join(
        failures
    )
