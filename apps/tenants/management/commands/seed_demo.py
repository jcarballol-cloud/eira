# SPDX-License-Identifier: EUPL-1.2
"""Datos de demostración: dous concellos e unha deputación FICTICIOS. Ningún dato é real.

python manage.py seed_demo            # crea (ou recrea) os datos
"""

import datetime as dt
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import F, OuterRef, Subquery
from django.utils import timezone

from apps.access.models import AccessEvent, KeyHandover
from apps.accounts.models import (
    AppRequest,
    Consent,
    Dependent,
    Household,
    Membership,
    PadronImport,
    RegionMembership,
    Residency,
    ResidencyInvitation,
    Role,
    User,
)
from apps.bookings.models import Booking
from apps.bookings.services import slot_starts
from apps.facilities.catalog import TEMPLATES, apply_template
from apps.facilities.models import Closure, Facility, Parish
from apps.incidents.models import Incident
from apps.integrations.demo import NEW_NEIGHBOUR
from apps.integrations.models import DevMail, FakePayment, OutboundMessage
from apps.maintenance.models import WorkOrder
from apps.maintenance.services import generate_orders
from apps.notifications.models import Notification
from apps.tenants.models import Municipality, Region

DEMO_DOMAIN = "demo.eira.example"
SEED_LOCK_ID = 7_314_201  # identificador arbitrario do bloqueo consultivo
FIRST_NAMES = [
    "Sabela",
    "Iago",
    "Noa",
    "Roi",
    "Antía",
    "Breixo",
    "Lúa",
    "Xián",
    "Uxía",
    "Anxo",
    "Iria",
    "Brais",
    "Aldara",
    "Martiño",
    "Olalla",
    "Xurxo",
    "Carme",
    "Fiz",
    "Xoana",
    "Lois",
    "Rosalía",
    "Bieito",
    "Maruxa",
    "Tareixa",
    "Ramiro",
    "Comba",
    "Gonzalo",
    "Icía",
    "Paio",
    "Mencía",
]

MUNICIPALITIES = [
    {
        "slug": "vilardeiras",
        "name": "Vilardeiras",
        "population": 1840,
        "ine_code": "99001",
        "accent": "#2E6A4F",
        "center": (42.7710, -7.8930),
        "phone": "982 000 000",
        "email": "deportes@vilardeiras.example",
        "parishes": ["Bustelo", "A Pereira", "Outeiro", "Fontela", "San Martiño"],
        "facilities": [
            ("outdoor_court", "Pista polideportiva de Bustelo", "Bustelo", 0, {"step_free": True}),
            (
                "sports_hall",
                "Pavillón municipal de Vilardeiras",
                "San Martiño",
                1,
                {
                    "key_holder_name": "Bar O Cruce",
                    "key_holder_place": "Praza do Concello, 3",
                    "key_holder_hours": "Todos os días de 8:00 a 23:00",
                    "key_holder_phone": "982 000 101",
                    "key_holder_email": "ocruce@vilardeiras.example",
                    "step_free": True,
                    "adapted_toilet": True,
                    "adapted_changing": True,
                    "accessible_parking": True,
                },
            ),
            ("padel", "Pista de pádel da Pereira", "A Pereira", 2, {"step_free": True}),
            (
                "gym",
                "Ximnasio municipal",
                "San Martiño",
                2,
                {"step_free": True, "adapted_toilet": True},
            ),
            (
                "grass_field",
                "Campo de fútbol de Outeiro",
                "Outeiro",
                1,
                {
                    "key_holder_name": "Asociación veciñal de Outeiro",
                    "key_holder_place": "Local social de Outeiro",
                    "key_holder_hours": "Luns a venres de 17:00 a 21:00",
                    "key_holder_phone": "982 000 102",
                    "key_holder_email": "av.outeiro@vilardeiras.example",
                },
            ),
            ("outdoor_court", "Pista exterior de Fontela", "Fontela", 0, {"lighting": False}),
        ],
    },
    {
        "slug": "pontedouro",
        "name": "Pontedouro",
        "population": 14250,
        "ine_code": "99002",
        "accent": "#2B5C8A",
        "center": (42.4310, -8.6420),
        "phone": "986 000 000",
        "email": "deportes@pontedouro.example",
        "parishes": ["Centro", "A Ribeira", "Monteagudo", "O Castro", "Lamas"],
        "facilities": [
            (
                "pool",
                "Piscina climatizada de Pontedouro",
                "Centro",
                3,
                {
                    "step_free": True,
                    "adapted_toilet": True,
                    "adapted_changing": True,
                    "accessible_parking": True,
                    "accessibility_notes": "Grúa hidráulica para entrar no vaso. Solicítaa na recepción.",
                },
            ),
            (
                "sports_hall",
                "Pavillón do Castro",
                "O Castro",
                3,
                {"step_free": True, "adapted_toilet": True},
            ),
            ("padel", "Pista de pádel 1 da Ribeira", "A Ribeira", 2, {}),
            ("padel", "Pista de pádel 2 da Ribeira", "A Ribeira", 2, {}),
            ("gym", "Ximnasio do Centro", "Centro", 3, {"step_free": True, "adapted_toilet": True}),
            (
                "grass_field",
                "Campo de herba artificial de Lamas",
                "Lamas",
                1,
                {
                    "key_holder_name": "Club Deportivo Lamas",
                    "key_holder_place": "Cafetería do campo",
                    "key_holder_hours": "Luns a sábado de 16:00 a 22:00",
                    "key_holder_phone": "986 000 103",
                    "key_holder_email": "cdlamas@pontedouro.example",
                },
            ),
            ("outdoor_court", "Pista exterior de Monteagudo", "Monteagudo", 0, {}),
        ],
    },
]

