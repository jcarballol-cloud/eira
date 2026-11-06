# SPDX-License-Identifier: EUPL-1.2
"""v1.5.1: reservas de apoio para que os exemplos da demo existan sempre.

A demo reparte as reservas ao chou e iso depende da data e da hora do seed. Cando un exemplo precisa
unha reserva concreta e o azar non a deixou, créase aquí nunha franxa libre."""

import datetime as dt

from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import slot_starts

INACTIVE = (Booking.Status.CANCELLED, Booking.Status.EXPIRED)


def free_slot(facility, days, now=None):
    """Primeira franxa sen ningunha reserva activa nos `days` indicados (desprazamento desde hoxe).

    Respecta o sentido do tempo: nos días pasados, só franxas xa rematadas; nos futuros, por vir."""
    now = now or timezone.now()
    today = timezone.localdate(now)
    for offset in days:
        for start in slot_starts(facility, today + dt.timedelta(days=offset)):
            end = start + dt.timedelta(minutes=facility.slot_minutes)
            if (offset < 0 and end > now) or (offset >= 0 and start <= now):
                continue
            busy = Booking.objects.filter(facility=facility, start__lt=end, end__gt=start).exclude(
                status__in=INACTIVE
            )
            if not busy.exists():
                return start
    raise RuntimeError(f"Demo: sen franxas libres en {facility} ({list(days)})")


def demo_booking(facility, user, days, status, now=None):
    """Reserva ficticia nunha franxa libre. Nunca devolve None: o exemplo ten que existir."""
    start = free_slot(facility, days, now)
    used = status == Booking.Status.USED
    return Booking.objects.create(
        municipality=facility.municipality,
        facility=facility,
        user=user,
        start=start,
        end=start + dt.timedelta(minutes=facility.slot_minutes),
        status=status,
        tariff_audience="resident",
        price_cents=0,
        base_price_cents=0,
        checked_in_at=start if used else None,
        rules_version=facility.current_rules(),
        rules_accepted_at=start - dt.timedelta(days=1),
    )
