# SPDX-License-Identifier: EUPL-1.2
"""Inicio da app da veciñanza: a próxima reserva co seu acceso, avisos e atallos."""

from django.shortcuts import render
from django.utils import timezone

from apps.access.services import booking_access_info
from apps.bookings.models import Booking
from apps.notifications.models import Notification

from .urlutils import neighbour_required


@neighbour_required
def home(request):
    now = timezone.now()
    # v5: tamén as reservas nos concellos próximos da rede (cada unha co seu concello)
    from django.db.models import Q

    towns = Q(municipality=request.tenant)
    if request.tenant.region_id:
        towns |= Q(municipality__region_id=request.tenant.region_id)
    mine = Booking.objects.filter(towns, user=request.user).select_related(
        "facility", "municipality"
    )
    upcoming = list(
        mine.filter(
            end__gt=now,
            status__in=[
                Booking.Status.CONFIRMED,
                Booking.Status.PENDING_PAYMENT,
                Booking.Status.USED,
                Booking.Status.PENDING_APPROVAL,
                Booking.Status.PENDING_OFFICE,
            ],
        ).order_by("start")[:4]
    )
    nxt = upcoming[0] if upcoming else None
    pending_checklist = [
        b
        for b in mine.filter(
            start__lte=now,
            closed_at__isnull=True,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.USED],
        )
        if b.needs_closing_checklist
    ]
    household = getattr(request.user, "household", None)
    from apps.bookings.views import weather_for

    forecast = weather_for(nxt.facility, nxt.start)[0] if nxt else None
    health = getattr(request.user, "health_profile", None)
    return render(
        request,
        "app/home.html",
        {
            "next_booking": nxt,
            "forecast": forecast,
            "now": now,
            "account_health": health.as_dict() if health else None,
            "access": booking_access_info(nxt) if nxt else None,
            "upcoming": upcoming[1:],
            "pending_checklist": pending_checklist,
            "notifications": Notification.objects.filter(
                user=request.user, municipality=request.tenant
            )[:3],
            "dependents": list(household.dependents.all()) if household else [],
            "is_resident": request.user.is_resident(request.tenant),
            "nearby": request.tenant.region_id is not None,
            "nav": "app_home",
        },
    )
