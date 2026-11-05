# SPDX-License-Identifier: EUPL-1.2
"""v1.5: demo coherente con A–F. Concellos, persoas e datos ficticios.

- Parroquias de residencia con fluxos por riba e por debaixo do limiar (n ≥ 10).
- Documentos legais aceptados en varias versións (e un consentimento retirado).
- Unha monitora pendente de acreditación e unha voluntaria con revisión vencida.
- Alertas lanzadas desde as apps de mantemento e de limpeza.
"""

import datetime as dt
from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import Membership, Residency, Role, User
from apps.activities import accreditation
from apps.activities.models import Activity, Group, MinorsAccreditation
from apps.bookings.models import Booking
from apps.bookings.services import slot_starts
from apps.facilities.models import Facility, Parish
from apps.legal import services as legal
from apps.legal.models import DocKind, LegalAcceptance
from apps.safety.models import Alert, ResponsibleContact
from apps.tenants.models import Municipality, Region

DOMAIN = "demo.eira.example"
CENTERS = {
    "vilardeiras": (Decimal("42.771000"), Decimal("-7.893000")),
    "pontedouro": (Decimal("42.431000"), Decimal("-8.642000")),
}
# Desprazamentos ficticios (graos) de cada parroquia respecto do centro do concello
OFFSETS = [
    (Decimal("0.022"), Decimal("-0.030")),
    (Decimal("-0.024"), Decimal("-0.022")),
    (Decimal("0.026"), Decimal("0.028")),
    (Decimal("-0.020"), Decimal("0.034")),
    (Decimal("0.002"), Decimal("0.046")),
]
# (nome, cantas persoas) para as veciñas da demo de cada concello
VIL_SHARES = [("Bustelo", 12), ("A Pereira", 4), ("Outeiro", 2)]


