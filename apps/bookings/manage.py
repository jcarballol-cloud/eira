# SPDX-License-Identifier: EUPL-1.2
"""Panel do día, axenda e reserva en nome dunha persoa (teléfono ou mostrador)."""

import datetime as dt

from django import forms
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.access import services as access
from apps.accounts.models import User
from apps.facilities.models import AccessLevel, Facility
from apps.incidents.models import Incident
from apps.integrations.registry import get_adapter
from apps.integrations.weather import advice
from apps.maintenance.models import WorkOrder
from apps.tenants.urlutils import role_required, treverse

from . import services
from .models import Booking

ADMIN_ROLES = ("admin", "region_admin")


@role_required(*ADMIN_ROLES)
def dashboard(request):
    tenant = request.tenant
    today = timezone.localdate()
    start = timezone.make_aware(dt.datetime.combine(today, dt.time.min))
    end = start + dt.timedelta(days=1)
    bookings = list(
        Booking.objects.for_tenant(tenant)
        .filter(start__gte=start, start__lt=end)
        .exclude(status=Booking.Status.CANCELLED)
        .select_related("facility", "user")
        .order_by("start")
    )
    facilities = list(
        Facility.objects.for_tenant(tenant)
        .filter(is_published=True)
        .prefetch_related("opening_hours")
    )
    capacity_slots = sum(len(services.slot_starts(f, today)) * f.capacity for f in facilities)
    held = sum(
        1
        for b in bookings
        if b.status in (Booking.Status.CONFIRMED, Booking.Status.USED, Booking.Status.NO_SHOW)
    )
    revenue = (
        Booking.objects.for_tenant(tenant)
        .filter(created_at__date=today)
        .aggregate(s=Sum("paid_cents"))["s"]
        or 0
    )
    incidents_new = (
        Incident.objects.for_tenant(tenant)
        .filter(status=Incident.Status.RECEIVED)
        .select_related("facility")[:8]
    )
    orders_today = (
        WorkOrder.objects.for_tenant(tenant)
        .filter(due_date__lte=today)
        .exclude(status=WorkOrder.Status.DONE)
        .select_related("facility", "assigned_to")[:10]
    )
    key_bookings = [b for b in bookings if b.facility.access_level == AccessLevel.CUSTODIAN]
    forecast = tips = None
    first = next((f for f in facilities if f.latitude is not None), None)
    if first and tenant.module_enabled("weather"):
        forecast = get_adapter("weather").forecast(
            first.latitude, first.longitude, timezone.now().replace(hour=18)
        )
        tips = advice(forecast)
    return render(
        request,
        "manage/dashboard.html",
        {
            "today": today,
            "bookings": bookings,
            "occupancy": round(100 * held / capacity_slots) if capacity_slots else 0,
            "held": held,
            "revenue": revenue,
            "incidents_new": incidents_new,
            "orders_today": orders_today,
            "key_bookings": key_bookings,
            "forecast": forecast,
            "tips": tips,
            "nav": "manage",
            "sub": "dashboard",
            "now": timezone.now(),
        },
    )


@role_required(*ADMIN_ROLES)
def agenda(request):
    tenant = request.tenant
    try:
        day = dt.date.fromisoformat(request.GET.get("dia", ""))
    except ValueError:
        day = timezone.localdate()
    start = timezone.make_aware(dt.datetime.combine(day, dt.time.min))
    bookings = (
        Booking.objects.for_tenant(tenant)
        .filter(start__gte=start, start__lt=start + dt.timedelta(days=1))
        .select_related("facility", "user")
        .order_by("facility__name", "start")
    )
    return render(
        request,
        "manage/agenda.html",
        {
            "day": day,
            "bookings": bookings,
            "prev": day - dt.timedelta(days=1),
            "next": day + dt.timedelta(days=1),
            "nav": "manage",
            "sub": "agenda",
        },
    )


