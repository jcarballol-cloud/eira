# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · G: recorrido por cada perfil con navegador. Comproba que ningunha función de versións
anteriores se perdeu: a páxina responde, mostra o texto esperado e non hai erros de consola.
A lista completa está en docs/REVISION_V1.5.md. Non substitúe a revisión dunha persoa."""

import pytest
from django.utils import timezone

from apps.activities.models import Group
from apps.activities.services import sessions_for_day
from apps.bookings.models import Booking
from apps.facilities.models import Facility
from apps.maintenance.models import CleaningZone, WorkOrder

from .conftest import DESKTOP, MOBILE, TABLET

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]

C = "/c/vilardeiras"


def inventory():
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    hall = Facility.objects.get(name="Pavillón municipal de Vilardeiras")
    booking = (
        Booking.objects.filter(user__email="uxia@demo.eira.example", status="confirmed")
        .order_by("start")
        .first()
    )
    order = (
        WorkOrder.objects.filter(municipality__slug="vilardeiras")
        .exclude(status="done")
        .exclude(kind="cleaning")  # mantemento non ve a limpeza; de madrugada iría a primeira
        .first()
    )
    zone = CleaningZone.objects.filter(municipality__slug="vilardeiras").first()
    session = sessions_for_day([Group.objects.get(name="Grupo grande (40)")], timezone.localdate())[
        0
    ]
    return [
        (
            None,
            DESKTOP,
            [
                ("Portada da demo", "/", "Eira"),
                ("Consulta sen rexistro", f"{C}/", "Instalacións"),
                ("Mapa de instalacións", f"{C}/?vista=mapa", "Vilardeiras"),
                ("Ficha e grella semanal", f"{C}/instalacions/{padel.pk}/", "Dispoñibilidade"),
                ("Privacidade", f"{C}/privacidade/", "Privacidade"),
                ("Quen custodia os datos", f"{C}/privacidade/datos/", "custodia"),
                ("Resumo da EIPD", f"{C}/privacidade/avaliacion-impacto/", "Procedencia"),
                ("Datos abertos", f"{C}/datos-abertos/", "Datos abertos"),
                ("Guía", "/axuda/", "Guía de Eira"),
                ("Simulador de pechadura", "/dev/lock-simulator/", "Pechadura"),
                ("Correo simulado", "/dev/mailbox/", "Correo"),
                ("Documentos legais públicos", f"{C}/legal/", "MODELO DE EXEMPLO"),
            ],
        ),
        (
            "uxia@demo.eira.example",
            MOBILE,
            [
                ("Inicio e próxima reserva", f"{C}/app/", "próxima reserva"),
                ("Reservas e historial", f"{C}/reservas/", "reservas"),
                ("Código de acceso", f"{C}/reservas/{booking.pk}/", "Acceso"),
                ("Aviso e alerta", f"{C}/seguridade/", "Alerta"),
                ("Protocolo de accidente", f"{C}/seguridade/accidente/{hall.pk}/", "DESA"),
                ("Incidencia con foto", f"{C}/incidencias/nova/", "instalación"),
                ("Avisos", f"{C}/avisos/", "Avisos"),
                ("Unidade familiar", "/conta/familia/", "familiar"),
                ("Saúde persoal", "/saude/", "A miña saúde"),
                ("Bonos", f"{C}/reservas/bonos/", "Bonos"),
                ("Carné municipal", f"{C}/carne/", "carné"),
                ("Partidas abertas", f"{C}/reservas/partidas/", "Partidas"),
                ("Concellos próximos", f"{C}/app/proximos/", "Onde estou"),
                ("Actividades e escolas", f"{C}/actividades/", "Actividades"),
                ("Centro de privacidade", "/conta/privacidade/", "rivacidade"),
                ("Dobre factor", "/conta/seguridade/", "factor"),
                ("Documentos aceptados", "/conta/documentos/", "Documentos aceptados"),
            ],
        ),
        (
            "brais@demo.eira.example",
            MOBILE,
            [
                ("Ordes de traballo", f"{C}/operario/", "Ordes de traballo"),
                ("Orde", f"{C}/operario/orde/{order.pk}/", order.title),
                ("Calendario de mantemento", f"{C}/operario/calendario/", "Calendario"),
                ("Alerta", f"{C}/seguridade/alerta/", "Accidente deportivo"),
            ],
        ),
        (
            "noela@demo.eira.example",
            MOBILE,
            [
                ("Tarefas de limpeza", f"{C}/operario/", "Tarefas de limpeza"),
                ("Zona con QR", f"{C}/operario/limpeza/{zone.token}/", zone.name),
                ("Alerta", f"{C}/seguridade/alerta/", "Accidente deportivo"),
            ],
        ),
        (
            "antia@demo.eira.example",
            TABLET,
            [
                ("Tableta: sesións", f"{C}/monitor/", "Modo tableta"),
                ("Rexistro con esforzo", f"{C}/monitor/sesion/{session.pk}/rexistro/", "Alerta"),
                ("Lista de asistencia", f"{C}/monitor/sesion/{session.pk}/asistencia/", "Alerta"),
                ("Estatísticas", f"{C}/monitor/estatisticas/", "Estat"),
                ("Alerta", f"{C}/seguridade/alerta/", "Accidente deportivo"),
            ],
        ),
        (
            "admin@vilardeiras.demo.eira.example",
            DESKTOP,
            [
                ("Panel do día", f"{C}/xestion/", "Panel"),
                ("Axenda", f"{C}/xestion/axenda/", "Axenda"),
                ("Reservar por alguén", f"{C}/xestion/reservar/", "Reservar"),
                ("Cobros", f"{C}/xestion/cobros/", "Cobros"),
                ("Valoracións", f"{C}/xestion/valoracions/", "Valoracións"),
                ("Enquisas e NPS", f"{C}/xestion/enquisas/", "NPS"),
                ("Rendemento", f"{C}/xestion/rendemento/", "Rendemento"),
                ("Observatorio", f"{C}/actividades/observatorio/", "Observatorio"),
                ("Indicadores", f"{C}/xestion/indicadores/", "Indicadores"),
                ("Abonos e carné", f"{C}/xestion/abonos/", "Abonos"),
                ("Limpeza", f"{C}/xestion/limpeza/", "Limpeza"),
                ("Mantemento", f"{C}/xestion/mantemento/", "Mantemento"),
                ("Ordes", f"{C}/xestion/ordes/", "Ordes"),
                ("Alertas e peches", f"{C}/xestion/seguridade/", "Alertas"),
                ("Accidentes", f"{C}/xestion/seguridade/accidentes/", "ccidentes"),
                ("Brechas", f"{C}/xestion/privacidade/brechas/", "rechas"),
                ("Auditoría", f"{C}/xestion/privacidade/auditoria/", "uditoría"),
                ("Altas e padrón", f"{C}/xestion/altas/padron/", "Padrón"),
                ("Persoal", f"{C}/xestion/persoal/", "Persoal"),
                ("Portabilidade", f"{C}/xestion/portabilidade/", "export"),
                ("Configuración", f"{C}/xestion/configuracion/", "Configuración"),
                ("Normas por instalación", f"{C}/xestion/instalacions/{hall.pk}/normas/", "Normas"),
                ("Procedencia", f"{C}/xestion/procedencia/", "outras procedencias"),
                ("Documentos legais", f"{C}/xestion/legal/", "MODELO DE EXEMPLO"),
                ("Acreditacións", f"{C}/xestion/actividades/acreditacions/", "Sabela"),
                ("LEEME", "/axuda/leeme/", "Requisitos legais"),
            ],
        ),
        (
            "deputacion@demo.eira.example",
            DESKTOP,
            [
                ("Comparativa da rede", "/rexion/marismas/", "Comparativa"),
                ("Novo concello", "/rexion/marismas/novo-concello/", "concello"),
                ("Mobilidade", "/rexion/marismas/mobilidade/", "Puntos quentes"),
                ("Modelos legais", "/rexion/marismas/legal/", "MODELO DE EXEMPLO"),
                ("Indicadores en consulta", f"{C}/xestion/indicadores/", "Indicadores"),
            ],
        ),
    ]


def test_walk_every_profile(new_page, base):
    failures, checked = [], 0
    for persona, viewport, items in inventory():
        page = new_page(viewport=viewport, persona=persona)
        errors = []
        page.on(
            "console",
            lambda m, errs=errors: (
                errs.append(m.text)
                if m.type == "error" and "tile" not in m.text and "ERR_" not in m.text
                else None
            ),
        )
        page.on("pageerror", lambda e, errs=errors: errs.append(str(e)))
        for name, path, expected in items:
            checked += 1
            response = page.goto(base + path)
            page.wait_for_load_state("load")
            if response.status != 200:
                failures.append(f"[{persona}] {name} {path}: HTTP {response.status}")
            elif expected.lower() not in page.locator("body").inner_text().lower():
                failures.append(f"[{persona}] {name} {path}: falta «{expected}»")
            if errors:
                failures.append(f"[{persona}] {name} {path}: consola: {errors[:2]}")
                errors.clear()
    print(f"\nRecorrido: {checked} pantallas")
    assert not failures, "\n".join(failures)
