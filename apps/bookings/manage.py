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
    # v5: reservas e cambios para aprobar e pagamentos pendentes na oficina
    from django.db.models import Q

    to_approve = (
        Booking.objects.for_tenant(tenant)
        .filter(
            Q(status=Booking.Status.PENDING_APPROVAL) | Q(requested_start__isnull=False),
            end__gt=timezone.now(),
        )
        .select_related("facility", "user")
        .order_by("start")[:10]
    )
    office = (
        Booking.objects.for_tenant(tenant)
        .filter(status=Booking.Status.PENDING_OFFICE, hold_expires_at__gt=timezone.now())
        .select_related("facility", "user")
        .order_by("hold_expires_at")[:10]
    )
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
            "to_approve": to_approve,
            "office": office,
            "vitality": _vitality(tenant),
            "forecast": forecast,
            "tips": tips,
            "nav": "manage",
            "sub": "dashboard",
            "now": timezone.now(),
        },
    )


def _vitality(tenant):
    """v5 · G: índice de vida activa por instalación (gárdase 10 min en caché)."""
    from django.core.cache import cache

    from apps.analytics.vitality import municipality_indices

    key = f"eira:vitality:{tenant.pk}:{timezone.localdate().isoformat()}"
    rows = cache.get(key)
    if rows is None:
        rows = [
            {
                "pk": i["facility"].pk,
                "name": i["facility"].name,
                "value": i["value"],
                "level": i["level"],
            }
            for i in municipality_indices(tenant)
        ]
        cache.set(key, rows, 600)
    return rows


@role_required(*ADMIN_ROLES)
def agenda(request):
    tenant = request.tenant
    try:
        day = dt.date.fromisoformat(request.GET.get("dia", ""))
    except ValueError:
        day = timezone.localdate()
    view = request.GET.get("vista", "lista")
    if view in ("semana", "mes"):
        return _agenda_calendar(request, day, view)
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