PERSONAS = [
    # email, nome, concello, rol, empadroada, ano
    ("uxia@demo.eira.example", "Uxía", "vilardeiras", Role.CITIZEN, True, 1999),
    ("manuel@demo.eira.example", "Manuel", "vilardeiras", Role.CITIZEN, True, 1950),
    ("irene@demo.eira.example", "Irene", "vilardeiras", Role.CITIZEN, False, 1988),
    (
        "admin@vilardeiras.demo.eira.example",
        "Concello de Vilardeiras",
        "vilardeiras",
        Role.ADMIN,
        False,
        None,
    ),
    (
        "admin@pontedouro.demo.eira.example",
        "Concello de Pontedouro",
        "pontedouro",
        Role.ADMIN,
        False,
        None,
    ),
    ("brais@demo.eira.example", "Brais (mantemento)", "vilardeiras", Role.MAINTENANCE, True, 1979),
    ("antia@demo.eira.example", "Antía (monitora)", "vilardeiras", Role.MONITOR, True, 1994),
    ("rosa@demo.eira.example", "Rosa", "pontedouro", Role.CITIZEN, True, 1985),
    ("tino@demo.eira.example", "Tino (mantemento)", "pontedouro", Role.MAINTENANCE, True, 1975),
]


CANCEL_REASONS_ON_TIME = [
    "Cancelada pola persoa con antelación",
    "Cambio de plans (cancelada a tempo)",
    "Cancelada polo concello: actividade municipal",
]
CANCEL_REASONS_LATE = ["Cancelada fóra de prazo (sen devolución)"]


def hour_weight(hour, weekday):
    if weekday >= 5:
        return {10: 0.55, 11: 0.65, 12: 0.55, 13: 0.3, 17: 0.4, 18: 0.45, 19: 0.4}.get(hour, 0.15)
    return {
        7: 0.25,
        8: 0.2,
        9: 0.12,
        10: 0.12,
        11: 0.1,
        12: 0.1,
        13: 0.08,
        14: 0.05,
        15: 0.08,
        16: 0.2,
        17: 0.45,
        18: 0.7,
        19: 0.8,
        20: 0.7,
        21: 0.45,
        22: 0.2,
    }.get(hour, 0.1)


