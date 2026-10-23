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
from .models import Booking, Payment
from .payments import record_counter_payment, refund_payment

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
    payment = forms.ChoiceField(
        label=gettext_lazy("Cobro"),
        choices=[
            ("pending", gettext_lazy("Pendente: pagará despois")),
            ("cash", gettext_lazy("Cobrado en efectivo")),
            ("card_terminal", gettext_lazy("Cobrado con tarxeta no TPV físico")),
        ],
        widget=forms.RadioSelect,
        initial="pending",
    )
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
                if d["payment"] in ("cash", "card_terminal"):
                    record_counter_payment(booking, d["payment"], request.user)
                else:
                    # Reserva feita polo persoal: a franxa gárdase ata a hora de uso para cobrar despois
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


class CounterPaymentForm(forms.Form):
    method = forms.ChoiceField(
        label=gettext_lazy("Método"),
        choices=[
            ("cash", gettext_lazy("Efectivo")),
            ("card_terminal", gettext_lazy("Tarxeta no TPV físico")),
        ],
        widget=forms.RadioSelect,
        initial="cash",
    )


@role_required(*ADMIN_ROLES)
def booking_detail(request, pk):
    """Ficha da reserva para o persoal: estado, cobros, acceso e accións (cobrar, cancelar)."""
    booking = get_object_or_404(
        Booking.objects.select_related("facility", "user", "rules_version", "created_by"),
        municipality=request.tenant,
        pk=pk,
    )
    form = CounterPaymentForm(request.POST or None)
    if request.method == "POST" and request.POST.get("action") == "counter_pay" and form.is_valid():
        if booking.status != Booking.Status.PENDING_PAYMENT:
            messages.error(request, _("Esta reserva non está pendente de pagamento."))
        else:
            record_counter_payment(booking, form.cleaned_data["method"], request.user)
            messages.success(request, _("Cobro rexistrado. A reserva está pagada e confirmada."))
        return redirect(treverse(request.tenant, "manage:booking", booking.pk))
    return render(
        request,
        "manage/booking.html",
        {
            "booking": booking,
            "payments": booking.payments.all(),
            "form": form,
            "nav": "manage",
            "sub": "agenda",
        },
    )


def _payments_queryset(request):
    qs = Payment.objects.for_tenant(request.tenant).select_related(
        "booking__facility", "enrollment__group"
    )
    g = request.GET
    try:
        if g.get("desde"):
            qs = qs.filter(created_at__date__gte=dt.date.fromisoformat(g["desde"]))
        if g.get("ata"):
            qs = qs.filter(created_at__date__lte=dt.date.fromisoformat(g["ata"]))
    except ValueError:
        pass
    if g.get("estado") in Payment.Status.values:
        qs = qs.filter(status=g["estado"])
    if g.get("metodo") in Payment.Method.values:
        qs = qs.filter(method=g["metodo"])
    if g.get("instalacion", "").isdigit():
        qs = qs.filter(booking__facility_id=int(g["instalacion"]))
    return qs


@role_required(*ADMIN_ROLES)
def payments_list(request):
    """Cobros e conciliación para Intervención/Tesourería."""
    qs = _payments_queryset(request)
    fmt = request.GET.get("exportar")
    if fmt in ("csv", "ods"):
        header = [
            "data",
            "referencia",
            "concepto",
            "instalacion",
            "metodo",
            "estado",
            "importe_eur",
            "devolto_eur",
            "neto_eur",
            "rexistrado_por",
        ]
        rows = [
            [
                timezone.localtime(p.created_at).strftime("%Y-%m-%d %H:%M"),
                p.reference,
                p.concept,
                p.booking.facility.name
                if p.booking
                else (str(p.enrollment.group) if p.enrollment else ""),
                p.get_method_display(),
                p.get_status_display(),
                p.amount_cents / 100,
                p.refunded_cents / 100,
                p.net_cents / 100,
                "persoal" if p.recorded_by_id else "pasarela",
            ]
            for p in qs
        ]
        from apps.analytics.views import _csv

        return _csv("cobros.csv", header, rows, ods=(fmt == "ods"))
    totals = {
        "paid": sum(
            p.amount_cents
            for p in qs
            if p.status
            in (Payment.Status.PAID, Payment.Status.REFUNDED, Payment.Status.PARTIALLY_REFUNDED)
        ),
        "refunded": sum(p.refunded_cents for p in qs),
        "pending": sum(p.amount_cents for p in qs if p.status == Payment.Status.PENDING),
        "rejected": sum(1 for p in qs if p.status == Payment.Status.REJECTED),
    }
    totals["net"] = totals["paid"] - totals["refunded"]
    return render(
        request,
        "manage/payments.html",
        {
            "payments": qs[:500],
            "totals": totals,
            "statuses": Payment.Status.choices,
            "methods": Payment.Method.choices,
            "facilities": Facility.objects.for_tenant(request.tenant),
            "filters": request.GET,
            "nav": "manage",
            "sub": "payments",
        },
    )


@role_required(*ADMIN_ROLES)
def payment_refund(request, pk):
    payment = get_object_or_404(Payment, municipality=request.tenant, pk=pk)
    if request.method == "POST":
        cents = refund_payment(
            payment, payment.amount_cents - payment.refunded_cents, reason="manual"
        )
        messages.success(
            request, _("Devolución rexistrada: %(e)s €.") % {"e": f"{cents / 100:.2f}"}
        )
    return redirect(treverse(request.tenant, "manage:payments"))