def _agenda_calendar(request, day, view):
    """Axenda en calendario: semana (días × horas) ou mes, con filtro de instalacións e .ics."""
    from django.http import HttpResponse

    from . import calendar

    tenant = request.tenant
    all_facilities = list(Facility.objects.for_tenant(tenant).order_by("name"))
    chosen = {int(x) for x in request.GET.getlist("i") if x.isdigit()}
    facilities = [f for f in all_facilities if f.pk in chosen] or all_facilities
    if view == "semana":
        first = day - dt.timedelta(days=day.weekday())
        days, prev, nxt = 7, first - dt.timedelta(days=7), first + dt.timedelta(days=7)
    else:
        first = day.replace(day=1)
        nxt_month = (first + dt.timedelta(days=32)).replace(day=1)
        days, prev, nxt = (
            (nxt_month - first).days,
            (first - dt.timedelta(days=1)).replace(day=1),
            nxt_month,
        )
    span_start = first - dt.timedelta(days=first.weekday()) if view == "mes" else first
    span_days = days + first.weekday() + 7 if view == "mes" else days
    evts = calendar.events(tenant, facilities, span_start, span_days)
    if request.GET.get("formato") == "ics":
        in_range = [e for e in evts if first <= e["start"].date() < first + dt.timedelta(days=days)]
        resp = HttpResponse(
            calendar.ics(in_range, f"{tenant.name} · Eira"),
            content_type="text/calendar; charset=utf-8",
        )
        resp["Content-Disposition"] = (
            f'attachment; filename="axenda-{tenant.slug}-{first:%Y%m%d}.ics"'
        )
        return resp
    query = "&".join(f"i={f.pk}" for f in facilities) if chosen else ""
    return render(
        request,
        "manage/agenda_calendar.html",
        {
            "view": view,
            "day": day,
            "first": first,
            "prev": prev,
            "next": nxt,
            "facilities": all_facilities,
            "chosen": {f.pk for f in facilities} if chosen else set(),
            "query": query,
            "week": calendar.week_grid(evts, first) if view == "semana" else None,
            "month": calendar.month_grid(evts, first) if view == "mes" else None,
            "states": calendar.STATES,
            "today": timezone.localdate(),
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


@role_required(*ADMIN_ROLES, "maintenance")
def booking_detail(request, pk):
    """Ficha da reserva para o persoal: estado, cobros, acceso e accións (cobrar, aprobar,
    cancelar). O persoal de mantemento vea só para consulta (estado ao entrar e ao saír)."""
    booking = get_object_or_404(
        Booking.objects.select_related(
            "facility", "user", "rules_version", "created_by", "voucher__type", "network_origin"
        ),
        municipality=request.tenant,
        pk=pk,
    )
    can_act = bool(request.roles & {"admin"})
    form = CounterPaymentForm(request.POST or None)
    action = request.POST.get("action") if request.method == "POST" else None
    if action and not can_act:
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied
    if action == "counter_pay" and form.is_valid():
        if booking.status != Booking.Status.PENDING_PAYMENT and not booking.outstanding_cents:
            messages.error(request, _("Esta reserva non está pendente de pagamento."))
        else:
            record_counter_payment(booking, form.cleaned_data["method"], request.user)
            messages.success(request, _("Cobro rexistrado."))
        return redirect(treverse(request.tenant, "manage:booking", booking.pk))
    if action in ("approve", "decline"):
        try:
            if action == "approve":
                services.approve_booking(booking, request.user)
                messages.success(request, _("Aprobada. Avisamos á persoa."))
            else:
                _b, refund = services.decline_booking(
                    booking, request.user, request.POST.get("reason", "")
                )
                msg = _("Rexeitada. Avisamos á persoa co motivo.")
                if refund:
                    msg += " " + _("Devolución automática: %(r)s €.") % {
                        "r": f"{refund / 100:.2f}".replace(".", ",")
                    }
                messages.success(request, msg)
        except services.BookingError as exc:
            messages.error(request, str(exc))
        return redirect(treverse(request.tenant, "manage:booking", booking.pk))
    return render(
        request,
        "manage/booking.html",
        {
            "booking": booking,
            "payments": booking.payments.all(),
            "form": form,
            "can_act": can_act,
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
    by_method = _by_payment_method(request)
    return render(
        request,
        "manage/payments.html",
        {
            "payments": qs[:500],
            "totals": totals,
            "by_method": by_method,
            "statuses": Payment.Status.choices,
            "methods": Payment.Method.choices,
            "facilities": Facility.objects.for_tenant(request.tenant),
            "filters": request.GET,
            "nav": "manage",
            "sub": "payments",
        },
    )


def _by_payment_method(request):
    """v5 · Conciliación por forma de pagamento (reservas do período): TPV, oficina, gratuíta,
    bono e aprazado, co cobrado e o pendente de cada unha. E os bonos vendidos."""
    from apps.tenants.models import PaymentMethod

    from .models import Voucher

    qs = Booking.objects.for_tenant(request.tenant).exclude(
        status__in=[Booking.Status.EXPIRED, Booking.Status.REJECTED]
    )
    vouchers = Voucher.objects.for_tenant(request.tenant).exclude(status=Voucher.Status.PENDING)
    g = request.GET
    try:
        if g.get("desde"):
            day = dt.date.fromisoformat(g["desde"])
            qs, vouchers = (
                qs.filter(created_at__date__gte=day),
                vouchers.filter(created_at__date__gte=day),
            )
        if g.get("ata"):
            day = dt.date.fromisoformat(g["ata"])
            qs, vouchers = (
                qs.filter(created_at__date__lte=day),
                vouchers.filter(created_at__date__lte=day),
            )
    except ValueError:
        pass
    if g.get("instalacion", "").isdigit():
        qs = qs.filter(facility_id=int(g["instalacion"]))
    rows = []
    for value, label in PaymentMethod.choices:
        items = [
            b
            for b in qs.filter(payment_method=value).only(
                "price_cents",
                "paid_cents",
                "refunded_cents",
                "status",
                "payment_method",
                "lighting_cents",
            )
        ]
        rows.append(
            {
                "method": value,
                "label": label,
                "bookings": len(items),
                "charged": sum(b.paid_cents - b.refunded_cents for b in items),
                "pending": sum(b.outstanding_cents for b in items),
                "lighting": sum(b.lighting_cents for b in items if b.paid_cents),
            }
        )
    return {
        "rows": rows,
        "vouchers_sold": vouchers.count(),
        "voucher_income": sum(v.price_cents for v in vouchers),
        "voucher_uses": qs.filter(payment_method=PaymentMethod.VOUCHER).count(),
    }


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


@role_required(*ADMIN_ROLES)
def ratings_view(request):
    """Valoracións da veciñanza: índice por instalación, etiquetas e comentarios sen nomes."""
    from apps.analytics.views import _csv

    from . import ratings

    days = (
        int(request.GET.get("dias", 90)) if request.GET.get("dias") in ("30", "90", "365") else 90
    )
    facilities = Facility.objects.for_tenant(request.tenant).order_by("name")
    facility = facilities.filter(pk=request.GET.get("instalacion") or 0).first()
    s = ratings.stats(request.tenant, days=days, facility=facility)
    if request.GET.get("csv") or request.GET.get("ods"):
        return _csv(
            "valoracions.csv",
            ["instalacion", "valoracions", "ben", "regular", "mal", "indice_0_100"],
            [
                [r["facility"].name, r["n"], r["good"], r["ok"], r["bad"], r["index"]]
                for r in s["rows"]
            ],
            ods=bool(request.GET.get("ods")),
        )
    return render(
        request,
        "manage/ratings.html",
        {
            "s": s,
            "days": days,
            "facilities": facilities,
            "facility": facility,
            "tag_labels": ratings.TAGS,
            "nav": "manage",
            "sub": "ratings",
        },
    )