class Seeder:
    def __init__(self):
        self.region = Region.objects.get(slug="marismas")
        self.vil = Municipality.objects.get(slug="vilardeiras")
        self.pon = Municipality.objects.get(slug="pontedouro")
        self.admin = User.objects.get(email=f"admin@vilardeiras.{DOMAIN}")
        self.now = timezone.now()

    def run(self):
        self.positions()
        self.residences()
        self.mobility_people()
        self.legal_documents()
        self.accreditations()
        self.alerts()

    # ------------------------------------------------------------ C · procedencia
    def positions(self):
        for town in (self.vil, self.pon):
            lat, lon = CENTERS[town.slug]
            town.latitude, town.longitude = lat, lon
            town.save(update_fields=["latitude", "longitude"])
            for parish, (d_lat, d_lon) in zip(
                Parish.objects.filter(municipality=town).order_by("pk"), OFFSETS, strict=False
            ):
                parish.latitude, parish.longitude = lat + d_lat, lon + d_lon
                parish.save(update_fields=["latitude", "longitude"])

    def _parish(self, town, name):
        return Parish.objects.get(municipality=town, name=name)

    def residences(self):
        neighbours = list(User.objects.filter(email__startswith="vecinanza").order_by("email"))
        start = 0
        for name, count in VIL_SHARES:
            parish = self._parish(self.vil, name)
            for user in neighbours[start : start + count]:
                user.residence_parish = parish
                user.save(update_fields=["residence_parish"])
            start += count
        parishes = list(Parish.objects.filter(municipality=self.pon).order_by("pk"))
        for index, user in enumerate(neighbours[start:]):
            user.residence_parish = parishes[index % 2]
            user.save(update_fields=["residence_parish"])
        people = {
            "uxia": self._parish(self.vil, "Bustelo"),
            "manuel": self._parish(self.vil, "A Pereira"),
            "rosa": self._parish(self.pon, "A Ribeira"),
        }
        for slug, parish in people.items():
            user = User.objects.get(email=f"{slug}@{DOMAIN}")
            user.residence_parish = parish
            user.save(update_fields=["residence_parish"])
        irene = User.objects.get(email=f"irene@{DOMAIN}")
        irene.residence_municipality = self.pon
        irene.save(update_fields=["residence_municipality"])

    def _visits(self, users, facility):
        """Só reservas pasadas e en franxas con sitio: non cambian a dispoñibilidade de hoxe."""
        today = timezone.localdate()
        created = []
        taken = {}
        for index, user in enumerate(users):
            for visit in range(2):
                for delta in range(3 + (index * 3 + visit * 11) % 45, 56):
                    day = today - dt.timedelta(days=delta)
                    starts = [s for s in slot_starts(facility, day) if s < self.now]
                    free = [
                        s
                        for s in starts
                        if Booking.objects.filter(
                            facility=facility,
                            start=s,
                            status__in=[Booking.Status.USED, Booking.Status.CONFIRMED],
                        ).count()
                        + taken.get(s, 0)
                        < facility.capacity
                    ]
                    if free:
                        start = free[index % len(free)]
                        taken[start] = taken.get(start, 0) + 1
                        created.append(
                            Booking(
                                municipality=facility.municipality,
                                facility=facility,
                                user=user,
                                start=start,
                                end=start + dt.timedelta(minutes=facility.slot_minutes),
                                status=Booking.Status.USED,
                                checked_in_at=start,
                            )
                        )
                        break
        Booking.objects.bulk_create(created)

    def _mobile_people(self, prefix, count, town, parish):
        users = []
        for i in range(count):
            user = User.objects.create_user(
                f"{prefix}{i:02d}@{DOMAIN}",
                display_name=f"Persoa {prefix} {i + 1}",
                birth_year=1960 + i,
                residence_parish=parish,
            )
            Residency.objects.create(user=user, municipality=town, method="counter")
            users.append(user)
        return users

    def mobility_people(self):
        """Por riba do limiar: Vilardeiras → piscina de Pontedouro (14) e Pontedouro → pavillón de
        Vilardeiras (12). Por debaixo: 4 de Vilardeiras no ximnasio de Pontedouro, que van a
        «outras procedencias»."""
        pool = (
            Facility.objects.filter(municipality=self.pon, kind="pool").order_by("pk").first()
            or Facility.objects.filter(municipality=self.pon).order_by("-capacity").first()
        )
        hall = Facility.objects.filter(municipality=self.vil).order_by("-capacity", "pk").first()
        outbound = self._mobile_people(
            "mobilidadev", 14, self.vil, self._parish(self.vil, "Fontela")
        )
        inbound = self._mobile_people("mobilidadep", 12, self.pon, self._parish(self.pon, "Centro"))
        few = self._mobile_people("mobilidadez", 4, self.vil, self._parish(self.vil, "San Martiño"))
        self._visits(outbound, pool)
        self._visits(inbound, hall)
        other = (
            Facility.objects.filter(municipality=self.pon)
            .exclude(pk=pool.pk)
            .order_by("-capacity", "pk")
            .first()
        )
        self._visits(few, other)

    # ------------------------------------------------------------ D · documentos legais
    def _publish_all(self, town, kinds):
        values = legal.default_values(town)
        versions = {}
        for kind in kinds:
            versions[kind] = legal.publish_version(
                town, kind, legal.latest_model(self.region, kind), by=self.admin, **values
            )
            versions[kind].published_at = self.now - dt.timedelta(days=120)
            versions[kind].save(update_fields=["published_at"])
        return versions

    def _accept(self, user, version, *, days=100, channel="app", withdrawn_days=None):
        LegalAcceptance.objects.create(
            municipality=version.municipality,
            user=user,
            version=version,
            accepted_at=self.now - dt.timedelta(days=days),
            channel=channel,
            withdrawn_at=self.now - dt.timedelta(days=withdrawn_days) if withdrawn_days else None,
        )

    def legal_documents(self):
        # A deputación publica no seu repositorio dous modelos; o resto, os incluídos en Eira
        for kind in (DocKind.PRIVACY, DocKind.TERMS):
            base = legal.included_model(kind)
            legal.publish_model(
                self.region,
                kind,
                title_gl=base.title_gl,
                title_es=base.title_es,
                body_gl=base.body_gl,
                body_es=base.body_es,
            )
        versions = self._publish_all(self.vil, list(DocKind))
        self._publish_all(self.pon, [DocKind.PRIVACY, DocKind.TERMS])
        values = legal.default_values(self.vil)
        # Privacidade v2 sen cambios substanciais: non se pide volver aceptar
        privacy_v2 = legal.publish_version(
            self.vil,
            DocKind.PRIVACY,
            legal.latest_model(self.region, DocKind.PRIVACY),
            substantial=False,
            by=self.admin,
            **values,
        )
        privacy_v2.published_at = self.now - dt.timedelta(days=40)
        privacy_v2.save(update_fields=["published_at"])
        # Condicións v2 con cambios substanciais: pídese volver aceptar
        terms_v2 = legal.publish_version(
            self.vil,
            DocKind.TERMS,
            legal.latest_model(self.region, DocKind.TERMS),
            substantial=True,
            by=self.admin,
            **values,
        )
        terms_v2.published_at = self.now - dt.timedelta(days=10)
        terms_v2.save(update_fields=["published_at"])

        # Uxía aceptou a v1 e ten pendentes as condicións novas; retirou a imaxe
        uxia = User.objects.get(email=f"uxia@{DOMAIN}")
        self._accept(uxia, versions[DocKind.PRIVACY])
        self._accept(uxia, versions[DocKind.TERMS])
        self._accept(uxia, versions[DocKind.RULES], channel="web")
        self._accept(uxia, versions[DocKind.IMAGE], withdrawn_days=30)
        self._accept(uxia, versions[DocKind.HEALTH], days=50)
        # Manuel aceptou no mostrador e despois as condicións novas
        manuel = User.objects.get(email=f"manuel@{DOMAIN}")
        self._accept(manuel, versions[DocKind.PRIVACY], channel="counter")
        self._accept(manuel, versions[DocKind.TERMS], channel="counter")
        self._accept(manuel, versions[DocKind.RULES], channel="counter")
        self._accept(manuel, terms_v2, days=5, channel="counter")
        # Máis persoas en varias versións, para que o rexistro CSV teña contido
        people = User.objects.filter(email__startswith="vecinanza").order_by("email")[:12]
        for index, user in enumerate(people):
            self._accept(user, privacy_v2 if index % 3 == 0 else versions[DocKind.PRIVACY])
            self._accept(user, terms_v2 if index % 2 == 0 else versions[DocKind.TERMS], days=4)
            self._accept(user, versions[DocKind.RULES], channel="web" if index % 4 == 0 else "app")

    # ------------------------------------------------------------ E · acreditación
    def accreditations(self):
        antia = User.objects.get(email=f"antia@{DOMAIN}")
        record = accreditation.confirm(self.vil, antia, by=self.admin)
        record.confirmed_at = self.now - dt.timedelta(days=200)
        record.save(update_fields=["confirmed_at"])
        # Pendente: non se pode asignar ao grupo infantil ata marcala
        sabela = User.objects.create_user(f"sabela@{DOMAIN}", display_name="Sabela")
        Membership.objects.create(user=sabela, municipality=self.vil, role=Role.MONITOR)
        activity = Activity.objects.filter(municipality=self.vil).order_by("pk").first()
        Group.objects.create(
            municipality=self.vil,
            activity=activity,
            name="Grupo novo (sen monitora)",
            min_age=8,
            max_age=12,
            weekdays="1,3",
            start_time=dt.time(17, 30),
        )
        # Voluntaria con revisión vencida: o concello recibe o aviso ao executar booking_maintenance
        xian = User.objects.create_user(f"xian@{DOMAIN}", display_name="Xián")
        Membership.objects.create(
            user=xian, municipality=self.vil, role=Role.MONITOR, is_volunteer=True
        )
        MinorsAccreditation.objects.create(
            municipality=self.vil,
            user=xian,
            confirmed_by=self.admin,
            confirmed_at=self.now - dt.timedelta(days=400),
        )

    # ------------------------------------------------------------ B · alertas
    def alerts(self):
        hall = Facility.objects.filter(municipality=self.vil).order_by("-capacity", "pk").first()
        ResponsibleContact.objects.create(
            municipality=self.vil,
            order=9,
            name="Conserxe do ximnasio",
            role_label="Conserxe",
            email=f"conserxe@vilardeiras.{DOMAIN}",
            facility=hall,
            from_time=dt.time(8, 0),
            until_time=dt.time(22, 0),
        )
        brais = User.objects.get(email=f"brais@{DOMAIN}")
        noela = User.objects.get(email=f"noela@{DOMAIN}")
        for user, origin, kind, days in (
            (brais, Alert.Origin.OPERATOR, Alert.Kind.SECURITY, 12),
            (noela, Alert.Origin.CLEANING, Alert.Kind.ACCIDENT, 20),
        ):
            at = self.now - dt.timedelta(days=days)
            Alert.objects.create(
                municipality=self.vil,
                kind=kind,
                origin=origin,
                facility=hall,
                raised_by=user,
                notified=["Conserxe", "Persoa monitora", "Administración do concello"],
                created_at=at,
                acknowledged_at=at + dt.timedelta(minutes=9),
                acknowledged_by=self.admin,
            )


def seed():
    Seeder().run()