class OnBehalfForm(forms.Form):
    holder_name = forms.CharField(label=gettext_lazy("Nome da persoa"), max_length=120)
    holder_phone = forms.CharField(
        label=gettext_lazy("Teléfono"),
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "off"}),
    )
    email = forms.EmailField(
        label=gettext_lazy("Correo (se ten conta)"),
        required=False,
        help_text=gettext_lazy(
            "Se o indicas, a reserva aparecerá no seu historial e recibirá avisos."
        ),
    )
    channel = forms.ChoiceField(
        label=gettext_lazy("Canle"),
        choices=[("phone", gettext_lazy("Teléfono")), ("counter", gettext_lazy("Mostrador"))],
        widget=forms.RadioSelect,
        initial="phone",
    )
    paid_at_counter = forms.BooleanField(label=gettext_lazy("Cobrado no mostrador"), required=False)
    rules_read = forms.BooleanField(label=gettext_lazy("Lin as normas á persoa e acéptaas"))


@role_required(*ADMIN_ROLES)
def on_behalf(request):
    tenant = request.tenant
    facilities = Facility.objects.for_tenant(tenant).filter(is_published=True)
    facility = facilities.filter(
        pk=request.GET.get("instalacion") or request.POST.get("instalacion")
    ).first()
    start = None
    if facility and (request.GET.get("inicio") or request.POST.get("inicio")):
        from .views import _parse_start

        start = _parse_start(request.GET.get("inicio") or request.POST.get("inicio"))
    form = OnBehalfForm(request.POST or None) if start else None
    if request.method == "POST" and form is not None and form.is_valid():
        d = form.cleaned_data
        user = User.objects.filter(email=d["email"].lower()).first() if d["email"] else None
        try:
            booking = services.create_booking(
                facility,
                start,
                user,
                rules_version=facility.current_rules(),
                channel=d["channel"],
                created_by=request.user,
                holder_name=d["holder_name"],
                holder_phone=d["holder_phone"],
            )
            if booking.status == Booking.Status.PENDING_PAYMENT:
                if d["paid_at_counter"]:
                    services.mark_paid(
                        booking, f"MOSTRADOR-{booking.reference}", booking.price_cents
                    )
                else:
                    booking.hold_expires_at = booking.start
                    booking.save(update_fields=["hold_expires_at"])
        except services.BookingError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                _("Reserva %(r)s feita para %(n)s.")
                % {"r": booking.reference, "n": d["holder_name"]},
            )
            return redirect(treverse(tenant, "manage:dashboard"))
    grid = monday = None
    if facility and not start:
        from apps.facilities.views import _monday

        try:
            week = dt.date.fromisoformat(request.GET.get("semana", ""))
        except ValueError:
            week = timezone.localdate()
        monday = _monday(max(week, _monday(timezone.localdate())))
        grid = services.week_grid(facility, monday)
    price = services.price_for(facility, None)[1] if facility else None
    return render(
        request,
        "manage/on_behalf.html",
        {
            "facilities": facilities,
            "facility": facility,
            "start": start,
            "form": form,
            "grid": grid,
            "monday": monday,
            "prev_week": monday - dt.timedelta(days=7)
            if monday and monday > timezone.localdate() - dt.timedelta(days=7)
            else None,
            "next_week": monday + dt.timedelta(days=7) if monday else None,
            "price": price,
            "facility_param": f"&instalacion={facility.pk}" if facility else "",
            "nav": "manage",
            "sub": "on_behalf",
            "staff_mode": True,
        },
    )


@role_required(*ADMIN_ROLES, "maintenance")
def key_action(request, pk, action):
    booking = get_object_or_404(Booking, municipality=request.tenant, pk=pk)
    if request.method == "POST":
        if action == "out":
            access.key_out(booking, request.user)
            messages.success(request, _("Chave entregada a %(n)s.") % {"n": booking.holder_label})
        elif action == "in":
            access.key_in(booking, request.user)
            messages.success(request, _("Chave devolta."))
    return redirect(request.POST.get("next") or treverse(request.tenant, "manage:dashboard"))


@role_required(*ADMIN_ROLES)
def staff_cancel(request, pk):
    booking = get_object_or_404(Booking, municipality=request.tenant, pk=pk)
    if request.method == "POST":
        try:
            services.cancel_booking(
                booking,
                by=request.user,
                reason=request.POST.get("reason", _("Cancelada polo concello")),
                force_full_refund=True,
            )
            messages.success(request, _("Reserva cancelada e reembolsada."))
        except services.BookingError as exc:
            messages.error(request, str(exc))
    return redirect(treverse(request.tenant, "manage:agenda"))
