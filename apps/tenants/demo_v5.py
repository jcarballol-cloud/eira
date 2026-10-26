# SPDX-License-Identifier: EUPL-1.2
"""v5 · Datos de demostración da versión definitiva (todos ficticios).

Execútase ao final de `seed_demo`, cun xerador aleatorio propio para non mover o resto da demo:
- Vilardeiras e Pontedouro abertos á rede e reservas cruzadas;
- dúas instalacións «con aprobación» (pendentes, aprobadas, rexeitada con devolución e un cambio);
- formas de pagamento, bonos, pagamentos na oficina e suplementos de luz;
- un estado ao entrar con problema (incidencia atribuída a antes da reserva);
- ficha de seguridade de todas as instalacións e revisións de seguridade feitas;
- unha brecha de exemplo ficticia e pechada, e a persoa DPD de Vilardeiras.
"""

import datetime as dt
import random

from django.db.models import F
from django.utils import timezone

from apps.accounts.models import DataBreach, Membership, Role, User
from apps.bookings.models import Booking, Payment, Voucher, VoucherType
from apps.bookings.payments import new_reference, sell_voucher
from apps.bookings.services import slot_starts
from apps.facilities.models import Facility
from apps.incidents.models import Incident
from apps.maintenance.models import WorkOrder
from apps.maintenance.safety import create_safety_review
from apps.tenants.models import Municipality

DPO_EMAIL = "dpd@vilardeiras.demo.eira.example"

EQUIPMENT = {
    "outdoor_court": "2 balóns de baloncesto\n2 balóns de fútbol sala\n1 rede de recambio",
    "sports_hall": "6 balóns de voleibol\n4 balóns de baloncesto\n2 redes de recambio\n20 petos",
    "padel": "2 palas de préstamo\n1 bote de pelotas",
    "gym": "Esterillas, bandas e mancuernas (ver inventario na entrada)",
    "grass_field": "10 balóns de fútbol\n20 conos\n2 porterías pequenas",
    "pool": "Táboas, pullbuoys e churros\nGrúa hidráulica de acceso ao vaso",
}
AED = {
    "vilardeiras": "Pavillón municipal (recepción), a 300 m",
    "pontedouro": "Recepción da piscina climatizada",
}
PROTOCOL = (
    "1. Protexe a persoa ferida e non a movas se non hai perigo.\n"
    "2. Chama ao 112: di a instalación e o enderezo.\n"
    "3. Se non respira, empeza a reanimación e manda buscar o DEA.\n"
    "4. Avisa ao concello."
)


