# SPDX-License-Identifier: EUPL-1.2
import datetime as dt

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST

from apps.access.services import booking_access_info, remote_open
from apps.facilities.models import Facility
from apps.integrations.registry import get_adapter
from apps.integrations.weather import advice
from apps.tenants.urlutils import treverse

from . import ics, services
from .models import Booking


def _parse_start(value):
    start = parse_datetime(value or "")
    if start is None:
        return None
    if timezone.is_naive(start):
        start = timezone.make_aware(start)
    return start


def weather_for(facility, start):
    if not facility.municipality.module_enabled("weather") or facility.latitude is None:
        return None, []
    if start - timezone.now() > dt.timedelta(days=7):
        return None, []
    forecast = get_adapter("weather").forecast(facility.latitude, facility.longitude, start)
    return forecast, advice(forecast, indoor=facility.indoor)


class ConfirmForm(forms.Form):
    accept_rules = forms.BooleanField(
        label=gettext_lazy("Lin e acepto as normas de uso, dereitos e deberes desta instalación."),
        error_messages={"required": gettext_lazy("Para reservar debes aceptar as normas.")},
    )


@login_required
def book(request, pk):
    tenant = request.tenant
    facility = get_object_or_404(Facility, municipality=tenant, pk=pk, is_published=True)
    start = _parse_start(request.GET.get("inicio") or request.POST.get("inicio"))
    if start is None:
        return redirect(treverse(tenant, "facilities:detail", facility.pk))
    rules = facility.current_rules()
    audience, price = services.price_for(facility, request.user)
    form = ConfirmForm(request.POST or None)
    error = None
    if request.method == "POST" and form.is_valid():
        try:
            booking = services.create_booking(facility, start, request.user, rules_version=rules)
        except services.BookingError as exc:
            error = str(exc)
        else:
            if booking.status == Booking.Status.PENDING_PAYMENT:
                return_url = treverse(tenant, "bookings:payment_return", booking.pk)
                ref, url = get_adapter("payment").create(
                    booking.price_cents, f"{facility.name} {booking.reference}", return_url
                )
                booking.payment_reference = ref
                booking.save(update_fields=["payment_reference"])
                return redirect(url)
            messages.success(request, _("Reserva confirmada."))
            return redirect(treverse(tenant, "bookings:detail", booking.pk))
    forecast, tips = weather_for(facility, start)
    return render(
        request,
        "bookings/confirm.html",
        {
            "facility": facility,
            "start": start,
            "end": start + dt.timedelta(minutes=facility.slot_minutes),
            "rules": rules,
            "price": price,
            "audience": audience,
            "form": form,
            "error": error,
            "nav": "facilities",
            "forecast": forecast,
            "tips": tips,
            "audience_label": dict(facility.tariffs.model.Audience.choices).get(audience, ""),
        },
    )


@login_required
def payment_return(request, pk):
    booking = get_object_or_404(Booking, municipality=request.tenant, pk=pk, user=request.user)
    status = (
        get_adapter("payment").status(booking.payment_reference)
        if booking.payment_reference
        else None
    )
    if status and status.paid:
        services.mark_paid(booking, status.reference, status.amount_cents)
        messages.success(request, _("Pagamento recibido. Reserva confirmada."))
    elif booking.status == Booking.Status.PENDING_PAYMENT:
        messages.error(
            request, _("O pagamento non se completou. A franxa queda gardada uns minutos.")
        )
    return redirect(treverse(request.tenant, "bookings:detail", booking.pk))


@login_required
def retry_payment(request, pk):
    booking = get_object_or_404(
        Booking,
        municipality=request.tenant,
        pk=pk,
        user=request.user,
        status=Booking.Status.PENDING_PAYMENT,
    )
    return_url = treverse(request.tenant, "bookings:payment_return", booking.pk)
    ref, url = get_adapter("payment").create(
        booking.price_cents, f"{booking.facility.name} {booking.reference}", return_url
    )
    booking.payment_reference = ref
    booking.save(update_fields=["payment_reference"])
    return redirect(url)


@login_required
def mine(request):
    qs = (
        Booking.objects.for_tenant(request.tenant)
        .filter(user=request.user)
        .select_related("facility")
    )
    now = timezone.now()
    upcoming = qs.filter(
        end__gt=now,
        status__in=[Booking.Status.CONFIRMED, Booking.Status.PENDING_PAYMENT, Booking.Status.USED],
    ).order_by("start")
    history = qs.exclude(pk__in=upcoming.values("pk")).order_by("-start")[:50]
    pending_checklist = [
        b
        for b in qs.filter(
            start__lte=now,
            closed_at__isnull=True,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.USED],
        )
        if b.needs_closing_checklist
    ]
    return render(
        request,
        "bookings/mine.html",
        {
            "upcoming": upcoming,
            "history": history,
            "pending_checklist": pending_checklist,
            "nav": "bookings",
        },
    )


def _own_booking(request, pk):
    return get_object_or_404(
        Booking.objects.select_related("facility", "rules_version", "municipality"),
        municipality=request.tenant,
        pk=pk,
        user=request.user,
    )


@login_required
def detail(request, pk):
    booking = _own_booking(request, pk)
    url = request.build_absolute_uri(treverse(request.tenant, "bookings:detail", booking.pk))
    forecast, tips = (
        weather_for(booking.facility, booking.start) if booking.end > timezone.now() else (None, [])
    )
    return render(
        request,
        "bookings/detail.html",
        {
            "booking": booking,
            "access": booking_access_info(booking),
            "nav": "bookings",
            "gcal_url": ics.google_calendar_url(booking, url),
            "forecast": forecast,
            "tips": tips,
            "penalty": booking.penalty_if_cancelled_now(),
        },
    )


