# SPDX-License-Identifier: EUPL-1.2
"""Recomendación horaria: ocupación prevista por (día da semana, hora) a partir do histórico."""

import datetime as dt
from collections import Counter

from django.core.cache import cache
from django.utils import timezone

HISTORY_WEEKS = 8


def expected_occupancy(facility, weeks=HISTORY_WEEKS):
    """Devolve {(weekday, hour): fracción media de prazas ocupadas} nas últimas `weeks` semanas.

    Só se calculan as franxas onde a instalación abre. Cachéase uns minutos.
    """
    from apps.bookings.models import Booking

    key = f"eira:expected:{facility.pk}:{timezone.localdate()}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    since = timezone.now() - dt.timedelta(weeks=weeks)
    counts = Counter()
    for start in Booking.objects.filter(
        facility=facility, start__gte=since, start__lt=timezone.now(),
        status__in=[Booking.Status.CONFIRMED, Booking.Status.USED, Booking.Status.NO_SHOW],
    ).values_list("start", flat=True):
        local = timezone.localtime(start)
        counts[(local.weekday(), local.hour)] += 1
    result = {}
    for h in facility.opening_hours.all():
        t = dt.datetime.combine(dt.date.today(), h.opens)
        end = dt.datetime.combine(dt.date.today(), h.closes)
        while t < end:
            k = (h.weekday, t.hour)
            result[k] = counts.get(k, 0) / (weeks * facility.capacity)
            t += dt.timedelta(minutes=facility.slot_minutes)
    # Sen histórico suficiente non se recomenda nada (evita recomendar todo ao inicio)
    if sum(counts.values()) < 10:
        result = {k: 1 for k in result}
    cache.set(key, result, 600)
    return result


def recommended_hours(facility, limit=5):
    expected = expected_occupancy(facility)
    return sorted((v, k) for k, v in expected.items() if v < 0.3)[:limit]
