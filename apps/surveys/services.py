# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · E: cálculo do NPS e resultados agregados (sempre con n ≥ 10).

NPS = % promotores (9–10) − % detractores (0–6). As persoas pasivas (7–8) contan no total."""

from django.db.models import Avg, Count, Q
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import audit

from .models import ASPECTS, Survey, SurveyResponse, UseNps

MIN_N = 10


def nps_from_counts(promoters, passives, detractors):
    n = promoters + passives + detractors
    if n < MIN_N:
        return None
    return {
        "n": n,
        "promoters": round(100 * promoters / n),
        "passives": round(100 * passives / n),
        "detractors": round(100 * detractors / n),
        "nps": round(100 * (promoters - detractors) / n),
    }


def nps(scores):
    scores = list(scores)
    return nps_from_counts(
        sum(1 for s in scores if s >= 9),
        sum(1 for s in scores if 7 <= s <= 8),
        sum(1 for s in scores if s <= 6),
    )


def _nps_qs(qs, field="nps"):
    c = qs.aggregate(
        p=Count("pk", filter=Q(**{f"{field}__gte": 9})),
        m=Count("pk", filter=Q(**{f"{field}__gte": 7, f"{field}__lte": 8})),
        d=Count("pk", filter=Q(**{f"{field}__lte": 6})),
    )
    return nps_from_counts(c["p"], c["m"], c["d"])


def results(survey):
    """Resultados agregados dunha enquisa. Nada se mostra con menos de 10 respostas."""
    qs = SurveyResponse.objects.filter(survey=survey)
    n = qs.count()
    out = {
        "n": n,
        "enough": n >= MIN_N,
        "nps": None,
        "aspects": [],
        "facilities": [],
        "comments": [],
    }
    if n < MIN_N:
        return out
    out["nps"] = _nps_qs(qs)
    averages = qs.aggregate(
        **{f"avg_{k}": Avg(k) for k, _label in ASPECTS},
        **{f"n_{k}": Count(k) for k, _label in ASPECTS},
    )
    for key, label in ASPECTS:
        count = averages[f"n_{key}"]
        value = averages[f"avg_{key}"]
        out["aspects"].append(
            {
                "key": key,
                "label": label,
                "n": count,
                "avg": round(value, 1) if (value is not None and count >= MIN_N) else None,
                "pct": round(100 * (value - 1) / 4)
                if (value is not None and count >= MIN_N)
                else 0,
            }
        )
    for row in (
        qs.exclude(facility=None)
        .values("facility", "facility__name")
        .annotate(n=Count("pk"))
        .order_by("facility__name")
    ):
        if row["n"] >= MIN_N:
            out["facilities"].append(
                {"name": row["facility__name"], **_nps_qs(qs.filter(facility=row["facility"]))}
            )
    # Comentarios sen nome nin data, en orde aleatoria estable (non por quen respondeu)
    out["comments"] = list(
        qs.exclude(comment="").order_by("?").values_list("comment", flat=True)[:30]
    )
    return out


def evolution(municipality):
    """NPS de cada enquisa pechada (ou aberta) por ano, só os anos con n ≥ 10."""
    rows = []
    for s in Survey.objects.filter(municipality=municipality).order_by("year"):
        value = _nps_qs(SurveyResponse.objects.filter(survey=s))
        rows.append({"year": s.year, "survey": s, "nps": value})
    return rows


def facility_use_nps(municipality, days=365):
    """NPS despois do uso por instalación (últimos 12 meses), só con n ≥ 10."""
    since = timezone.now() - timezone.timedelta(days=days)
    qs = UseNps.objects.filter(municipality=municipality, created_at__gte=since)
    out = []
    for row in (
        qs.values("facility", "facility__name").annotate(n=Count("pk")).order_by("facility__name")
    ):
        value = _nps_qs(qs.filter(facility=row["facility"]), field="score")
        if value:
            out.append({"name": row["facility__name"], **value})
    return out


def latest_nps(municipality):
    """O NPS da última enquisa con datos suficientes (para o panel e a deputación)."""
    for row in reversed(evolution(municipality)):
        if row["nps"]:
            return row
    return None


def open_survey(municipality, day=None):
    day = day or timezone.localdate()
    return (
        Survey.objects.filter(municipality=municipality, opens_on__lte=day, closes_on__gte=day)
        .order_by("-year")
        .first()
    )


def pending_for(user, municipality):
    """A enquisa aberta que a persoa aínda non respondeu (ou None)."""
    if not (user and user.is_authenticated):
        return None
    survey = open_survey(municipality)
    if survey and not SurveyResponse.objects.filter(survey=survey, user=user).exists():
        return survey
    return None


def announce(survey, by=None):
    """Aviso da enquisa por app, correo e Telegram (segundo as canles de cada persoa)."""
    from apps.accounts.models import Membership, Role, User
    from apps.notifications.services import notify
    from apps.tenants.urlutils import treverse

    m = survey.municipality
    people = (
        User.objects.filter(
            Q(memberships__municipality=m, memberships__role=Role.CITIZEN)
            | Q(residencies__municipality=m, residencies__revoked_at__isnull=True)
        )
        .exclude(
            pk__in=Membership.objects.filter(municipality=m)
            .exclude(role=Role.CITIZEN)
            .values("user_id")
        )
        .distinct()
    )
    url = treverse(m, "surveys:answer")
    count = 0
    for person in people:
        notify(
            person,
            _("Enquisa de satisfacción %(y)s: dinos que tal") % {"y": survey.year},
            _("Son 2 minutos. Responde ata o %(d)s. As respostas son anónimas.")
            % {"d": survey.closes_on.strftime("%d/%m")},
            url=url,
            municipality=m,
            email=True,
            telegram=True,
        )
        count += 1
    survey.announced_at = timezone.now()
    survey.save(update_fields=["announced_at"])
    audit("survey.announce", by, m, survey, people=count)
    return count
