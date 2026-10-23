# SPDX-License-Identifier: EUPL-1.2
"""Escolas deportivas de demostración (datos ficticios) e baterías de probas.

As baterías levan só os NOMES das probas de ALPHA-Fitness e Senior Fitness Test, sen baremos.
"""

import datetime as dt

from django.utils import timezone

from apps.accounts.models import Consent, Dependent, Household, Membership, Role, User
from apps.facilities.models import Facility
from apps.tenants.models import Municipality

from .models import (
    Activity,
    Attendance,
    Enrollment,
    FitnessBattery,
    FitnessResult,
    FitnessTest,
    Group,
)
from .services import pseudonym

ALPHA = (
    "ALPHA-Fitness (infancia e adolescencia)",
    "Ruiz et al., Br J Sports Med 2011 · batería ALPHA-Fitness",
    [
        ("Forza de prensión manual", "kg"),
        ("Salto de lonxitude a pés xuntos", "cm"),
        ("Velocidade-axilidade 4×10 m", "s"),
        ("Test de ida e volta de 20 m", "períodos"),
        ("Peso", "kg"),
        ("Talla", "cm"),
        ("Perímetro da cintura", "cm"),
    ],
)
SFT = (
    "Senior Fitness Test",
    "Rikli e Jones, 2001/2013 · Senior Fitness Test",
    [
        ("Levantarse da cadeira en 30 s", "rep."),
        ("Flexión de cóbado en 30 s", "rep."),
        ("Marcha estática 2 minutos", "pasos"),
        ("Flexión do tronco sentado", "cm"),
        ("Xuntar as mans tras as costas", "cm"),
        ("Levantarse, camiñar 2,44 m e volver", "s"),
    ],
)
KIDS = [
    "Noa",
    "Breixo",
    "Lúa",
    "Xián",
    "Antía",
    "Brais",
    "Icía",
    "Roi",
    "Uxía",
    "Iago",
    "Sabela",
    "Martiño",
    "Aldara",
    "Anxo",
    "Olalla",
    "Bieito",
    "Mencía",
    "Paio",
    "Comba",
    "Lois",
    "Iria",
    "Fiz",
    "Xoana",
    "Ramiro",
]