@login_required
def cancel(request, pk):
    booking = _own_booking(request, pk)
    if not booking.can_cancel():
        messages.error(request, _("Esta reserva xa non se pode cancelar."))
        return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    if request.method == "POST":
        try:
            refund, penalty = services.cancel_booking(
                booking, by=request.user, reason=request.POST.get("reason", "")
            )
        except services.BookingError as exc:
            messages.error(request, str(exc))
        else:
            msg = _("Reserva cancelada.")
            if refund:
                msg += " " + _("Devolverémosche %(r)s €.") % {
                    "r": f"{refund / 100:.2f}".replace(".", ",")
                }
            messages.success(request, msg)
        return redirect(treverse(request.tenant, "bookings:mine"))
    return render(
        request,
        "bookings/cancel.html",
        {
            "booking": booking,
            "penalty": booking.penalty_if_cancelled_now(),
            "nav": "bookings",
        },
    )


@login_required
def modify(request, pk):
    booking = _own_booking(request, pk)
    if not booking.can_modify():
        messages.error(request, _("Xa non se pode modificar esta reserva (prazo superado)."))
        return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    start = _parse_start(request.POST.get("inicio") or request.GET.get("inicio"))
    if request.method == "POST" and start:
        try:
            services.modify_booking(booking, start, by=request.user)
        except services.BookingError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, _("Reserva cambiada."))
            return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    from apps.facilities.views import _monday

    today = timezone.localdate()
    try:
        week = dt.date.fromisoformat(request.GET.get("semana", ""))
    except ValueError:
        week = timezone.localdate(booking.start)
    monday = _monday(max(week, _monday(today)))
    grid = services.week_grid(booking.facility, monday, request.user)
    return render(
        request,
        "bookings/modify.html",
        {
            "booking": booking,
            "grid": grid,
            "facility": booking.facility,
            "start": start,
            "monday": monday,
            "prev_week": monday - dt.timedelta(days=7) if monday > _monday(today) else None,
            "next_week": monday + dt.timedelta(days=7),
            "nav": "bookings",
            "modify_mode": True,
        },
    )


@login_required
def receipt(request, pk):
    booking = _own_booking(request, pk)
    if booking.paid_cents == 0 and booking.price_cents > 0:
        raise Http404
    return render(request, "bookings/receipt.html", {"booking": booking, "nav": "bookings"})


@login_required
def ics_one(request, pk):
    booking = _own_booking(request, pk)
    url = request.build_absolute_uri(treverse(request.tenant, "bookings:detail", booking.pk))
    body = ics.calendar([booking], url_for=lambda b: url, name=booking.facility.name)
    response = HttpResponse(body, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="reserva-{booking.reference}.ics"'
    return response


@login_required
def ics_all(request):
    qs = (
        Booking.objects.for_tenant(request.tenant)
        .filter(
            user=request.user,
            end__gt=timezone.now(),
            status__in=[Booking.Status.CONFIRMED, Booking.Status.USED],
        )
        .select_related("facility", "municipality")
    )
    body = ics.calendar(
        qs,
        url_for=lambda b: request.build_absolute_uri(
            treverse(request.tenant, "bookings:detail", b.pk)
        ),
        name=f"Eira · {request.tenant.name}",
    )
    response = HttpResponse(body, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="as-minas-reservas.ics"'
    return response


class ChecklistForm(forms.Form):
    YES_NO = [("1", gettext_lazy("Si")), ("0", gettext_lazy("Non"))]
    door_ok = forms.ChoiceField(
        label=gettext_lazy("Deixaches a porta pechada?"), choices=YES_NO, widget=forms.RadioSelect
    )
    key_ok = forms.ChoiceField(
        label=gettext_lazy("Devolviches a chave?"),
        choices=YES_NO,
        widget=forms.RadioSelect,
        required=False,
    )
    all_ok = forms.ChoiceField(
        label=gettext_lazy("Quedou todo en orde (luces, material, limpeza)?"),
        choices=YES_NO,
        widget=forms.RadioSelect,
    )
    notes = forms.CharField(
        label=gettext_lazy("Algo que contar? (opcional)"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, needs_key=False, **kwargs):
        super().__init__(*args, **kwargs)
        if needs_key:
            self.fields["key_ok"].required = True
        else:
            del self.fields["key_ok"]


@login_required
def checklist(request, pk):
    booking = _own_booking(request, pk)
    if booking.closed_at:
        messages.info(request, _("Xa enviaches o checklist de peche desta reserva."))
        return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    needs_key = booking.facility.access_level == 1
    form = ChecklistForm(request.POST or None, needs_key=needs_key)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        incident = services.submit_closing_checklist(
            booking,
            d["door_ok"] == "1",
            (d["key_ok"] == "1") if needs_key else None,
            d["all_ok"] == "1",
            d.get("notes", ""),
            by=request.user,
        )
        if incident:
            messages.warning(
                request,
                _("Grazas. Creamos a incidencia #%(n)s para que o concello o revise.")
                % {"n": incident.pk},
            )
        else:
            messages.success(request, _("Grazas! Instalación pechada correctamente."))
        return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    return render(
        request, "bookings/checklist.html", {"booking": booking, "form": form, "nav": "bookings"}
    )


@login_required
@require_POST
def open_lock(request, pk):
    booking = _own_booking(request, pk)
    if booking.facility.access_level != 3 or not remote_open(booking, request.user):
        messages.error(
            request, _("Agora non se pode abrir. A porta ábrese desde 10 minutos antes do inicio.")
        )
    else:
        messages.success(request, _("Porta aberta. Ben adestramento!"))
    if request.headers.get("HX-Request"):
        return render(
            request,
            "bookings/_access.html",
            {"booking": booking, "access": booking_access_info(booking), "just_opened": True},
        )
    return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
