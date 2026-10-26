# SPDX-License-Identifier: EUPL-1.2
"""v1.1 · Datos de demostración do rexistro de limpeza (todos ficticios).

Execútase ao final de `seed_demo`, despois da v5, cun xerador aleatorio propio:
- Noela, persoal de limpeza de Vilardeiras dunha empresa contratada ficticia;
- plan de limpeza do pavillón municipal (pista, vestiarios, aseos, bancadas e almacén) e dos
  vestiarios do campo de Outeiro, cos seus QR;
- rexistros das últimas tres semanas (algún checklist incompleto e observacións);
- os aseos do pavillón levan 20 h sen limpar (máximo 16 h) → aviso ao concello;
- unha valoración «Mal · Sucia» recente que xerou unha tarefa para a limpeza.
Pontedouro non ten persoal de limpeza: alí todo segue como ata agora.
"""

import datetime as dt
import io
import random

from django.core.files.base import ContentFile
from django.utils import timezone

from apps.accounts.models import Membership, Role, User
from apps.bookings.models import Booking, Rating
from apps.facilities.models import Facility
from apps.maintenance import cleaning
from apps.maintenance.models import CleaningLog, CleaningZone, Frequency, WorkOrder
from apps.maintenance.services import generate_orders
from apps.tenants.models import Municipality

CLEANER_EMAIL = "noela@demo.eira.example"
COMPANY = "Limpezas Brillo do Val, S. L. (empresa ficticia)"
HALL = "Pavillón municipal de Vilardeiras"
FIELD = "Campo de fútbol de Outeiro"
LATE_ZONE = "Aseos"
DAYS = 21
# Horas das quendas segundo cantas veces ao día se limpa
ROUNDS = {1: [(9, 0)], 2: [(8, 30), (19, 0)], 3: [(8, 30), (13, 30), (19, 30)]}
NOTES = [
    "Repuxen xabón e papel.",
    "Falta papel no aseo adaptado: repuxen o que quedaba no almacén.",
    "Unha billa da ducha 3 pinga. Aviso a mantemento.",
    "Moita area na pista despois do adestramento.",
    "Papeleira da entrada rota (xa avisada).",
]


