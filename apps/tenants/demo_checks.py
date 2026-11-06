# SPDX-License-Identifier: EUPL-1.2
"""v1.5.1: exemplos que a demo debe ter sempre, sexa cal sexa a data e a hora do seed.

A guía da demo, as capturas e o pitch contan con eles. `missing()` devolve os que faltan;
úsano as probas e pódese executar tras un seed para comprobar unha demo concreta."""

from django.utils import timezone


def _checks():
    from apps.accounts.models import AppRequest, DataBreach, User
    from apps.activities.models import Group, MinorsAccreditation, Session
    from apps.activities.services import sessions_for_day
    from apps.analytics import provenance
    from apps.bookings.models import Booking, GameJoin, OpenGame, Rating, SlotRelease, WaitlistEntry
    from apps.facilities.models import Facility
    from apps.incidents.models import Incident
    from apps.legal.models import LegalAcceptance
    from apps.legal.services import pending_versions
    from apps.maintenance.cleaning import zone_status
    from apps.maintenance.models import CleaningZone, WorkOrder
    from apps.notifications.models import Notice
    from apps.safety.models import AccidentReport, Alert, ClosingEscalation
    from apps.surveys.models import Survey
    from apps.tenants.models import Municipality, Region

    now = timezone.now()
    vil = Municipality.objects.get(slug="vilardeiras")
    pon = Municipality.objects.get(slug="pontedouro")
    region = Region.objects.get(slug="marismas")
    padel = Facility.objects.get(municipality=vil, kind="padel")
    hall = Facility.objects.get(municipality=vil, kind="sports_hall")
    uxia = User.objects.get(email="uxia@demo.eira.example")
    manuel = User.objects.get(email="manuel@demo.eira.example")
    rosa = User.objects.get(email="rosa@demo.eira.example")
    upcoming = Booking.objects.filter(start__gt=now, status="confirmed")
    flows = provenance.town_flows(vil)
    network = provenance.region_flows(region)
    late_zones = [
        z
        for z in CleaningZone.objects.for_tenant(vil).filter(active=True)
        if zone_status(z)["overdue"]
    ]
    group = Group.objects.get(name="Grupo grande (40)")
    return {
        # Veciñanza
        "uxia_lista_espera": WaitlistEntry.objects.filter(
            user=uxia, status="waiting", start__gt=now
        ).exists(),
        "uxia_padel_proximo": upcoming.filter(user=uxia, facility=padel).exists(),
        "uxia_ximnasio": Booking.objects.filter(
            user=uxia, facility__kind="gym", end__gt=now, status="confirmed"
        ).exists(),
        "uxia_peche_pendente": Booking.objects.filter(
            user=uxia, facility=padel, status="used", end__lte=now, closed_at__isnull=True
        ).exists(),
        "uxia_reserva_noutro_concello": Booking.objects.filter(
            user=uxia, municipality=pon
        ).exists(),
        "uxia_documentos_pendentes": bool(pending_versions(uxia, vil)),
        "manuel_ximnasio": upcoming.filter(user=manuel, facility__kind="gym").exists(),
        "manuel_chave_pavillon": upcoming.filter(
            user=manuel, facility=hall, key_handover__isnull=False
        ).exists(),
        "rosa_reserva": upcoming.filter(user=rosa, municipality=pon).exists(),
        "rosa_noutro_concello": upcoming.filter(user=rosa, municipality=vil).exists(),
        # Xestión de reservas
        "franxa_liberada": SlotRelease.objects.filter(
            municipality=vil, released_booking__isnull=False, taken_booking__isnull=False
        ).exists(),
        "lista_espera_resolta": WaitlistEntry.objects.filter(
            municipality=vil, status="accepted"
        ).exists(),
        "pendente_aprobacion": Booking.objects.filter(
            municipality=vil, status="pending_approval"
        ).exists(),
        "rexeitada_polo_concello": Booking.objects.filter(status="declined").exists(),
        "aprobada_con_cambio": Booking.objects.filter(
            municipality=pon, approved_at__isnull=False, requested_start__isnull=False
        ).exists(),
        "pendente_oficina": Booking.objects.filter(status="pending_office").exists(),
        "suplemento_luz": Booking.objects.filter(lighting_cents__gt=0, start__gt=now).exists(),
        "problema_ao_comezar": Booking.objects.filter(
            facility=padel, start_state_ok=False
        ).exists(),
        "valoracion_con_incidencia": Rating.objects.filter(
            facility=hall, incident__isnull=False
        ).exists(),
        "partida_con_solicitudes": OpenGame.objects.filter(
            municipality=vil, booking__facility=padel, joins__isnull=False
        ).exists(),
        "partida_aceptada": GameJoin.objects.filter(status="accepted").exists(),
        "partida_pontedouro": OpenGame.objects.filter(municipality=pon).exists(),
        # Seguridade
        "peche_escalado": ClosingEscalation.objects.filter(
            municipality=vil, stage=ClosingEscalation.Stage.ESCALATED
        ).exists(),
        "accidente": AccidentReport.objects.filter(municipality=vil).exists(),
        "alerta_mantemento": Alert.objects.filter(municipality=vil, origin="operator").exists(),
        "alerta_limpeza": Alert.objects.filter(municipality=vil, origin="cleaning").exists(),
        "brecha": DataBreach.objects.filter(municipality=vil).exists(),
        # Persoal
        "orde_para_mantemento": WorkOrder.objects.filter(
            municipality=vil, due_date__lte=timezone.localdate()
        )
        .exclude(status="done")
        .exclude(kind="cleaning")
        .exists(),
        "orde_de_limpeza": WorkOrder.objects.filter(municipality=vil, kind="cleaning")
        .exclude(status="done")
        .exists(),
        "zona_atrasada": bool(late_zones),
        "incidencia_aberta": Incident.objects.filter(municipality=vil)
        .exclude(status="resolved")
        .exists(),
        "sesion_hoxe": bool(sessions_for_day([group], timezone.localdate())),
        "sesion_pechada": Session.objects.filter(group=group).exists()
        or Session.objects.filter(municipality=vil, closed_at__isnull=False).exists(),
        # Concello
        "aviso_con_cancelacions": Notice.objects.filter(municipality=vil, cancelled__gt=0).exists(),
        "alta_con_codigo": AppRequest.objects.filter(
            municipality=vil, invitation__isnull=False
        ).exists(),
        "enquisas": Survey.objects.filter(municipality=vil).count() >= 2,
        "reservas_hoxe_ou_mana": Booking.objects.filter(
            municipality=vil,
            start__date__gte=timezone.localdate(),
            start__date__lte=timezone.localdate() + timezone.timedelta(days=1),
        ).exists(),
        # Procedencia: fluxos por riba e por debaixo do limiar
        "fluxo_parroquia": any(r["origin_kind"] == "parish" for r in flows["rows"]),
        "fluxo_outro_concello": any(r["origin_kind"] == "municipality" for r in flows["rows"]),
        "outras_procedencias": bool(flows["others"]),
        "fluxo_rede_ida": any(
            r["origin"] == vil and r["destination"] == pon for r in network["rows"]
        ),
        "fluxo_rede_volta": any(
            r["origin"] == pon and r["destination"] == vil for r in network["rows"]
        ),
        # Documentos e acreditación
        "aceptacions_varias_versions": LegalAcceptance.objects.filter(
            municipality=vil, version__number__gt=1
        ).exists()
        and LegalAcceptance.objects.filter(municipality=vil, version__number=1).exists(),
        "consentimento_retirado": LegalAcceptance.objects.filter(
            user=uxia, withdrawn_at__isnull=False
        ).exists(),
        "monitora_pendente": not MinorsAccreditation.objects.filter(
            user__email="sabela@demo.eira.example"
        ).exists()
        and User.objects.filter(email="sabela@demo.eira.example").exists(),
        "revision_vencida": MinorsAccreditation.objects.filter(
            user__email="xian@demo.eira.example"
        ).exists(),
    }


def missing():
    """Nomes dos exemplos que faltan na demo actual."""
    return sorted(name for name, ok in _checks().items() if not ok)