class Seeder:
    def __init__(self):
        self.rng = random.Random("eira-v5")
        self.now = timezone.now()
        self.vil = Municipality.objects.get(slug="vilardeiras")
        self.pon = Municipality.objects.get(slug="pontedouro")

    def run(self):
        self.towns()
        self.facilities()
        self.history_methods()
        self.cross_bookings()
        self.approval()
        self.vouchers()
        self.office_and_light()
        self.start_state_problem()
        self.safety_reviews()
        self.breach()

    # ------------------------------------------------------------------
    def towns(self):
        Municipality.objects.filter(pk=self.vil.pk).update(
            network_open=True,
            network_max_active=2,
            payment_methods=["tpv", "office", "free", "voucher"],
            office_payment_hours=48,
            lighting_rule="sunset",
        )
        Municipality.objects.filter(pk=self.pon.pk).update(
            network_open=True,
            network_max_active=3,
            network_advance_days=7,
            payment_methods=["tpv", "office", "voucher", "deferred"],
            office_payment_hours=24,
            lighting_rule="fixed",
            lighting_from=dt.time(19, 30),
            lighting_until=dt.time(8, 30),
        )
        self.vil.refresh_from_db()
        self.pon.refresh_from_db()
        # DPD de Vilardeiras (ve o rexistro de brechas)
        dpo = User.objects.create_user(DPO_EMAIL, display_name="DPD de Vilardeiras")
        Membership.objects.create(user=dpo, municipality=self.vil, role=Role.DPO)

    def facilities(self):
        for f in Facility.objects.filter(municipality__in=[self.vil, self.pon]):
            f.equipment = EQUIPMENT.get(f.kind, "")
            f.accident_protocol = PROTOCOL
            f.aed_location = AED[f.municipality.slug]
            f.max_participants = {"padel": 4, "gym": 1, "pool": 1, "grass_field": 22}.get(
                f.kind, 12
            )
            light = {
                "padel": 150,
                "outdoor_court": 100,
                "grass_field": 600,
                "sports_hall": 200,
            }.get(f.kind, 0)
            if f.lighting and light:
                f.lighting_supplement_cents = light
            # Dúas instalacións con aprobación do concello
            if f.name in ("Campo de fútbol de Outeiro", "Pavillón do Castro"):
                f.booking_mode = "approval"
            # Formas de pagamento por instalación: TPV, oficina e bono; o aprazado só no campo de
            # Lamas (clubs) e a pista de Fontela é gratuíta (instalación sen taxa)
            f.payment_methods = ["tpv", "office", "voucher"]
            if f.name == "Campo de herba artificial de Lamas":
                f.payment_methods = ["tpv", "office", "deferred"]
            if f.name == "Pista exterior de Fontela":
                f.payment_methods = ["free"]
            f.save()

    def history_methods(self):
        """Forma de pagamento coherente no histórico e participantes realistas."""
        qs = Booking.objects.filter(municipality__in=[self.vil, self.pon])
        qs.filter(price_cents=0).update(payment_method="free")
        qs.filter(channel__in=["phone", "counter"], price_cents__gt=0).update(
            payment_method="office"
        )
        qs.update(participants=(F("id") % 4) + 1)
        Booking.objects.filter(facility__kind__in=["gym", "pool"]).update(participants=1)

    def _slot(self, facility, day_offset, hour):
        for extra in range(0, 7):
            day = timezone.localdate() + dt.timedelta(days=day_offset + extra)
            for s in slot_starts(facility, day):
                if timezone.localtime(s).hour >= hour:
                    free = (
                        not Booking.objects.filter(
                            facility=facility,
                            start__lt=s + dt.timedelta(minutes=facility.slot_minutes),
                            end__gt=s,
                        )
                        .holding()
                        .exists()
                    )
                    if free:
                        return s
        return None

    def _make(
        self, facility, user, start, *, status, method="tpv", paid=True, origin=None, **extra
    ):
        if start is None:
            return None
        end = start + dt.timedelta(minutes=facility.slot_minutes)
        tariffs = {t.audience: t.price_cents for t in facility.tariffs.all()}
        audience = extra.pop("audience", "non_resident" if origin else "resident")
        price = extra.pop("price", tariffs.get(audience, 0))
        light = extra.pop("lighting_cents", 0)
        total = 0 if method in ("free", "voucher") else price + light
        ref = new_reference() if total and paid else ""
        b = Booking.objects.create(
            municipality=facility.municipality,
            facility=facility,
            user=user,
            start=start,
            end=end,
            status=status,
            tariff_audience=audience,
            price_cents=total,
            base_price_cents=price,
            lighting_cents=light if total else 0,
            needs_light=bool(light),
            paid_cents=total if paid else 0,
            payment_reference=ref,
            payment_method=method,
            network_origin=origin,
            rules_version=facility.current_rules(),
            rules_accepted_at=start - dt.timedelta(days=2),
            participants=extra.pop("participants", 2),
            **extra,
        )
        Booking.objects.filter(pk=b.pk).update(
            created_at=min(self.now, start - dt.timedelta(days=2))
        )
        if total and paid:
            Payment.objects.create(
                municipality=facility.municipality,
                booking=b,
                concept=f"{facility.name} · {b.reference}",
                amount_cents=total,
                status=Payment.Status.PAID,
                method={"tpv": "online", "office": "cash", "deferred": "card_terminal"}.get(
                    method, "online"
                ),
                reference=ref,
                signature_ok=method == "tpv",
                provider_code="0000",
                resolved_at=min(self.now, start - dt.timedelta(days=2)),
            )
        return b

    def cross_bookings(self):
        """Reservas cruzadas: veciñanza de Vilardeiras en Pontedouro e ao revés."""
        uxia = User.objects.get(email="uxia@demo.eira.example")
        rosa = User.objects.get(email="rosa@demo.eira.example")
        pon_padel = Facility.objects.get(municipality=self.pon, name="Pista de pádel 1 da Ribeira")
        pon_pool = Facility.objects.get(municipality=self.pon, kind="pool")
        vil_hall = Facility.objects.get(municipality=self.vil, kind="sports_hall")
        # Uxía xa xogou en Pontedouro hai 10 días (con luz) e valorouno
        past = self._slot(pon_padel, -10, 20)
        b = self._make(
            pon_padel,
            uxia,
            past,
            status="used",
            origin=self.vil,
            lighting_cents=150,
            checked_in_at=past,
        )
        if b:
            from apps.bookings.models import Rating

            Rating.objects.create(
                municipality=self.pon, booking=b, facility=pon_padel, score="good"
            )
        # Rosa (Pontedouro) reservou o pavillón de Vilardeiras para a semana que vén
        self._make(vil_hall, rosa, self._slot(vil_hall, 6, 18), status="confirmed", origin=self.pon)
        # Veciñanza de Vilardeiras na piscina de Pontedouro (histórico, para as estatísticas)
        vil_people = list(
            User.objects.filter(residencies__municipality=self.vil, email__startswith="vecinanza")
            .exclude(residencies__municipality=self.pon)
            .distinct()[:8]
        )
        for i, person in enumerate(vil_people):
            start = self._slot(pon_pool, -20 + i * 2, 18 + i % 3)
            self._make(
                pon_pool,
                person,
                start,
                status="used",
                origin=self.vil,
                participants=1,
                checked_in_at=start,
            )

    def approval(self):
        """Pendentes, aprobada, rexeitada con devolución e un cambio pendente."""
        outeiro = Facility.objects.get(municipality=self.vil, name="Campo de fútbol de Outeiro")
        castro = Facility.objects.get(municipality=self.pon, name="Pavillón do Castro")
        admin_v = User.objects.get(email="admin@vilardeiras.demo.eira.example")
        admin_p = User.objects.get(email="admin@pontedouro.demo.eira.example")
        neighbours = list(User.objects.filter(email__startswith="vecinanza").order_by("email"))
        # Vilardeiras: dúas pendentes de aprobación (unha xa pagada) e unha rexeitada con devolución
        self._make(
            outeiro,
            neighbours[2],
            self._slot(outeiro, 3, 18),
            status="pending_approval",
            participants=14,
        )
        self._make(
            outeiro,
            neighbours[3],
            self._slot(outeiro, 5, 19),
            status="pending_approval",
            paid=False,
            method="office",
            participants=18,
        )
        declined = self._make(
            outeiro,
            neighbours[4],
            self._slot(outeiro, 4, 20),
            status="declined",
            participants=10,
            decided_by=admin_v,
            decision_reason="O campo está reservado para o partido da escola de fútbol.",
        )
        if declined:
            declined.refunded_cents = declined.paid_cents
            declined.cancelled_at = self.now - dt.timedelta(hours=5)
            declined.cancel_reason = declined.decision_reason[:200]
            declined.save(update_fields=["refunded_cents", "cancelled_at", "cancel_reason"])
            Payment.objects.filter(booking=declined).update(
                status=Payment.Status.REFUNDED, refunded_cents=F("amount_cents")
            )
        # Pontedouro: unha aprobada e un cambio pendente
        ok = self._make(
            castro,
            neighbours[12],
            self._slot(castro, 4, 19),
            status="confirmed",
            approved_at=self.now - dt.timedelta(days=1),
            decided_by=admin_p,
            participants=10,
        )
        if ok:
            ok.requested_start = self._slot(castro, 5, 20)
            ok.save(update_fields=["requested_start"])
        self._make(
            castro,
            neighbours[14],
            self._slot(castro, 2, 18),
            status="pending_approval",
            participants=8,
        )

    def vouchers(self):
        vil_gym = Facility.objects.get(municipality=self.vil, kind="gym")
        pon_padel = Facility.objects.get(municipality=self.pon, name="Pista de pádel 1 da Ribeira")
        gym_type = VoucherType.objects.create(
            municipality=self.vil,
            name="Bono 10 usos ximnasio",
            facility=vil_gym,
            uses=10,
            price_cents=1800,
        )
        VoucherType.objects.create(
            municipality=self.vil, name="Bono 5 usos (calquera)", uses=5, price_cents=1500
        )
        padel_type = VoucherType.objects.create(
            municipality=self.pon,
            name="Bono 5 partidos de pádel",
            facility=pon_padel,
            uses=5,
            price_cents=1600,
        )
        admin_v = User.objects.get(email="admin@vilardeiras.demo.eira.example")
        manuel = User.objects.get(email="manuel@demo.eira.example")
        v = sell_voucher(gym_type, manuel, method="cash", by=admin_v)
        Voucher.objects.filter(pk=v.pk).update(created_at=self.now - dt.timedelta(days=20))
        Payment.objects.filter(voucher=v).update(created_at=self.now - dt.timedelta(days=20))
        # Manuel xa gastou 3 usos
        for days in (-12, -8, -4):
            self._make(
                vil_gym,
                manuel,
                self._slot(vil_gym, days, 10),
                status="used",
                method="voucher",
                voucher=v,
                audience="senior",
                participants=1,
            )
        Voucher.objects.filter(pk=v.pk).update(uses_left=7)
        # Algúns bonos de pádel vendidos en Pontedouro (TPV)
        for person in User.objects.filter(residencies__municipality=self.pon).order_by("email")[:3]:
            pv = Voucher.objects.create(
                municipality=self.pon,
                type=padel_type,
                user=person,
                uses_total=5,
                uses_left=self.rng.randint(1, 5),
                price_cents=1600,
                status=Voucher.Status.ACTIVE,
                expires_at=self.now + dt.timedelta(days=300),
            )
            Payment.objects.create(
                municipality=self.pon,
                voucher=pv,
                concept=f"{padel_type.name} · 5 usos",
                amount_cents=1600,
                status=Payment.Status.PAID,
                reference=new_reference(),
                signature_ok=True,
                provider_code="0000",
                resolved_at=self.now - dt.timedelta(days=self.rng.randint(2, 30)),
            )

    def office_and_light(self):
        """Pagamentos pendentes na oficina e reservas futuras con suplemento de luz."""
        neighbours = list(User.objects.filter(email__startswith="vecinanza").order_by("email"))
        hall = Facility.objects.get(municipality=self.vil, kind="sports_hall")
        padel = Facility.objects.get(municipality=self.vil, kind="padel")
        for i, (f, hour) in enumerate(((hall, 17), (padel, 12))):
            b = self._make(
                f,
                neighbours[6 + i],
                self._slot(f, 1 + i, hour),
                status="pending_office",
                method="office",
                paid=False,
            )
            if b:
                b.hold_expires_at = min(b.start, self.now + dt.timedelta(hours=30 - i * 10))
                b.save(update_fields=["hold_expires_at"])
        # Oficina xa cobrada (efectivo)
        self._make(
            hall,
            neighbours[8],
            self._slot(hall, -3, 18),
            status="used",
            method="office",
            checked_in_at=None,
        )
        # Luz: reservas de noite nas pistas con suplemento
        for f in Facility.objects.filter(
            municipality__in=[self.vil, self.pon], lighting_supplement_cents__gt=0
        ):
            if f.booking_mode == "approval":
                continue
            local = list(
                User.objects.filter(
                    residencies__municipality=f.municipality, email__startswith="vecinanza"
                ).order_by("email")
            )
            for k, person in enumerate(self.rng.sample(local, 2)):
                start = self._slot(f, 1 + k * 2, 21)
                self._make(
                    f, person, start, status="confirmed", lighting_cents=f.lighting_supplement_cents
                )

    def start_state_problem(self):
        """Hoxe: alguén atopou a rede rota ao entrar no pádel; queda atribuída a antes."""
        padel = Facility.objects.get(municipality=self.vil, kind="padel")
        person = User.objects.get(email="vecinanza05@demo.eira.example")
        start = None
        for i in range(0, 4):
            past = [
                s
                for s in slot_starts(padel, timezone.localdate() - dt.timedelta(days=i))
                if s + dt.timedelta(minutes=padel.slot_minutes) <= self.now
            ]
            if past:
                start = past[-1]
                break
        if start is None:
            return
        Booking.objects.filter(
            facility=padel,
            start__lt=start + dt.timedelta(minutes=padel.slot_minutes),
            end__gt=start,
        ).exclude(user__email="uxia@demo.eira.example").update(
            status="cancelled", cancel_reason="Reorganización da demo"
        )
        if Booking.objects.filter(
            facility=padel, start=start, status__in=["used", "confirmed"]
        ).exists():
            start = start - dt.timedelta(days=1)
        b = self._make(
            padel,
            person,
            start,
            status="used",
            checked_in_at=start + dt.timedelta(minutes=2),
            start_state_at=start + dt.timedelta(minutes=3),
            start_state_ok=False,
            start_state_notes="A rede está descosida no lateral esquerdo e falta unha pala de préstamo.",
            closed_at=start + dt.timedelta(minutes=92),
            close_door_ok=True,
            close_all_ok=True,
        )
        previous = (
            Booking.objects.filter(facility=padel, end__lte=start, status="used")
            .exclude(pk=b.pk)
            .order_by("-end")
            .first()
        )
        text = (
            f"Ao comezar a reserva {b.reference}, a persoa atopou un problema que xa estaba antes."
        )
        if previous:
            text += f" Última reserva anterior: {previous.reference} ({timezone.localtime(previous.end):%d/%m %H:%M})."
        inc = Incident.objects.create(
            municipality=self.vil,
            facility=padel,
            reporter=person,
            prior_to_booking=b,
            category="damage",
            source="start_state",
            description=f"{b.start_state_notes}\n\n{text}",
        )
        Incident.objects.filter(pk=inc.pk).update(created_at=b.start_state_at)

    def safety_reviews(self):
        """Revisións de seguridade inicial feitas en varias instalacións (e unha en curso)."""
        names = [
            ("Pavillón municipal de Vilardeiras", 40),
            ("Pista de pádel da Pereira", 25),
            ("Ximnasio municipal", 12),
            ("Piscina climatizada de Pontedouro", 30),
            ("Pista de pádel 1 da Ribeira", 9),
        ]
        for name, days in names:
            f = Facility.objects.get(name=name)
            order = create_safety_review(f)
            closed = self.now - dt.timedelta(days=days)
            WorkOrder.objects.filter(pk=order.pk).update(
                status=WorkOrder.Status.DONE,
                closed_at=closed,
                due_date=timezone.localdate(closed),
                checklist_state=[{**item, "done": True} for item in order.checklist_state],
                closing_notes="Todo correcto. Reposto o botiquín.",
            )
        # Unha pendente para que se vexa no operario
        create_safety_review(Facility.objects.get(name="Pista exterior de Fontela"))

    def breach(self):
        admin = User.objects.get(email="admin@vilardeiras.demo.eira.example")
        detected = self.now - dt.timedelta(days=45, hours=3)
        DataBreach.objects.create(
            municipality=self.vil,
            detected_at=detected,
            occurred_at=detected - dt.timedelta(hours=2),
            description=(
                "Exemplo ficticio: un correo sobre o adestramento da escola de fútbol enviouse desde "
                "un correo persoal con todos os enderezos das familias á vista (CC en vez de CCO)."
            ),
            data_affected="Enderezos de correo electrónico das familias inscritas",
            people_affected="23 familias (ficticias)",
            risk=DataBreach.Risk.RISK,
            measures=(
                "Pedíuselles ás persoas destinatarias que borrasen o correo. Os avisos das escolas "
                "envíanse sempre desde Eira, que manda un correo por persoa. Formación ao persoal."
            ),
            aepd_notified=True,
            aepd_notified_at=detected + dt.timedelta(hours=30),
            people_informed=True,
            people_informed_at=detected + dt.timedelta(hours=40),
            status=DataBreach.Status.CLOSED,
            closed_at=detected + dt.timedelta(days=6),
            created_by=admin,
            is_demo=True,
        )


def seed():
    Seeder().run()
