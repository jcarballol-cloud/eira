# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · Datos de demostración (todos ficticios) das propostas da terceira rolda.

Execútase ao final de `seed_demo`, despois da v1.1:
- A: persoas responsables, protocolo do concello e un accidente leve rexistrado e pechado;
- B: un peche sen confirmar escalado á persoa responsable (e revisado);
- C: fichas con accesibilidade detallada, aparcabicis, recarga e DESA;
- D, E, F, G e H: ver os métodos correspondentes.
"""

import datetime as dt
import random

from django.utils import timezone

from apps.access.models import LockDevice
from apps.bookings.models import Booking
from apps.facilities.models import Facility
from apps.incidents.models import Incident
from apps.integrations.registry import get_adapter
from apps.safety.models import (
    AccidentReport,
    Alert,
    ClosingEscalation,
    ResponsibleContact,
)
from apps.tenants.models import Municipality

# Accesibilidade detallada por instalación (valor, nota). Sen entrada = sen datos.
DETAIL = {
    "Pavillón municipal de Vilardeiras": {
        "pmr_parking": ("yes", "2 prazas xunto á entrada principal"),
        "route": ("yes", ""),
        "widths": ("yes", ""),
        "toilets": ("yes", ""),
        "changing": ("yes", "Vestiario 3 adaptado"),
        "stands": ("partial", "Espazo para cadeira de rodas, sen acompañante ao carón"),
        "signage": ("partial", "Braille nas portas; falta sinalización podotáctil"),
    },
    "Pista polideportiva de Bustelo": {
        "pmr_parking": ("no", "Aparcamento en terra"),
        "route": ("yes", "Rampla desde a estrada"),
        "widths": ("yes", ""),
        "toilets": ("no", ""),
        "changing": ("no", ""),
        "stands": ("no", ""),
        "signage": ("no", ""),
    },
    "Ximnasio municipal": {
        "pmr_parking": ("yes", ""),
        "route": ("yes", ""),
        "widths": ("partial", "A porta da sala de máquinas mide 75 cm"),
        "toilets": ("yes", ""),
        "changing": ("partial", "Banco abatible, sen ducha adaptada"),
        "stands": ("no", "Sen bancadas"),
        "signage": ("yes", ""),
    },
    "Piscina climatizada de Pontedouro": {
        "pmr_parking": ("yes", "4 prazas"),
        "route": ("yes", ""),
        "widths": ("yes", ""),
        "toilets": ("yes", ""),
        "changing": ("yes", "Grúa hidráulica para o vaso"),
        "stands": ("yes", "2 prazas reservadas na bancada"),
        "signage": ("yes", "Bucle magnético na recepción"),
    },
    "Pavillón do Castro": {
        "pmr_parking": ("partial", "Unha praza, sen sinalizar no chan"),
        "route": ("yes", ""),
        "widths": ("yes", ""),
        "toilets": ("yes", ""),
        "changing": ("no", ""),
        "stands": ("partial", ""),
        "signage": ("no", ""),
    },
}
# Sostibilidade: (aparcabicis, puntos de recarga, tipo, parada)
SUSTAINABILITY = {
    "Pavillón municipal de Vilardeiras": (
        10,
        2,
        "Tipo 2, 7 kW",
        "Bus comarcal, parada Praza do Concello (150 m)",
    ),
    "Pista polideportiva de Bustelo": (4, 0, "", ""),
    "Ximnasio municipal": (6, 0, "", "Bus comarcal, parada Praza do Concello (200 m)"),
    "Piscina climatizada de Pontedouro": (
        20,
        4,
        "Tipo 2, 22 kW",
        "Bus urbano liñas 1 e 3, parada Piscina (50 m)",
    ),
    "Pavillón do Castro": (8, 0, "", "Bus urbano liña 2, parada O Castro (300 m)"),
}
# DESA na propia instalación: (ubicación, horario)
AED_ON_SITE = {
    "Pavillón municipal de Vilardeiras": (
        "Recepción, á dereita da porta principal",
        "Mentres o pavillón está aberto",
    ),
    "Piscina climatizada de Pontedouro": ("Recepción da piscina", "Mentres a piscina está aberta"),
    "Pavillón do Castro": (
        "Corredor dos vestiarios, armario sinalizado",
        "Mentres o pavillón está aberto",
    ),
}


class Seeder:
    def __init__(self):
        self.rng = random.Random("eira-v1.2")
        self.now = timezone.now()
        self.vil = Municipality.objects.get(slug="vilardeiras")
        self.pon = Municipality.objects.get(slug="pontedouro")
        self.hall = Facility.objects.get(municipality=self.vil, kind="sports_hall")

    def run(self):
        self.facility_sheets()  # C
        self.safety_contacts()  # A e B
        self.accident()  # A
        self.closing_escalation()  # B
        self.surveys()  # E
        self.waitlist_resolved()  # F
        self.performance()  # D
        self.open_games()  # G
        self.passes()  # H

    # ------------------------------------------------------------------ C
    def facility_sheets(self):
        adapter = get_adapter("defibrillators")
        for f in Facility.objects.filter(municipality__in=[self.vil, self.pon]):
            detail = DETAIL.get(f.name)
            if detail:
                f.accessibility_detail = {
                    k: {"value": v, "note": note} for k, (v, note) in detail.items()
                }
                f.sync_basic_accessibility()
            bikes, ev, ev_type, stop = SUSTAINABILITY.get(f.name, (None, 0, "", ""))
            f.bike_parking_spaces, f.ev_chargers, f.ev_charger_type, f.transit_stop = (
                bikes,
                ev,
                ev_type,
                stop,
            )
            if f.name in AED_ON_SITE:
                f.aed_on_site = True
                f.aed_inside_location, f.aed_hours = AED_ON_SITE[f.name]
            else:
                f.aed_on_site = False
                near = next(iter(adapter.nearest(f.latitude, f.longitude)), None)
                if near:
                    f.aed_near_name = near["name"]
                    f.aed_near_address = near["address"]
                    f.aed_near_distance_m = near["distance_m"]
                    f.aed_near_hours = near["hours"]
            f.save()

    # ------------------------------------------------------------------ A e B
    def safety_contacts(self):
        Municipality.objects.filter(pk=self.vil.pk).update(police_phone="982 000 092")
        Municipality.objects.filter(pk=self.pon.pk).update(police_phone="986 000 092")
        for m, phone in ((self.vil, "982 000 110"), (self.pon, "986 000 110")):
            ResponsibleContact.objects.create(
                municipality=m,
                order=1,
                name="Conserxaría de deportes (ficticia)",
                role_label="Conserxe",
                phone=phone,
                email=f"conserxaria@{m.slug}.example",
                from_time=dt.time(8, 0),
                until_time=dt.time(22, 0),
            )
            ResponsibleContact.objects.create(
                municipality=m,
                order=2,
                name="Persoa de garda (ficticia)",
                role_label="Garda fóra de horario",
                phone=phone.replace("110", "111"),
                email=f"garda@{m.slug}.example",
                from_time=dt.time(22, 0),
                until_time=dt.time(8, 0),
            )

    def accident(self):
        """Un accidente leve ficticio: alerta desde a app, rexistro e peche (sen relación coa pista)."""
        court = Facility.objects.get(municipality=self.vil, name="Pista polideportiva de Bustelo")
        at = (self.now - dt.timedelta(days=6)).replace(hour=18, minute=20, second=0, microsecond=0)
        incident = Incident.objects.create(
            municipality=self.vil,
            facility=court,
            category=Incident.Category.SAFETY,
            source=Incident.Source.ALERT,
            priority=Incident.Priority.URGENT,
            status=Incident.Status.RESOLVED,
            description="Accidente deportivo. Revisar se a instalación tivo que ver (chan, material, iluminación…).",
            resolution_note="Revisada a pista: chan seco e sen desperfectos. Caída casual.",
            validated_at=at + dt.timedelta(hours=1),
            resolved_at=at + dt.timedelta(days=1),
        )
        Incident.objects.filter(pk=incident.pk).update(created_at=at)
        alert = Alert.objects.create(
            municipality=self.vil,
            kind=Alert.Kind.ACCIDENT,
            origin=Alert.Origin.APP,
            facility=court,
            incident=incident,
            notified=["Conserxaría de deportes (ficticia)", "Administración do concello"],
            created_at=at,
            acknowledged_at=at + dt.timedelta(minutes=4),
        )
        AccidentReport.objects.create(
            municipality=self.vil,
            facility=court,
            occurred_at=at,
            kind=AccidentReport.Kind.FALL,
            severity=AccidentReport.Severity.MILD,
            called_112=False,
            reporter_role=AccidentReport.ReporterRole.USER,
            alert=alert,
            closed_at=at + dt.timedelta(days=1),
            facility_related=False,
        )

    def _used_hall_booking(self, day):
        from apps.accounts.models import User

        user = User.objects.filter(email__startswith="vecinanza").order_by("email").first()
        if user is None:
            return None
        minutes = self.hall.slot_minutes
        for hour in (20, 19, 21, 18, 17, 16, 12, 11, 10):
            start = timezone.make_aware(dt.datetime.combine(day, dt.time(hour, 0)))
            end = start + dt.timedelta(minutes=minutes)
            busy = Booking.objects.filter(facility=self.hall, start__lt=end, end__gt=start).exclude(
                status__in=[Booking.Status.CANCELLED, Booking.Status.EXPIRED]
            )
            if busy.exists():
                continue
            return Booking.objects.create(
                municipality=self.vil,
                facility=self.hall,
                user=user,
                start=start,
                end=end,
                status=Booking.Status.USED,
                tariff_audience="resident",
                price_cents=0,
                base_price_cents=0,
                checked_in_at=start,
                rules_version=self.hall.current_rules(),
                rules_accepted_at=start - dt.timedelta(days=1),
            )
        return None

    def closing_escalation(self):
        """Un peche sen confirmar onte no pavillón (chave custodiada), escalado á conserxaría."""
        yesterday = timezone.localdate() - dt.timedelta(days=1)
        booking = (
            Booking.objects.filter(
                facility=self.hall,
                status=Booking.Status.USED,
                start__date=yesterday,
            )
            .order_by("-start")
            .first()
        )
        if booking is None:
            # v1.3: a demo xera as reservas ao chou e algúns días non hai ningunha usada onte no
            # pavillón; créase unha para que o exemplo exista sempre (o E2E e as capturas úsano).
            booking = self._used_hall_booking(yesterday)
        if booking is None:
            return
        booking.closed_at = None
        booking.close_door_ok = booking.close_key_ok = booking.close_all_ok = None
        booking.close_unconfirmed = True
        booking.checked_in_at = booking.checked_in_at or booking.start
        booking.save()
        m = self.vil
        first = booking.end + dt.timedelta(minutes=m.close_reminder_minutes)
        second = first + dt.timedelta(minutes=m.close_second_minutes)
        third = second + dt.timedelta(minutes=m.close_escalate_minutes)
        contact = ResponsibleContact.objects.filter(municipality=m).order_by("order").first()
        ClosingEscalation.objects.create(
            municipality=m,
            booking=booking,
            stage=ClosingEscalation.Stage.ESCALATED,
            first_at=first,
            second_at=second,
            escalated_at=third,
            contact=contact,
            resolved_at=third + dt.timedelta(minutes=25),
            outcome=ClosingEscalation.Outcome.CHECKED,
            note="A porta estaba pechada e a chave no bar. Faltaba apagar unha luz.",
        )
        # Pontedouro: estado da porta das pechaduras conectadas (simulador)
        LockDevice.objects.filter(municipality=self.pon, kind=LockDevice.Kind.CONNECTED).update(
            door_closed=True, door_state_at=self.now
        )

    # ------------------------------------------------------------------ E
    def surveys(self):
        """Enquisa do ano pasado pechada (NPS calculado) e a deste ano aberta.

        Uxía non respondeu a aberta (ve o aviso na app). Pontedouro activou o NPS tras o uso."""
        from apps.accounts.models import User
        from apps.bookings.models import Booking
        from apps.surveys.models import ASPECTS, Survey, SurveyResponse, UseNps

        today = timezone.localdate()
        people = list(User.objects.filter(email__startswith="vecinanza").order_by("email")) + list(
            User.objects.filter(email__in=["manuel@demo.eira.example", "irene@demo.eira.example"])
        )
        comments = [
            "Os vestiarios do pavillón poderían ter auga máis quente.",
            "Reservar co móbil é moi doado.",
            "Gustaríame que a piscina abrise máis cedo.",
            "Faltan bancos á sombra na pista de Bustelo.",
            "O persoal sempre atende moi ben.",
            "",
            "",
        ]
        last = today.year - 1
        plans = {
            # concello: [(ano, abre, pecha, respostas, proporción de promotoras)]
            self.vil: [
                (last, dt.date(last, 10, 1), dt.date(last, 10, 31), 26, 0.55),
                (
                    today.year,
                    today - dt.timedelta(days=12),
                    today + dt.timedelta(days=18),
                    14,
                    0.62,
                ),
            ],
            self.pon: [(last, dt.date(last, 11, 1), dt.date(last, 11, 30), 22, 0.45)],
        }
        for m, rows in plans.items():
            facilities = list(Facility.objects.filter(municipality=m, is_published=True))
            for year, opens, closes, n, bias in rows:
                survey = Survey.objects.create(
                    municipality=m,
                    year=year,
                    opens_on=opens,
                    closes_on=closes,
                    announced_at=timezone.make_aware(dt.datetime.combine(opens, dt.time(10))),
                )
                pool = list(people)
                self.rng.shuffle(pool)
                for person in pool[:n]:
                    r = self.rng.random()
                    if r < bias:
                        score = self.rng.choice([9, 10, 10])
                    elif r < bias + 0.25:
                        score = self.rng.choice([7, 8])
                    else:
                        score = self.rng.choice([3, 5, 6])
                    aspects = {}
                    for key, _label in ASPECTS:
                        mean = 3.4 if key == "price" else 3.9
                        value = max(1, min(5, round(self.rng.gauss(mean, 0.8))))
                        aspects[key] = None if self.rng.random() < 0.08 else value
                    SurveyResponse.objects.create(
                        survey=survey,
                        user=person,
                        nps=score,
                        facility=self.rng.choice(facilities) if self.rng.random() < 0.7 else None,
                        comment=self.rng.choice(comments),
                        **aspects,
                    )
        # Pontedouro activou a pregunta NPS despois de cada uso (por defecto vai desactivada)
        Municipality.objects.filter(pk=self.pon.pk).update(nps_after_use=True)
        used = Booking.objects.filter(
            municipality=self.pon, status="used", start__gte=self.now - dt.timedelta(days=60)
        ).order_by("-start")[:180]
        for b in used:
            if self.rng.random() < 0.6:
                UseNps.objects.create(
                    municipality=self.pon,
                    booking=b,
                    facility=b.facility,
                    score=self.rng.choice([10, 10, 9, 9, 9, 8, 8, 7, 6, 4]),
                )

    # ------------------------------------------------------------------ F
    def waitlist_resolved(self):
        """Unha lista de espera resolta (pádel da Pereira, hai 3 días) e Uxía agardando unha franxa."""
        from apps.accounts.models import User
        from apps.bookings.models import Booking, SlotRelease, WaitlistEntry

        padel = Facility.objects.get(municipality=self.vil, kind="padel")
        taken = (
            Booking.objects.filter(
                facility=padel,
                status="used",
                start__date=timezone.localdate() - dt.timedelta(days=3),
                user__email__startswith="vecinanza",
            )
            .order_by("start")
            .first()
        )
        if taken is None:
            return
        others = list(
            User.objects.filter(email__startswith="vecinanza")
            .exclude(pk=taken.user_id)
            .order_by("email")[:2]
        )
        cancelled_at = taken.start - dt.timedelta(hours=9)
        original = Booking.objects.create(
            municipality=self.vil,
            facility=padel,
            user=others[0],
            start=taken.start,
            end=taken.end,
            status=Booking.Status.CANCELLED,
            tariff_audience="resident",
            price_cents=taken.price_cents,
            base_price_cents=taken.price_cents,
            paid_cents=taken.price_cents,
            refunded_cents=taken.price_cents,
            cancelled_at=cancelled_at,
            cancel_reason="Non podo ir: cambio de quenda no traballo.",
            rules_version=padel.current_rules(),
            rules_accepted_at=cancelled_at - dt.timedelta(days=2),
        )
        t = cancelled_at
        first = others[1].display_name.split()[0]
        winner = taken.user.display_name.split()[0]
        rel = SlotRelease.objects.create(
            municipality=self.vil,
            facility=padel,
            start=taken.start,
            end=taken.end,
            released_booking=original,
            reason=SlotRelease.Reason.CANCELLED,
            released_at=t,
            taken_booking=taken,
            closed_at=t + dt.timedelta(minutes=41),
            penalty_refunded_cents=taken.price_cents // 2,
            log=[
                {"at": t.isoformat(), "event": "released", "who": "cancelled"},
                {"at": t.isoformat(), "event": "offered", "who": first},
                {
                    "at": (t + dt.timedelta(minutes=30)).isoformat(),
                    "event": "expired",
                    "who": first,
                },
                {
                    "at": (t + dt.timedelta(minutes=30)).isoformat(),
                    "event": "offered",
                    "who": winner,
                },
                {
                    "at": (t + dt.timedelta(minutes=41)).isoformat(),
                    "event": "accepted",
                    "who": winner,
                },
                {
                    "at": (t + dt.timedelta(minutes=41)).isoformat(),
                    "event": "penalty_refunded",
                    "who": "",
                },
            ],
        )
        for user, status, offered in (
            (others[1], "expired", t),
            (taken.user, "accepted", t + dt.timedelta(minutes=30)),
        ):
            WaitlistEntry.objects.create(
                municipality=self.vil,
                facility=padel,
                start=taken.start,
                end=taken.end,
                user=user,
                status=status,
                offered_at=offered,
                offer_expires_at=offered + dt.timedelta(minutes=30),
                release=rel,
                booking=taken if status == "accepted" else None,
            )
        # Uxía agarda unha franxa ocupada de mañá no pádel
        uxia = User.objects.get(email="uxia@demo.eira.example")
        busy = (
            Booking.objects.filter(
                facility=padel,
                start__date=timezone.localdate() + dt.timedelta(days=1),
                status="confirmed",
            )
            .exclude(user=uxia)
            .order_by("start")
            .first()
        )
        if busy:
            WaitlistEntry.objects.create(
                municipality=self.vil, facility=padel, start=busy.start, end=busy.end, user=uxia
            )

    # ------------------------------------------------------------------ D
    # (instalación, [(tipo, descrición, kW, modo, factor)])
    EQUIPMENT = {
        "Pavillón municipal de Vilardeiras": [
            ("lighting", "Proxectores LED da pista (12 × 400 W)", "4.80", "booking", "1.00"),
            ("lighting", "Iluminación de vestiarios e corredores", "0.90", "opening", "0.80"),
            ("hvac", "Bomba de calor (calefacción)", "12.00", "opening", "0.45"),
            ("dhw", "Auga quente das duchas", "9.00", "booking", "0.35"),
            ("other", "Ventilación e sistemas", "0.40", "continuous", "1.00"),
        ],
        "Pista polideportiva de Bustelo": [
            ("lighting", "Proxectores da pista (4 × 1 kW)", "4.00", "light", "1.00"),
        ],
        "Ximnasio municipal": [
            ("hvac", "Climatización", "6.00", "opening", "0.50"),
            ("other", "Máquinas de cardio", "2.40", "booking", "0.60"),
            ("lighting", "Iluminación da sala", "1.20", "opening", "1.00"),
        ],
        "Pista de pádel da Pereira": [
            ("lighting", "Proxectores LED (8 × 200 W)", "1.60", "light", "1.00"),
        ],
        "Piscina climatizada de Pontedouro": [
            ("pumps", "Depuración e recirculación do vaso", "7.50", "continuous", "0.90"),
            ("hvac", "Deshumectadora e climatización", "18.00", "opening", "0.60"),
            ("dhw", "Auga quente e quecemento do vaso", "25.00", "continuous", "0.35"),
            ("lighting", "Iluminación do recinto", "3.00", "opening", "1.00"),
        ],
        "Pavillón do Castro": [
            ("lighting", "Proxectores LED da pista", "5.20", "booking", "1.00"),
            ("hvac", "Calefacción por aerotermos", "15.00", "opening", "0.40"),
        ],
    }

    def performance(self):
        """Inventario de equipos e lecturas reais de facturas para comparar coa estimación."""
        from decimal import Decimal

        from apps.analytics.performance import period_stats
        from apps.facilities.models import EnergyReading, Equipment

        for name, items in self.EQUIPMENT.items():
            f = Facility.objects.filter(name=name).first()
            if f is None:
                continue
            for kind, label, kw, mode, factor in items:
                Equipment.objects.create(
                    facility=f,
                    kind=kind,
                    name=label,
                    power_kw=Decimal(kw),
                    mode=mode,
                    use_factor=Decimal(factor),
                )
        # Facturas dos dous últimos meses pechados: real = estimación ± unha desviación crible
        today = timezone.localdate()
        first_this = today.replace(day=1)
        last_month_end = first_this - dt.timedelta(days=1)
        prev_start = last_month_end.replace(day=1)
        prev_end = prev_start - dt.timedelta(days=1)
        prev_prev_start = prev_end.replace(day=1)
        for name, deviations in (
            ("Pavillón municipal de Vilardeiras", (1.12, 1.07)),
            ("Piscina climatizada de Pontedouro", (0.94, 1.03)),
        ):
            f = Facility.objects.get(name=name)
            for (start, end), dev in zip(
                ((prev_prev_start, prev_end), (prev_start, last_month_end)), deviations, strict=True
            ):
                est = period_stats(f, start, end + dt.timedelta(days=1))["kwh"]
                real = (est * Decimal(str(dev))).quantize(Decimal("0.1"))
                EnergyReading.objects.create(
                    facility=f,
                    period_start=start,
                    period_end=end,
                    kwh=real,
                    cost_cents=int(real * f.municipality.energy_price_eur_kwh * 100),
                )

    # ------------------------------------------------------------------ G
    def open_games(self):
        """Partidas abertas de veciñanza ficticia en Vilardeiras e Pontedouro, unha con
        solicitudes, unha persoa aceptada e mensaxes predefinidas."""
        from apps.accounts.models import User
        from apps.bookings.models import Booking, GameJoin, GameMessage, OpenGame

        people = list(
            User.objects.filter(
                email__startswith="vecinanza", birth_year__lte=timezone.localdate().year - 18
            ).order_by("email")
        )
        plans = [
            (self.vil, "padel", "medium", 2, "Buscamos parella para dobres."),
            (self.vil, "outdoor_court", "beginner", 4, "Fútbol sala tranquilo, ven quen queira."),
            (self.vil, "sports_hall", "advanced", 3, ""),
            (self.pon, "padel", "medium", 1, "Falta unha persoa."),
        ]
        used = set()
        for i, (m, kind, level, spots, message) in enumerate(plans):
            b = (
                Booking.objects.filter(
                    municipality=m,
                    facility__kind=kind,
                    status="confirmed",
                    start__gt=self.now + dt.timedelta(hours=20),
                    start__lt=self.now + dt.timedelta(days=6),
                    user__email__startswith="vecinanza",
                    user__birth_year__lte=timezone.localdate().year - 18,
                )
                .exclude(pk__in=used)
                .order_by("start")
                .first()
            )
            if b is None:
                continue
            used.add(b.pk)
            b.participants = max(1, min(b.participants, b.facility.max_participants - spots))
            b.save(update_fields=["participants"])
            game = OpenGame.objects.create(
                municipality=m,
                booking=b,
                spots=spots,
                base_participants=b.participants,
                level=level,
                message=message,
                consent_at=self.now - dt.timedelta(days=1),
            )
            if i == 0:
                others = [p for p in people if p.pk != b.user_id][:3]
                accepted, pending = others[0], others[1]
                GameJoin.objects.create(
                    game=game,
                    user=accepted,
                    status="accepted",
                    consent_at=self.now - dt.timedelta(hours=20),
                    decided_at=self.now - dt.timedelta(hours=19),
                )
                GameJoin.objects.create(
                    game=game, user=pending, consent_at=self.now - dt.timedelta(hours=2)
                )
                b.participants += 1
                b.save(update_fields=["participants"])
                GameMessage.objects.create(game=game, user=accepted, code="rackets")
                GameMessage.objects.create(game=game, user=b.user, code="see_you")

    # ------------------------------------------------------------------ H
    PASS_TYPES = [
        # (nome, tipo, prezo €, desconto %, descrición)
        ("Abono xeral", "general", 45, 20, "Para calquera persoa. Un ano."),
        ("Abono mocidade", "youth", 25, 30, "Ata 25 anos."),
        ("Abono maiores", "senior", 20, 40, "Desde 65 anos."),
        ("Abono familiar", "family", 70, 25, "Unidade familiar con crianzas."),
    ]

    def passes(self):
        """Tipos de abono nos dous concellos; Uxía (TPV) e Manuel (oficina) con abono e carné,
        e algunhas persoas máis. Un carné vinculado ao carné ficticio da biblioteca."""
        from apps.accounts.models import Membership, Role, User
        from apps.members import services as members
        from apps.members.models import MemberCard, PassType, SportsPass

        types = {}
        for m in (self.vil, self.pon):
            for name, kind, euros, pct, desc in self.PASS_TYPES:
                types[(m.slug, kind)] = PassType.objects.create(
                    municipality=m,
                    name=name,
                    kind=kind,
                    price_cents=euros * 100,
                    discount_pct=pct,
                    description=desc,
                )
        admin = Membership.objects.filter(municipality=self.vil, role=Role.ADMIN).first()
        plan = [
            ("uxia@demo.eira.example", "general", None, 40),
            ("manuel@demo.eira.example", "senior", "cash", 200),
        ] + [
            (
                u.email,
                "general" if i % 3 else "youth",
                "card_terminal" if i % 2 else None,
                30 + 20 * i,
            )
            for i, u in enumerate(
                User.objects.filter(email__startswith="vecinanza").order_by("email")[:8]
            )
        ]
        for email, kind, method, days_ago in plan:
            user = User.objects.get(email=email)
            p = members.buy_pass(
                types[("vilardeiras", kind)],
                user,
                method=method or "card_terminal",
                by=admin.user if admin else None,
            )
            if not method:  # comprado co TPV desde a app
                p.channel = "online"
                p.sold_by = None
            start = timezone.localdate() - dt.timedelta(days=days_ago)
            p.starts_on, p.expires_on = start, start + dt.timedelta(days=p.type.valid_days - 1)
            p.save()
        # Un abono xa caducado no historial de Manuel
        manuel = User.objects.get(email="manuel@demo.eira.example")
        old_start = timezone.localdate() - dt.timedelta(days=200 + 365)
        SportsPass.objects.create(
            municipality=self.vil,
            user=manuel,
            type=types[("vilardeiras", "senior")],
            status=SportsPass.Status.EXPIRED,
            starts_on=old_start,
            expires_on=old_start + dt.timedelta(days=364),
            price_cents=2000,
            channel="office",
        )
        card = MemberCard.objects.get(municipality=self.vil, user=manuel)
        card.external_id = "BIB-00012"  # carné ficticio da biblioteca (adaptador simulado)
        card.save(update_fields=["external_id"])


def seed():
    Seeder().run()
