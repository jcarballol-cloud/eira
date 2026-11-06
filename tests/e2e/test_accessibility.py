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
from apps.integrations.demo import NEW_NEIGHBOUR
from apps.integrations.models import DevMail
from apps.maintenance.models import WorkOrder
from apps.notifications.models import Notice

from .conftest import DESKTOP, MOBILE, TABLET, released_booking_id, uxia_waitlist_entry

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
        WorkOrder.objects.filter(municipality__slug="vilardeiras")
        .exclude(status="done")
        .exclude(kind="cleaning")  # mantemento non ve a limpeza; de madrugada iría a primeira
        .first()
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
    mail = DevMail.objects.order_by("-pk").first()
    notice = Notice.objects.filter(municipality__slug="vilardeiras", cancelled__gt=0).first()
    # v5
    from apps.accounts.models import DataBreach

    pon_padel = Facility.objects.get(name="Pista de pádel 1 da Ribeira")
    from apps.bookings.services import slot_starts

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
    breach = DataBreach.objects.filter(municipality__slug="vilardeiras").first()
    # v1.1 · limpeza
    from apps.maintenance.models import CleaningZone

    zone = CleaningZone.objects.get(facility__municipality__slug="vilardeiras", name="Aseos")
    clean_order = (
        WorkOrder.objects.filter(municipality__slug="vilardeiras", kind="cleaning")
        .exclude(status="done")
        .first()
    )
    hall = zone.facility
    # v1.2
    from apps.safety.models import ClosingEscalation

    esc = ClosingEscalation.objects.filter(municipality__slug="vilardeiras").first()
    from apps.surveys.models import Survey

    surveys = Survey.objects.filter(municipality__slug="vilardeiras").order_by("year")
    released = released_booking_id()
    wait = uxia_waitlist_entry()
    padel_v = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    from apps.bookings.models import OpenGame

    game = OpenGame.objects.filter(municipality__slug="vilardeiras", joins__isnull=False).first()
    uxia_next_padel = (
        Booking.objects.filter(
            user__email="uxia@demo.eira.example", facility=padel_v, status="confirmed"
        )
        .order_by("start")
        .first()
    )
    # v1.5: pantallas novas (claro e, nos perfís con tema escuro, tamén escuro)
    v15_group = Group.objects.get(name="Grupo novo (sen monitora)")
    v15_admin = [
        f"{c}/xestion/procedencia/",
        f"{c}/xestion/procedencia/?periodo=30&deporte=gym",
        f"{c}/xestion/legal/",
        f"{c}/xestion/legal/terms/",
        f"{c}/xestion/actividades/acreditacions/",
        f"{c}/xestion/actividades/grupo/{v15_group.pk}/",
        f"{c}/seguridade/alerta/?instalacion={f.pk}",
        f"{c}/seguridade/accidente/{f.pk}/",
        "/axuda/leeme/",
    ]
    v15_neighbour = [
        f"{c}/legal/",
        f"{c}/legal/terms/",
        f"{c}/legal/rules/",
        "/conta/documentos/",
        f"{c}/app/proximos/",
        "/preferencias/",
        f"{c}/seguridade/alerta/?instalacion={f.pk}",
        f"{c}/seguridade/accidente/{f.pk}/",
    ]
    v15_staff = [f"{c}/seguridade/alerta/?instalacion={f.pk}"]
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
            f"{c}/privacidade/datos/",
            "/axuda/",
            f"{c}/accesibilidade/",
            f"{c}/datos-abertos/",
            "/dev/lock-simulator/",
            "/dev/mailbox/",
            f"/dev/mailbox/{mail.pk}/",
            "/dev/telegram/",
            "/dev/saida/",
            "/dev/ilustracions/",
            "/offline/",
            f"{c}/app/solicitar/",
            f"{c}/app/instalar/?codigo=ABCD-2345",
            # v1.1: QR de limpeza visto por quen non é persoal, e a ficha coa última limpeza
            f"{c}/operario/limpeza/{zone.token}/",
            f"{c}/instalacions/{hall.pk}/",
            # v1.2 · A–C: protocolo sen sesión, páxina da persoa responsable e busca con filtros
            f"{c}/seguridade/accidente/{hall.pk}/",
            f"{c}/seguridade/peche/{esc.token}/",
            f"{c}/?full_access=on&bikes=on&aed=on",
            # v1.3 · B
            f"{c}/privacidade/avaliacion-impacto/",
        ],
        "uxia@demo.eira.example": [
            *v15_neighbour,
            f"{c}/app/",
            f"{c}/app/benvida/?paso=familia",
            f"{c}/reservas/",
            f"{c}/reservas/{upcoming.pk}/",
            f"{c}/reservas/{uxia_booking.pk}/peche/",
            f"{c}/reservas/{uxia_booking.pk}/valorar/",
            f"{c}/incidencias/nova/",
            f"{c}/avisos/",
            f"{c}/avisos/preferencias/",
            "/conta/",
            "/conta/familia/",
            "/conta/privacidade/",
            f"{c}/reservas/{upcoming.pk}/cancelar/",
            f"{c}/actividades/",
            f"{c}/actividades/as-minas/",
            f"{c}/actividades/grupo/{group.pk}/inscribirse/",
            f"{c}/actividades/observatorio/",
            # v5
            f"{c}/app/proximos/",
            "/c/pontedouro/",
            f"/c/pontedouro/instalacions/{pon_padel.pk}/",
            f"/c/pontedouro/instalacions/{pon_padel.pk}/reservar/?inicio="
            + night.isoformat().replace("+", "%2B"),
            f"{c}/reservas/bonos/",
            f"{c}/seguridade/",
            f"{c}/privacidade/datos/",
            f"{c}/incidencias/nova/?risco=1",
            f"{c}/reservas/{upcoming.pk}/estado-inicial/",
            "/axuda/",
            # v1.2 · A e C
            f"{c}/seguridade/alerta/",
            f"{c}/seguridade/alerta/?instalacion={hall.pk}",
            f"{c}/seguridade/accidente/{hall.pk}/",
            f"{c}/seguridade/accidente/{hall.pk}/rexistrar/",
            f"{c}/seguridade/emerxencia/",
            f"{c}/instalacions/{hall.pk}/",
            # v1.2 · E e F
            f"{c}/enquisa/",
            f"{c}/reservas/lista-de-espera/{wait.pk}/",
            f"{c}/reservas/agardar/{padel_v.pk}/?inicio="
            + wait.start.isoformat().replace("+", "%2B"),
            f"{c}/instalacions/{padel_v.pk}/",
            # v1.2 · G e H
            f"{c}/reservas/partidas/",
            f"{c}/reservas/partidas/{game.pk}/",
            f"{c}/reservas/{uxia_next_padel.pk}/busco-xente/",
            f"{c}/carne/",
            # v1.3 · B e C
            "/conta/seguridade/",
            f"{c}/privacidade/avaliacion-impacto/",
        ],
        "admin@vilardeiras.demo.eira.example": [
            *v15_admin,
            # v5
            f"{c}/xestion/cobros/",
            f"{c}/xestion/cobros/bonos/",
            f"{c}/xestion/reservas/{approval.pk}/",
            f"{c}/xestion/reservas/{states.pk}/",
            f"{c}/xestion/privacidade/brechas/",
            f"{c}/xestion/privacidade/brechas/{breach.pk}/",
            f"{c}/xestion/privacidade/brechas/{breach.pk}/comunicacion/",
            f"{c}/xestion/privacidade/brechas/nova/",
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
            f"{c}/xestion/avisos/",
            f"{c}/xestion/avisos/novo/",
            f"{c}/xestion/avisos/{notice.pk}/",
            # v1.1
            f"{c}/xestion/limpeza/",
            f"{c}/xestion/limpeza/zona/{zone.pk}/qr/",
            # v1.2 · A–C
            f"{c}/xestion/seguridade/",
            f"{c}/xestion/seguridade/accidentes/",
            f"{c}/xestion/seguridade/protocolo/",
            f"{c}/xestion/seguridade/protocolo/?instalacion={hall.pk}",
            f"{c}/xestion/instalacions/{hall.pk}/",
            # v1.2 · E e F
            f"{c}/xestion/enquisas/",
            f"{c}/xestion/enquisas/{surveys[0].pk}/",
            f"{c}/xestion/enquisas/{surveys[1].pk}/",
            f"{c}/xestion/reservas/{released}/",
            # v1.2 · D
            f"{c}/xestion/instalacions/{hall.pk}/rendemento/",
            f"{c}/xestion/rendemento/",
            # v1.2 · H
            f"{c}/xestion/abonos/",
            f"{c}/xestion/carne/",
            # v1.3 · C
            f"{c}/xestion/privacidade/auditoria/",
            f"{c}/xestion/privacidade/auditoria/?categoria=accidentes",
            "/conta/seguridade/",
        ],
        "noela@demo.eira.example": [
            *v15_staff,
            f"{c}/operario/",
            f"{c}/operario/?dia=manha",
            f"{c}/operario/calendario/",
            f"{c}/operario/limpeza/{zone.token}/",
            f"{c}/operario/orde/{clean_order.pk}/",
            f"{c}/avisos/",
        ],
        "brais@demo.eira.example": [
            *v15_staff,
            f"{c}/operario/",
            f"{c}/operario/orde/{order.pk}/",
            f"{c}/operario/calendario/",
            f"{c}/operario/?dia=manha",
        ],
        NEW_NEIGHBOUR: [f"{c}/app/", f"{c}/reservas/", f"{c}/avisos/"],
        "antia@demo.eira.example": [
            *v15_staff,
            f"{c}/monitor/",
            f"{c}/monitor/sesion/{session.pk}/asistencia/",
            f"{c}/monitor/sesion/{kiosk_session.pk}/rexistro/",
            f"{c}/monitor/sesion/{session.pk}/esforzo/",
            f"{c}/monitor/grupo/{group.pk}/probas/",
            f"{c}/monitor/estatisticas/",
        ],
        "deputacion@demo.eira.example": [
            "/rexion/marismas/mobilidade/",
            "/rexion/marismas/legal/",
            "/rexion/marismas/legal/terms/",
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