class Seeder:
    def __init__(self):
        self.rng = random.Random("eira-v1.1")
        self.now = timezone.now()
        self.today = timezone.localdate()
        self.vil = Municipality.objects.get(slug="vilardeiras")
        self.hall = Facility.objects.get(municipality=self.vil, name=HALL)

    def run(self):
        self.person()
        self.plans()
        self.orders()
        self.history()
        self.dirty_rating()
        cleaning.check_overdue(self.vil, now=self.now)

    # ------------------------------------------------------------------
    def person(self):
        self.noela = User.objects.create_user(
            CLEANER_EMAIL, display_name="Noela (limpeza)", birth_year=1983
        )
        Membership.objects.create(
            user=self.noela, municipality=self.vil, role=Role.CLEANING, company=COMPANY
        )
        self.brais = User.objects.get(email="brais@demo.eira.example")

    def plans(self):
        cleaning.apply_template(self.hall, "sports_hall")
        field = Facility.objects.filter(municipality=self.vil, name=FIELD).first()
        if field:
            cleaning.apply_template(field, "grass_field")
            # O campo só ten vestiarios na demo: a bancada queda desactivada
            CleaningZone.objects.filter(facility=field, kind=CleaningZone.Kind.STANDS).update(
                active=False
            )
        start = self.today - dt.timedelta(days=DAYS + 7)
        CleaningZone.objects.filter(municipality=self.vil).update(
            created_at=self.now - dt.timedelta(days=DAYS + 7)
        )
        from apps.maintenance.models import MaintenanceTask

        MaintenanceTask.objects.filter(zone__municipality=self.vil).update(start_date=start)
        self.zones = list(
            CleaningZone.objects.filter(municipality=self.vil, active=True)
            .select_related("facility")
            .prefetch_related("tasks")
        )

    def orders(self):
        generate_orders(
            days=DAYS, today=self.today - dt.timedelta(days=DAYS), municipality=self.vil
        )
        generate_orders(days=14, today=self.today, municipality=self.vil)

    # ------------------------------------------------------------------
    def _times(self, zone, day):
        task = zone.tasks.first()
        if task is None or not task.occurs_on(day):
            return []
        times = task.occurrences_per_day if task.frequency == Frequency.SEVERAL else 1
        if task.frequency == Frequency.WEEKLY:
            return [(0, (11, 0))]
        return list(enumerate(ROUNDS.get(times, ROUNDS[1])))

    def history(self):
        late_since = self.now - dt.timedelta(hours=20)  # máis que as 16 h dos aseos
        photo_left = 3
        for back in range(DAYS, -1, -1):
            day = self.today - dt.timedelta(days=back)
            for zone in self.zones:
                for slot, (h, m) in self._times(zone, day):
                    at = timezone.make_aware(
                        dt.datetime.combine(day, dt.time(h, m))
                        + dt.timedelta(minutes=self.rng.randint(-10, 25))
                    )
                    if at > self.now - dt.timedelta(minutes=30):
                        continue  # aínda non tocaba
                    if zone.name == LATE_ZONE and zone.facility == self.hall and at > late_since:
                        continue  # a zona atrasada da demo
                    order = (
                        WorkOrder.objects.filter(zone=zone, due_date=day, slot=slot)
                        .exclude(status=WorkOrder.Status.DONE)
                        .first()
                    )
                    photo = photo_left > 0 and self.rng.random() < 0.05
                    photo_left -= photo
                    self._log(zone, at, order, photo=photo)

    def _log(self, zone, at, order, photo=False):
        items = zone.checklist_items()
        done = list(items)
        if self.rng.random() < 0.08:
            done.remove(self.rng.choice(items))  # checklist incompleto (control da empresa)
        notes = self.rng.choice(NOTES) if self.rng.random() < 0.06 else ""
        # Os domingos cobre Brais (mantemento) os vestiarios: tamén queda rexistrado
        user = self.brais if at.weekday() == 6 and zone.kind == "changing" else self.noela
        log = CleaningLog.objects.create(
            municipality=self.vil,
            facility=zone.facility,
            zone=zone,
            user=user,
            by_name=str(user),
            company=COMPANY if user == self.noela else "",
            done_at=at,
            items=[{"label": i, "done": i in done} for i in items],
            notes=notes,
            order=order,
            source=(
                CleaningLog.Source.ORDER
                if order is not None and self.rng.random() < 0.2
                else CleaningLog.Source.QR
            ),
        )
        if photo:
            log.photo.save(f"limpeza-{log.pk}.jpg", ContentFile(_photo(self.rng)), save=True)
        if order is not None:
            WorkOrder.objects.filter(pk=order.pk).update(
                status=WorkOrder.Status.DONE,
                closed_at=at,
                closing_notes=notes,
                checklist_state=[{"label": i, "done": i in done} for i in items],
            )

    def dirty_rating(self):
        """Valoración «Mal · Sucia» recente no pavillón → incidencia de limpeza e tarefa para Noela."""
        from apps.bookings.ratings import save_rating
        from apps.incidents.models import Incident

        b = (
            Booking.objects.filter(
                facility=self.hall,
                status=Booking.Status.USED,
                end__gte=self.now - dt.timedelta(days=4),
                end__lte=self.now,
                user__isnull=False,
            )
            .exclude(pk__in=Rating.objects.values("booking_id"))
            .order_by("-end")
            .first()
        )
        if b is None:
            return
        rating = save_rating(
            b,
            "bad",
            ["dirty"],
            "O vestiario 2 tiña o chan moi sucio e as papeleiras cheas.",
            create_incident=True,
        )
        if rating.incident:
            Incident.objects.filter(pk=rating.incident.pk).update(created_at=b.end)


def _photo(rng):
    """Foto ficticia (unha cor lisa con textura) para algúns rexistros."""
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (480, 360), (205, 222, 214))
    d = ImageDraw.Draw(im)
    for _i in range(40):
        x, y = rng.randint(0, 470), rng.randint(0, 350)
        d.rectangle([x, y, x + rng.randint(8, 40), y + 6], fill=(180, 200, 192))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70)
    return buf.getvalue()


def seed():
    Seeder().run()