def seed(rng):
    m = Municipality.objects.get(slug="vilardeiras")
    monitor = User.objects.get(email="antia@demo.eira.example")
    hall = Facility.objects.get(municipality=m, kind="sports_hall")
    field = Facility.objects.get(municipality=m, kind="grass_field")
    gym = Facility.objects.get(municipality=m, kind="gym")
    for name, ref, tests in (ALPHA, SFT):
        b = FitnessBattery.objects.create(municipality=m, name=name, reference=ref)
        for i, (tname, unit) in enumerate(tests):
            FitnessTest.objects.create(battery=b, name=tname, unit=unit, order=i)

    football = Activity.objects.create(
        municipality=m,
        name="Escola de fútbol",
        description="Iniciación ao fútbol para nenas e nenos.",
    )
    senior = Activity.objects.create(
        municipality=m,
        name="Ximnasia de mantemento",
        description="Forza, equilibrio e mobilidade para maiores.",
    )
    pilates = Activity.objects.create(
        municipality=m, name="Pilates", description="Grupo de pilates para persoas adultas."
    )
    groups = [
        Group.objects.create(
            municipality=m,
            activity=football,
            name="Benxamín (8–10)",
            facility=field,
            monitor=monitor,
            min_age=8,
            max_age=10,
            places=16,
            fee_cents=1500,
            weekdays="1,3",
            start_time=dt.time(17, 30),
            rpe_scale=Group.RpeScale.OMNI,
        ),
        Group.objects.create(
            municipality=m,
            activity=football,
            name="Alevín (11–12)",
            facility=field,
            monitor=monitor,
            min_age=11,
            max_age=12,
            places=16,
            fee_cents=1500,
            weekdays="1,3",
            start_time=dt.time(18, 30),
            rpe_scale=Group.RpeScale.OMNI,
        ),
        Group.objects.create(
            municipality=m,
            activity=senior,
            name="Maiores mañá",
            facility=hall,
            monitor=monitor,
            min_age=60,
            max_age=110,
            places=20,
            fee_cents=0,
            weekdays="0,2,4",
            start_time=dt.time(10),
            rpe_scale=Group.RpeScale.BORG,
        ),
        Group.objects.create(
            municipality=m,
            activity=pilates,
            name="Adultos tarde",
            facility=gym,
            monitor=monitor,
            min_age=18,
            max_age=110,
            places=12,
            fee_cents=2000,
            weekdays="0,2",
            start_time=dt.time(20),
            rpe_scale=Group.RpeScale.BORG,
        ),
    ]
    today = timezone.localdate()
    parents = list(User.objects.filter(email__startswith="vecinanza")[:12])
    # Menores ficticios en unidades familiares de veciños/as ficticios
    kid_enrollments = {groups[0]: [], groups[1]: []}
    for i, name in enumerate(KIDS):
        parent = parents[i % len(parents)]
        hh, _c = Household.objects.get_or_create(responsible=parent)
        target = groups[0] if i % 2 == 0 else groups[1]
        age = rng.randint(target.min_age, target.max_age)
        d = Dependent.objects.create(household=hh, first_name=name, birth_year=today.year - age)
        Consent.objects.create(dependent=d, kind="data", granted_by=parent)
        if rng.random() < 0.8:
            Consent.objects.create(dependent=d, kind="performance", granted_by=parent)
        kid_enrollments[target].append((parent, d))
    enrollments = []
    for g, members in kid_enrollments.items():
        for parent, d in members:
            enrollments.append(
                Enrollment(
                    municipality=m,
                    group=g,
                    user=parent,
                    dependent=d,
                    status="active",
                    paid_cents=g.fee_cents,
                )
            )
    adults = list(User.objects.filter(email__startswith="vecinanza"))
    seniors = [u for u in adults if u.age and u.age >= 60]
    others = [u for u in adults if u.age and 18 <= u.age < 60]
    extra_seniors = []
    for i in range(max(0, 12 - len(seniors))):
        u = User.objects.create_user(
            f"maior{i:02d}@demo.eira.example",
            display_name=KIDS[i % len(KIDS)] + " (maior)",
            birth_year=today.year - rng.randint(62, 84),
        )
        Membership.objects.create(user=u, municipality=m, role=Role.CITIZEN)
        extra_seniors.append(u)
    for u in seniors + extra_seniors:
        enrollments.append(Enrollment(municipality=m, group=groups[2], user=u, status="active"))
    for u in others[:12]:
        enrollments.append(
            Enrollment(municipality=m, group=groups[3], user=u, status="active", paid_cents=2000)
        )
    Enrollment.objects.bulk_create(enrollments)
    for e in Enrollment.objects.filter(municipality=m):
        e.pseudonym = pseudonym(e.pk)
        e.save(update_fields=["pseudonym"])
    # Unha persoa en lista de espera para que se vexa o fluxo
    if others[12:13]:
        Enrollment.objects.create(
            municipality=m, group=groups[3], user=others[12], status="waitlist", pseudonym=""
        )

    # Seis semanas de sesións pasadas con asistencia e esforzo
    from .models import Session

    for g in groups:
        members = list(g.enrolled().select_related("dependent"))
        for offset in range(42, 0, -1):
            day = today - dt.timedelta(days=offset)
            if day.weekday() not in g.weekday_list():
                continue
            s = Session.objects.create(
                municipality=m,
                group=g,
                date=day,
                start_time=g.start_time,
                duration_minutes=g.duration_minutes,
                closed_at=timezone.now() - dt.timedelta(days=offset),
            )
            rows = []
            for e in members:
                present = rng.random() < 0.82
                allowed = not e.dependent_id or e.dependent.has_consent("performance")
                rpe = None
                if present and allowed:
                    base = 5 if g.rpe_scale == "omni" else 4
                    rpe = max(0, min(10, base + rng.randint(-2, 3)))
                rows.append(
                    Attendance(
                        session=s,
                        enrollment=e,
                        present=present,
                        rpe=rpe,
                        minutes=g.duration_minutes if present else 0,
                    )
                )
            Attendance.objects.bulk_create(rows)
    # Algúns resultados de probas
    alpha = FitnessBattery.objects.get(municipality=m, name__startswith="ALPHA")
    grip = alpha.tests.get(order=0)
    for e in groups[0].enrolled():
        if e.dependent.has_consent("performance"):
            FitnessResult.objects.create(
                enrollment=e,
                test=grip,
                date=today - dt.timedelta(days=20),
                value=round(rng.uniform(10, 18), 1),
                recorded_by=monitor,
            )
