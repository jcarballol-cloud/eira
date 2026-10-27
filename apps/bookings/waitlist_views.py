# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · F: «Confirmo» / «Cancelo» dun toque e lista de espera nas reservas."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.facilities.models import Facility
from apps.tenants.urlutils import neighbour_required, treverse

from . import services, waitlist
from .models import Booking, WaitlistEntry
from .views import _go_to_gateway, _own_booking, _parse_start


@neighbour_required
@require_POST
def confirm(request, pk):
    booking = _own_booking(request, pk)
    try:
        waitlist.confirm_attendance(booking, by=request.user)
    except waitlist.WaitlistError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, _("Grazas! Asistencia confirmada."))
    return redirect(treverse(request.tenant, "bookings:detail", booking.pk))


@neighbour_required
@require_POST
def quick_cancel(request, pk):
    """«Cancelo»: un toque. A penalización (se a hai) xa se mostra ao lado do botón."""
    booking = _own_booking(request, pk)
    if not booking.can_cancel():
        messages.error(request, _("Esta reserva xa non se pode cancelar."))
        return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    try:
        refund, _penalty = services.cancel_booking(
            booking, by=request.user, reason=_("Cancelada desde o recordatorio.")
        )
    except services.BookingError as exc:
        messages.error(request, str(exc))
        return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    msg = _("Reserva cancelada. Grazas por avisar: a franxa queda para outra persoa.")
    if refund:
        msg += " " + _("Devolverémosche %(r)s €.") % {"r": f"{refund / 100:.2f}".replace(".", ",")}
    messages.success(request, msg)
    return redirect(treverse(request.tenant, "bookings:mine"))


@neighbour_required
def join(request, facility_pk):
    facility = get_object_or_404(
        Facility, municipality=request.tenant, pk=facility_pk, is_published=True
    )
    start = _parse_start(request.GET.get("inicio") or request.POST.get("inicio"))
    if start is None:
        return redirect(treverse(request.tenant, "facilities:detail", facility.pk))
    if request.method == "POST":
        try:
            waitlist.join(facility, start, request.user)
        except waitlist.WaitlistError as exc:
            messages.error(request, str(exc))
            return redirect(treverse(request.tenant, "facilities:detail", facility.pk))
        messages.success(
            request, _("Feito. Se queda libre, avisarémoste e terás un tempo para collela.")
        )
        return redirect(treverse(request.tenant, "bookings:mine") + "#lista-espera")
    ahead = WaitlistEntry.objects.filter(
        facility=facility, start=start, status=WaitlistEntry.Status.WAITING
    ).count()
    return render(
        request,
        "bookings/waitlist_join.html",
        {"facility": facility, "start": start, "ahead": ahead, "nav": "book"},
    )


def _own_entry(request, pk):
    return get_object_or_404(
        WaitlistEntry.objects.select_related("facility", "release"),
        municipality=request.tenant,
        user=request.user,
        pk=pk,
    )


@neighbour_required
def offer(request, pk):
    entry = _own_entry(request, pk)
    if request.method == "POST" and request.POST.get("accion") == "aceptar":
        try:
            booking = waitlist.accept(entry, request.user)
        except waitlist.WaitlistError as exc:
            messages.error(request, str(exc))
            return redirect(treverse(request.tenant, "bookings:waitlist_offer", entry.pk))
        if booking.status == Booking.Status.PENDING_PAYMENT:
            return _go_to_gateway(request, booking)
        messages.success(request, _("É túa! Reserva confirmada."))
        return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    if request.method == "POST" and request.POST.get("accion") == "deixar":
        waitlist.leave(entry, by=request.user)
        messages.success(request, _("Saíches da lista de espera."))
        return redirect(treverse(request.tenant, "bookings:mine"))
    return render(
        request,
        "bookings/waitlist_offer.html",
        {"entry": entry, "now": timezone.now(), "nav": "bookings"},
    )