class Command(BaseCommand):
    help = "Carga datos de demostración ficticios (borra os anteriores de demostración)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--if-empty", action="store_true", help="Só se aínda non hai ningún concello"
        )

    def handle(self, *args, **options):
        self.rng = random.Random(2026)
        with transaction.atomic():
            # Serializa cargas simultáneas (p. ex. primeiro arranque da app e rexeneración nocturna)
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_xact_lock(%s)", [SEED_LOCK_ID])
            if options["if_empty"] and Municipality.objects.exists():
                self.stdout.write("Xa hai datos: non se carga a demo.")
                return
            self.reset()
            region = Region.objects.create(
                name="Deputación das Marismas", slug="marismas", kind=Region.Kind.PROVINCE
            )
            self.users = self.create_people()
            for spec in MUNICIPALITIES:
                self.create_municipality(spec, region)
            dep = User.objects.create_user(
                "deputacion@demo.eira.example", display_name="Deputación das Marismas"
            )
            RegionMembership.objects.create(user=dep, region=region)
            self.persona_bookings()
            self.seed_activities()
            self.seed_notices()
            self.new_neighbour()
            # v5: rede, formas de pagamento, aprobación, luz, seguridade e brecha de exemplo
            from apps.tenants.demo_v5 import seed as seed_v5

            seed_v5()
            # v1.1: rexistro de limpeza (Noela, empresa contratada ficticia, en Vilardeiras)
            from apps.tenants.demo_v11 import seed as seed_v11

            seed_v11()
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo lista: {Municipality.objects.count()} concellos, {Facility.objects.count()} instalacións, "
                f"{Booking.objects.count()} reservas, {Incident.objects.count()} incidencias."
            )
        )

    # ------------------------------------------------------------------
    def reset(self):
        Booking.objects.all().delete()
        for m in Municipality.objects.all():
            m.delete()
        Region.objects.all().delete()
        User.objects.filter(email__endswith=DEMO_DOMAIN).delete()
        User.objects.filter(email__endswith=".example").delete()
        User.objects.filter(email__endswith="example.org").delete()
        for model in (DevMail, OutboundMessage, FakePayment, Notification):
            model.objects.all().delete()

    def create_people(self):
        users = {}
        for email, name, *_rest in PERSONAS:
            users[email] = User.objects.create_user(email, display_name=name, birth_year=_rest[-1])
        neighbours = []
        for i, name in enumerate(FIRST_NAMES):
            u = User.objects.create_user(
                f"vecinanza{i:02d}@{DEMO_DOMAIN}",
                display_name=name,
                birth_year=self.rng.randint(1945, 2010),
                photo_consent=i % 4 != 0,  # unha de cada catro non autoriza fotos
            )
            neighbours.append(u)
        users["neighbours"] = neighbours
        return users

    def create_municipality(self, spec, region):
        m = Municipality.objects.create(
            name=spec["name"],
            slug=spec["slug"],
            region=region,
            population=spec["population"],
            ine_code=spec["ine_code"],
            accent_color=spec["accent"],
            contact_phone=spec["phone"],
            contact_email=spec["email"],
            address="Praza do Concello, 1",
            dpo_contact=f"dpd@{spec['slug']}.example · Praza do Concello, 1",
            # Códigos postais ficticios: o padrón simulado recoñece estes
            postcodes={"vilardeiras": "15999,15998"}.get(spec["slug"], "27999"),
            modules={
                "bookings": True,
                "access": True,
                "incidents": True,
                "maintenance": True,
                "activities": True,
                "monitor": True,
                "observatory": True,
                "weather": True,
                "health": True,
                "ai_summary": True,
                "opendata": True,
            },
        )
        parishes = {
            name: Parish.objects.create(municipality=m, name=name) for name in spec["parishes"]
        }
        lat0, lon0 = spec["center"]
        facilities = []
        for key, name, parish, level, extra in spec["facilities"]:
            t = TEMPLATES[key]
            f = Facility.objects.create(
                municipality=m,
                name=name,
                kind=t["kind"],
                parish=parishes[parish],
                description=str(t["description"]),
                address=f"Lugar de {parish}, s/n",
                latitude=Decimal(f"{lat0 + self.rng.uniform(-0.03, 0.03):.6f}"),
                longitude=Decimal(f"{lon0 + self.rng.uniform(-0.04, 0.04):.6f}"),
                indoor=t["indoor"],
                lighting=extra.pop("lighting", t["lighting"]),
                capacity=t["capacity"],
                slot_minutes=t["slot_minutes"],
                access_level=level,
                **extra,
            )
            # v1.1: a limpeza da demo créaa demo_v11 só onde toca (pavillón de Vilardeiras)
            apply_template(f, key, cleaning=False)
            if f.step_free:  # accesibilidade completa nas instalacións cubertas grandes
                f.lift = f.indoor and t["kind"] != "padel"
                f.hearing_loop = t["kind"] in ("sports_hall", "pool")
                f.braille_signage = t["kind"] == "pool"
                f.save(update_fields=["lift", "hearing_loop", "braille_signage"])
            facilities.append(f)
        # Persoas: roles e empadroamento
        for email, _name, slug, role, resident, _year in PERSONAS:
            if slug != m.slug:
                continue
            user = self.users[email]
            Membership.objects.get_or_create(user=user, municipality=m, role=role)
            if resident:
                Residency.objects.create(user=user, municipality=m, method=Residency.Method.COUNTER)
        local = (
            self.users["neighbours"][:18]
            if m.slug == "vilardeiras"
            else self.users["neighbours"][10:]
        )
        for u in local:
            Membership.objects.get_or_create(user=u, municipality=m, role=Role.CITIZEN)
            if self.rng.random() < 0.85:
                Residency.objects.create(user=u, municipality=m, method=Residency.Method.COUNTER)
        for _ in range(3):
            ResidencyInvitation.issue(m, note="Carta de benvida")
        self.app_requests(m)
        self.history(m, facilities, local)
        self.closures(m, facilities)
        self.incidents_and_orders(m, facilities)

    def padron(self, m):
        """v4: padrón ficticio cargado por CSV (só se gardan os HMAC). DNI de proba con letra
        correcta xerados a partir de números inventados; nunca datos reais."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.accounts import padron

        def dni(n):
            return f"{n:08d}{padron.LETTERS[n % 23]}"

        rows = ["dni_nie;data_nacemento"]
        base = 70000000 if m.slug == "vilardeiras" else 71000000
        rng = random.Random(f"padron-{m.slug}")  # propio, para non mover o resto da seed
        for i in range(400):
            born = dt.date(1940, 1, 1) + dt.timedelta(days=rng.randint(0, 365 * 75))
            rows.append(f"{dni(base + i * 7)};{born:%d/%m/%Y}")
        if m.slug == "vilardeiras":
            # Persoa do guión do pitch: ao pedir a app con estes datos, alta automática
            rows.append("12345678Z;14/05/1990")
        admin = User.objects.filter(
            memberships__municipality=m, memberships__role=Role.ADMIN
        ).first()
        padron.import_csv(m, SimpleUploadedFile("padron.csv", "\n".join(rows).encode()), by=admin)
        PadronImport.objects.filter(municipality=m).update(
            imported_at=timezone.now() - dt.timedelta(days=6)
        )

    def app_requests(self, m):
        """Solicitudes da app: pendentes de revisar co motivo e algunhas xa enviadas (ficticias)."""
        self.padron(m)
        pending = [
            # Non figura: DNI que non está no padrón cargado
            (
                "Breixo",
                "Proba Souto",
                "breixo.solicitude@example.org",
                "00000002W",
                dt.date(1987, 3, 9),
                "Rúa do Exemplo, 4",
            ),
            # A data non coincide (un erro ao teclear ou un padrón desactualizado)
            (
                "Antía",
                "Exemplo Rial",
                "antia.solicitude@example.org",
                "00000003A",
                dt.date(1992, 11, 21),
                "",
            ),
        ]
        if m.slug != "vilardeiras":
            pending = pending[:1]
        for name, surnames, email, id_number, born, address in pending:
            AppRequest.objects.create(
                municipality=m,
                name=name,
                surnames=surnames,
                email=email if m.slug == "vilardeiras" else f"{m.slug}.{email}",
                id_number=id_number,
                birth_date=born,
                birth_year=born.year,
                address=address,
                review_reason="no_match",
            )
        for i, (name, channel) in enumerate(
            [("Persoa de mostrador 1", "counter"), ("Persoa en liña 1", "online")]
        ):
            inv = ResidencyInvitation.issue(m, note=f"Solicitude da app · {name}")
            AppRequest.objects.create(
                municipality=m,
                name=name,
                email="" if channel == "counter" else f"enlinea{i}.{m.slug}@example.org",
                birth_year=1970 + 10 * i,
                postcode=m.postcodes.split(",")[0],
                channel=channel,
                status=AppRequest.Status.SENT,
                padron_match=True,
                invitation=inv,
                resolved_at=timezone.now(),
            )

    def ratings_for(self, m, facilities):
        """Valoracións de exemplo: a maioría «Ben»; a pista exterior ten as luces mal."""
        from apps.bookings.models import Rating

        comments = {
            "good": [
                "Todo perfecto, moi limpa.",
                "O código funcionou á primeira.",
                "Grazas por ter a pista tan coidada.",
            ],
            "ok": ["Ben, pero faltaba unha rede.", "Vestiarios algo fríos."],
            "bad": [
                "Dúas lámpadas non acendían e xa era de noite.",
                "A porta custaba de pechar.",
                "Había auga no chan da pista.",
            ],
        }
        trouble = next((f for f in facilities if f.kind == "outdoor_court"), facilities[-1])
        since = timezone.now() - dt.timedelta(days=60)
        rows = []
        for b in Booking.objects.filter(municipality=m, status="used", start__gte=since):
            if self.rng.random() > 0.3:
                continue
            bad_bias = 0.35 if b.facility_id == trouble.pk else 0.06
            r = self.rng.random()
            score = "bad" if r < bad_bias else ("ok" if r < bad_bias + 0.18 else "good")
            if score == "good":
                tags = self.rng.sample(
                    ["clean", "light", "gear", "access", "quiet"], self.rng.randint(0, 2)
                )
            elif score == "ok":
                tags = self.rng.sample(
                    ["dirty", "gear_broken", "water", "clean"], self.rng.randint(0, 1)
                )
            else:
                tags = (
                    ["lights_broken"]
                    if b.facility_id == trouble.pk
                    else self.rng.sample(["dirty", "gear_broken", "access_problem"], 1)
                )
            comment = self.rng.choice(comments[score]) if self.rng.random() < 0.15 else ""
            rows.append(
                Rating(
                    municipality=m,
                    booking=b,
                    facility_id=b.facility_id,
                    score=score,
                    tags=tags,
                    comment=comment,
                )
            )
        Rating.objects.bulk_create(rows, batch_size=1000)
        Rating.objects.filter(municipality=m).update(
            created_at=Subquery(Booking.objects.filter(pk=OuterRef("booking_id")).values("end")[:1])
        )

    def history(self, m, facilities, people):
        today = timezone.localdate()
        now = timezone.now()
        bookings = []
        popularity = {f.pk: self.rng.uniform(0.25, 1.0) for f in facilities}
        resident_ids = set(
            Residency.objects.filter(municipality=m).values_list("user_id", flat=True)
        )
        # Un par de instalacións quedan infrautilizadas para que o indicador teña sentido
        popularity[facilities[-1].pk] = 0.08
        for f in facilities:
            rules = f.current_rules()
            tariffs = {t.audience: t.price_cents for t in f.tariffs.all()}
            for offset in range(-56, 15):
                day = today + dt.timedelta(days=offset)
                for start in slot_starts(f, day):
                    local = timezone.localtime(start)
                    p = hour_weight(local.hour, local.weekday()) * popularity[f.pk]
                    n = (
                        sum(1 for _ in range(f.capacity) if self.rng.random() < p)
                        if f.capacity > 1
                        else int(self.rng.random() < p)
                    )
                    if offset > 0:
                        n = int(n * max(0.2, 1 - offset / 15))  # menos reservas canto máis lonxe
                    for _ in range(n):
                        end = start + dt.timedelta(minutes=f.slot_minutes)
                        user = self.rng.choice(people)
                        audience = "resident" if user.pk in resident_ids else "non_resident"
                        price = tariffs.get(audience, tariffs.get("resident", 0))
                        if end <= now:
                            r = self.rng.random()
                            status = (
                                "used" if r < 0.86 else ("no_show" if r < 0.96 else "cancelled")
                            )
                            if status == "no_show" and f.access_level == 0:
                                status = (
                                    "used"  # nivel 0: o QR é voluntario, non hai «non presentadas»
                                )
                        else:
                            status = "confirmed" if self.rng.random() < 0.97 else "cancelled"
                        checked = (
                            start + dt.timedelta(minutes=self.rng.randint(-5, 10))
                            if status == "used"
                            else None
                        )
                        channel = self.rng.choices(["online", "phone", "counter"], [85, 10, 5])[0]
                        # Cancelacións: a maioría a tempo (devolución íntegra); algunhas tarde, sen devolución
                        refund, reason = 0, ""
                        if status == "cancelled":
                            on_time = self.rng.random() < 0.8
                            refund = price if on_time else 0
                            reason = self.rng.choice(
                                CANCEL_REASONS_ON_TIME if on_time else CANCEL_REASONS_LATE
                            )
                        bookings.append(
                            Booking(
                                municipality=m,
                                facility=f,
                                user=user,
                                start=start,
                                end=end,
                                status=status,
                                channel=channel,
                                tariff_audience=audience,
                                price_cents=price,
                                paid_cents=price if status != "pending_payment" else 0,
                                refunded_cents=refund,
                                cancel_reason=reason,
                                payment_reference=f"FRDEMO{self.rng.randint(10**7, 10**8)}"
                                if price
                                else "",
                                rules_version=rules,
                                rules_accepted_at=start - dt.timedelta(days=2),
                                checked_in_at=checked,
                                closed_at=end + dt.timedelta(minutes=5)
                                if status == "used" and self.rng.random() < 0.6
                                else None,
                                close_door_ok=True if status == "used" else None,
                                close_all_ok=True if status == "used" else None,
                                cancelled_at=start - dt.timedelta(days=1)
                                if status == "cancelled"
                                else None,
                            )
                        )
        Booking.objects.bulk_create(bookings, batch_size=1000)
        Booking.objects.filter(municipality=m).update(created_at=F("start") - dt.timedelta(days=2))
        self.payments_for(m)
        self.ratings_for(m, facilities)
        # Eventos de acceso coherentes (mostra) e entregas de chave
        events = []
        for b in Booking.objects.filter(municipality=m, status="used").select_related("facility")[
            :1500
        ]:
            kind = {0: "checkin", 1: "key_out", 2: "code_ok", 3: "remote_open"}[
                b.facility.access_level
            ]
            events.append(
                AccessEvent(
                    municipality=m, facility=b.facility, booking=b, kind=kind, at=b.checked_in_at
                )
            )
        AccessEvent.objects.bulk_create(events, batch_size=1000)

    def payments_for(self, m):
        """Cobros históricos coherentes coas reservas (para a conciliación)."""
        from apps.bookings.models import Payment
        from apps.bookings.payments import new_reference

        method = {"online": "online", "phone": "card_terminal", "counter": "cash"}
        rows = []
        for b in Booking.objects.filter(municipality=m, paid_cents__gt=0).select_related(
            "facility"
        ):
            status = (
                Payment.Status.REFUNDED if b.refunded_cents >= b.paid_cents else Payment.Status.PAID
            )
            rows.append(
                Payment(
                    municipality=m,
                    booking=b,
                    concept=f"{b.facility.name} · {b.reference}",
                    amount_cents=b.paid_cents,
                    refunded_cents=b.refunded_cents,
                    status=status,
                    method=method.get(b.channel, "online"),
                    reference=new_reference(),
                    signature_ok=b.channel == "online",
                    provider_code="0000",
                )
            )
        Payment.objects.bulk_create(rows, batch_size=1000)
        Payment.objects.filter(municipality=m).update(
            created_at=Subquery(
                Booking.objects.filter(pk=OuterRef("booking_id")).values("created_at")[:1]
            )
        )
        # algúns intentos rexeitados para que a conciliación os mostre
        for b in Booking.objects.filter(municipality=m, status="cancelled", paid_cents=0)[:6]:
            Payment.objects.create(
                municipality=m,
                booking=b,
                concept=f"{b.facility.name} · {b.reference}",
                amount_cents=b.price_cents or 400,
                status=Payment.Status.REJECTED,
                reference=new_reference(),
                provider_code="0190",
                signature_ok=True,
            )

    def closures(self, m, facilities):
        today = timezone.localdate()
        holiday = today + dt.timedelta(
            days=(5 - today.weekday()) % 7 + 7
        )  # sábado da semana que vén
        Closure.objects.create(
            municipality=m,
            kind=Closure.Kind.HOLIDAY,
            reason="Festas patronais",
            starts_at=timezone.make_aware(dt.datetime.combine(holiday, dt.time(0))),
            ends_at=timezone.make_aware(dt.datetime.combine(holiday, dt.time(23, 59))),
        )
        works = today + dt.timedelta(days=4)
        Closure.objects.create(
            municipality=m,
            facility=facilities[0],
            kind=Closure.Kind.WORKS,
            reason="Pintado das liñas da pista",
            starts_at=timezone.make_aware(dt.datetime.combine(works, dt.time(9))),
            ends_at=timezone.make_aware(dt.datetime.combine(works, dt.time(14))),
        )
        Booking.objects.filter(municipality=m, start__date=holiday, status="confirmed").update(
            status="cancelled",
            cancelled_at=timezone.now(),
            cancel_reason="Peche da instalación: Festas patronais",
        )

    def incidents_and_orders(self, m, facilities):
        today = timezone.localdate()
        generate_orders(days=14, today=today - dt.timedelta(days=13), municipality=m)
        generate_orders(days=14, today=today, municipality=m)
        staff = (
            Membership.objects.filter(municipality=m, role=Role.MAINTENANCE)
            .select_related("user")
            .first()
        )
        WorkOrder.objects.filter(municipality=m, due_date__lt=today).update(
            status=WorkOrder.Status.DONE, closed_at=timezone.now() - dt.timedelta(days=1)
        )
        # Algunhas atrasadas para que se vexan
        for o in WorkOrder.objects.filter(municipality=m, due_date__lt=today).order_by("?")[:2]:
            o.status, o.closed_at = WorkOrder.Status.OPEN, None
            o.save()
        if staff:
            WorkOrder.objects.filter(municipality=m, due_date__gte=today).update(
                assigned_to=staff.user
            )
            if m.slug == "vilardeiras":
                # v4.1: Brais adiantou hoxe as tarefas de mañá, así o filtro «Mañá» do operario
                # mostra o estado baleiro «todo ao día» (o xerador non as volve crear).
                WorkOrder.objects.filter(
                    municipality=m, due_date=today + dt.timedelta(days=1)
                ).update(status=WorkOrder.Status.DONE, closed_at=timezone.now())
        people = self.users["neighbours"]
        specs = [
            (
                facilities[0],
                "lighting",
                "Unha das torres de luz non acende.",
                Incident.Status.RECEIVED,
                0,
            ),
            (
                facilities[1],
                "water",
                "As duchas do vestiario 2 saen frías.",
                Incident.Status.VALIDATED,
                1,
            ),
            (
                facilities[2],
                "damage",
                "A rede da pista está descosida nun lateral.",
                Incident.Status.WORK_ORDER,
                2,
            ),
            (
                facilities[3],
                "cleaning",
                "Papeleira rota xunto á entrada.",
                Incident.Status.RESOLVED,
                6,
            ),
            (
                facilities[4],
                "access",
                "A porta do vestiario non pecha ben.",
                Incident.Status.RESOLVED,
                12,
            ),
            (facilities[1], "safety", "Un banco solto na bancada.", Incident.Status.RECEIVED, 0),
        ]
        for f, cat, text, status, days_ago in specs:
            created = timezone.now() - dt.timedelta(days=days_ago, hours=self.rng.randint(1, 8))
            inc = Incident.objects.create(
                municipality=m,
                facility=f,
                reporter=self.rng.choice(people),
                category=cat,
                description=text,
                status=status,
            )
            Incident.objects.filter(pk=inc.pk).update(
                created_at=created,
                validated_at=created + dt.timedelta(hours=3) if status != "received" else None,
                resolved_at=created + dt.timedelta(days=2) if status == "resolved" else None,
                resolution_note="Arranxado polo equipo de mantemento."
                if status == "resolved"
                else "",
            )
            if status in ("work_order", "resolved"):
                WorkOrder.objects.create(
                    municipality=m,
                    facility=f,
                    incident=inc,
                    title=f"Incidencia #{inc.pk}: {inc.get_category_display()}",
                    description=text,
                    due_date=today
                    if status == "work_order"
                    else today - dt.timedelta(days=days_ago - 1),
                    assigned_to=staff.user if staff else None,
                    status=WorkOrder.Status.OPEN
                    if status == "work_order"
                    else WorkOrder.Status.DONE,
                    checklist_state=[
                        {"label": "Revisar e reparar", "done": False},
                        {"label": "Deixar a zona segura e limpa", "done": False},
                    ],
                )
        # Unha incidencia xerada polo checklist de peche
        b = (
            Booking.objects.filter(municipality=m, status="used", facility=facilities[1])
            .order_by("-start")
            .first()
        )
        if b:
            b.close_door_ok = False
            b.save(update_fields=["close_door_ok"])
            Incident.objects.create(
                municipality=m,
                facility=b.facility,
                reporter=b.user,
                booking=b,
                category="access",
                source="checklist",
                description="A porta non quedou pechada.",
            )

    def persona_bookings(self):
        """Reservas das persoas da demo, preparadas para o guión do pitch."""
        m = Municipality.objects.get(slug="vilardeiras")
        uxia = User.objects.get(email="uxia@demo.eira.example")
        manuel = User.objects.get(email="manuel@demo.eira.example")
        gym = Facility.objects.get(municipality=m, kind="gym")
        padel = Facility.objects.get(municipality=m, kind="padel")
        hall = Facility.objects.get(municipality=m, kind="sports_hall")
        now = timezone.now()

        def next_slot(f, after, hour=None):
            """Primeira franxa da instalación que comeza despois de `after` (opcionalmente a unha hora)."""
            for i in range(0, 10):
                for s_ in slot_starts(f, timezone.localdate(after) + dt.timedelta(days=i)):
                    if s_ >= after and (hour is None or timezone.localtime(s_).hour == hour):
                        return s_
            return None

        def last_finished(f):
            for i in range(0, 4):
                past = [
                    s_
                    for s_ in slot_starts(f, timezone.localdate() - dt.timedelta(days=i))
                    if s_ + dt.timedelta(minutes=f.slot_minutes) <= now
                ]
                if past:
                    return past[-1]
            return None

        def make(f, user, start, status="confirmed"):
            if start is None:
                return None
            end = start + dt.timedelta(minutes=f.slot_minutes)
            Booking.objects.filter(facility=f, start__lt=end, end__gt=start).exclude(
                user=user
            ).filter(status__in=["confirmed", "pending_payment", "used"]).update(status="cancelled")
            audience = "senior" if user == manuel else "resident"
            price = {t.audience: t.price_cents for t in f.tariffs.all()}.get(audience, 0)
            from apps.bookings.models import Payment
            from apps.bookings.payments import new_reference

            ref = new_reference() if price else ""
            booking = Booking.objects.create(
                municipality=f.municipality,
                facility=f,
                user=user,
                start=start,
                end=end,
                status=status,
                tariff_audience=audience,
                price_cents=price,
                base_price_cents=price,
                paid_cents=price,
                payment_reference=ref,
                rules_version=f.current_rules(),
                rules_accepted_at=now - dt.timedelta(days=1),
            )
            if price:
                Payment.objects.create(
                    municipality=f.municipality,
                    booking=booking,
                    concept=f"{f.name} · {booking.reference}",
                    amount_cents=price,
                    status=Payment.Status.PAID,
                    reference=ref,
                    signature_ok=True,
                    provider_code="0000",
                    resolved_at=now,
                )
            return booking

        # Uxía: reserva no ximnasio (nivel 2) en curso ou a seguinte franxa aberta: o código próbase no simulador
        current = None
        for s_ in slot_starts(gym, timezone.localdate()):
            if s_ <= now < s_ + dt.timedelta(minutes=gym.slot_minutes):
                current = s_
        make(gym, uxia, current or next_slot(gym, now))
        # Uxía: pádel ás 19:30 do próximo día e unha reserva xa rematada (checklist de peche pendente)
        make(padel, uxia, next_slot(padel, now + dt.timedelta(hours=12), hour=19))
        b = make(padel, uxia, last_finished(padel), status="used")
        if b:
            b.checked_in_at = b.start
            b.save(update_fields=["checked_in_at"])
        # Historial de Uxía: pasa a ela algunhas reservas pasadas dos veciños
        past = Booking.objects.filter(
            municipality=m, status__in=["used", "no_show"], end__lt=now - dt.timedelta(days=1)
        )
        Booking.objects.filter(
            pk__in=list(past.order_by("-start").values_list("pk", flat=True)[:40:5])
        ).update(user=uxia)
        # Manuel: ximnasio ás 10:00 e pavillón (chave custodiada) ás 11:00
        make(gym, manuel, next_slot(gym, now + dt.timedelta(days=1), hour=10))
        b = make(hall, manuel, next_slot(hall, now + dt.timedelta(days=1), hour=11))
        if b:
            KeyHandover.objects.create(municipality=m, booking=b, custodian_notified_at=now)
        # Rosa (Pontedouro): unha reserva próxima para que a súa app teña contido
        rosa = User.objects.get(email="rosa@demo.eira.example")
        pd = Municipality.objects.get(slug="pontedouro")
        for f in Facility.objects.filter(municipality=pd, access_level__gte=2).order_by("pk")[:2]:
            make(f, rosa, next_slot(f, now + dt.timedelta(hours=20), hour=18))
        # Unidade familiar de Uxía con dúas crianzas
        hh = Household.objects.create(responsible=uxia)
        for name, year in (
            ("Noa", timezone.localdate().year - 9),
            ("Breixo", timezone.localdate().year - 12),
        ):
            d = Dependent.objects.create(household=hh, first_name=name, birth_year=year)
            Consent.objects.create(dependent=d, kind="data", granted_by=uxia)
            Consent.objects.create(dependent=d, kind="performance", granted_by=uxia)

    def new_neighbour(self):
        """v4.1: Brais, veciño novo de Vilardeiras, dado de alta despois de todo o demais: sen
        reservas, avisos nin inscricións, para que se vexan os estados baleiros."""
        m = Municipality.objects.get(slug="vilardeiras")
        user = User.objects.create_user(NEW_NEIGHBOUR, display_name="Brais", birth_year=2001)
        Membership.objects.create(user=user, municipality=m, role=Role.CITIZEN)
        Residency.objects.create(user=user, municipality=m, method=Residency.Method.COUNTER)

    def seed_notices(self):
        """v4: avisos do concello, preferencias, bot de Telegram e correos coherentes coas reservas."""
        from apps.notifications.demo import seed

        seed(self.rng)

    def seed_activities(self):
        """Escolas deportivas (P3). Defínese en apps.activities.demo se existe."""
        try:
            from apps.activities.demo import seed
        except ImportError:
            return
        seed(self.rng)
