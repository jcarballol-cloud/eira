# SPDX-License-Identifier: EUPL-1.2
import datetime as dt

from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.validators import MaxValueValidator
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
from apps.tenants.urlutils import neighbour_required, treverse

from . import ics, payments, services
from .models import Booking
from .ratings import RatingForm, can_rate


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
    # v5 · participantes, forma de pagamento e luz
    participants = forms.IntegerField(
        label=gettext_lazy("Cantas persoas ides?"),
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"inputmode": "numeric"}),
    )
    participant_names = forms.CharField(
        label=gettext_lazy("Nomes (opcional)"),
        required=False,
        help_text=gettext_lazy("Un por liña. Só os ve o concello e bórranse coa reserva."),
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    payment_method = forms.ChoiceField(
        label=gettext_lazy("Como pagas?"), widget=forms.RadioSelect, required=False
    )
    voucher = forms.ChoiceField(label=gettext_lazy("Bono"), required=False)
    needs_light = forms.BooleanField(
        label=gettext_lazy("Necesito luz"),
        required=False,
        help_text=gettext_lazy("Márcao se queres as luces acesas aínda que sexa de día."),
    )
    accept_rules = forms.BooleanField(
        label=gettext_lazy("Lin e acepto as normas de uso, dereitos e deberes desta instalación."),
        error_messages={"required": gettext_lazy("Para reservar debes aceptar as normas.")},
    )

    def __init__(self, *args, facility=None, vouchers=(), **kwargs):
        super().__init__(*args, **kwargs)
        from apps.tenants.models import PaymentMethod

        self.fields["participants"].max_value = facility.max_participants
        self.fields["participants"].widget.attrs["max"] = facility.max_participants
        self.fields["participants"].validators.append(MaxValueValidator(facility.max_participants))
        self.fields["participants"].help_text = _("Máximo %(n)s.") % {
            "n": facility.max_participants
        }
        labels = dict(PaymentMethod.choices)
        methods = [
            m for m in facility.payment_method_list() if m != PaymentMethod.VOUCHER or vouchers
        ] or [PaymentMethod.TPV.value]
        self.fields["payment_method"].choices = [(m, labels[m]) for m in methods]
        self.fields["payment_method"].initial = methods[0]
        self.methods = methods
        if vouchers:
            self.fields["voucher"].choices = [
                (str(v.pk), f"{v.type.name} · {v.uses_left}/{v.uses_total}") for v in vouchers
            ]
        else:
            del self.fields["voucher"]
        if len(methods) == 1:
            self.fields["payment_method"].widget = forms.HiddenInput()
        if not (facility.lighting and facility.lighting_supplement_cents):
            del self.fields["needs_light"]

    def clean_payment_method(self):
        value = self.cleaned_data.get("payment_method") or self.methods[0]
        if value not in self.methods:
            raise forms.ValidationError(_("Escolle unha forma de pagamento."))
        return value


def _go_to_gateway(request, booking):
    url_ok = treverse(request.tenant, "bookings:payment_return", booking.pk) + "?resultado=ok"
    url_ko = treverse(request.tenant, "bookings:payment_return", booking.pk) + "?resultado=ko"
    return redirect(payments.start_online_payment(booking=booking, url_ok=url_ok, url_ko=url_ko))


@neighbour_required
def book(request, pk):
    tenant = request.tenant
    facility = get_object_or_404(Facility, municipality=tenant, pk=pk, is_published=True)
    start = _parse_start(request.GET.get("inicio") or request.POST.get("inicio"))
    if start is None:
        return redirect(treverse(tenant, "facilities:detail", facility.pk))
    rules = facility.current_rules()
    vouchers = services.usable_vouchers(facility, request.user)
    data = (
        request.POST
        if request.method == "POST"
        else (request.GET if request.GET.get("resumo") else None)
    )
    form = ConfirmForm(data, facility=facility, vouchers=vouchers)
    # Prezo cos datos que haxa (forma de pagamento e «necesito luz») para o desglose
    method = (data or {}).get("payment_method") or form.methods[0]
    if method not in form.methods:
        method = form.methods[0]
    needs_light = bool((data or {}).get("needs_light")) and "needs_light" in form.fields
    quote = services.quote(facility, request.user, start, needs_light=needs_light, method=method)
    origin = services.network_origin(tenant, request.user)
    error = None
    if not tenant.network_open and not services.linked_to(tenant, request.user):
        error = _("%(c)s non admite agora reservas de persoas doutros concellos.") % {
            "c": tenant.name
        }
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            booking = services.create_booking(
                facility,
                start,
                request.user,
                rules_version=rules,
                participants=d["participants"],
                participant_names=d.get("participant_names", ""),
                payment_method=d["payment_method"],
                needs_light=d.get("needs_light", False),
                voucher=int(d["voucher"]) if d.get("voucher") else None,
            )
        except services.BookingError as exc:
            error = str(exc)
        else:
            if booking.status == Booking.Status.PENDING_PAYMENT:
                return _go_to_gateway(request, booking)
            if booking.status == Booking.Status.PENDING_APPROVAL:
                messages.info(
                    request,
                    _("Solicitude enviada. O concello ten que aprobala; avisarémoste da resposta."),
                )
            elif booking.status == Booking.Status.PENDING_OFFICE:
                messages.warning(
                    request,
                    _("Reserva gardada. Págaa na oficina antes do %(d)s ou quedará libre.")
                    % {"d": timezone.localtime(booking.hold_expires_at).strftime("%d/%m %H:%M")},
                )
            else:
                messages.success(request, _("Reserva confirmada."))
            return redirect(treverse(tenant, "bookings:detail", booking.pk))
    ctx = {
        "facility": facility,
        "start": start,
        "end": start + dt.timedelta(minutes=facility.slot_minutes),
        "rules": rules,
        "quote": quote,
        "price": quote.total_cents,
        "base_price": quote.base_cents,
        "discount": quote.discount_pct,
        "audience": quote.audience,
        "hold_minutes": settings.EIRA_PAYMENT_HOLD_MINUTES,
        "form": form,
        "error": error,
        "nav": "facilities",
        "network_origin": origin,
        "audience_label": dict(facility.tariffs.model.Audience.choices).get(quote.audience, ""),
    }
    if request.GET.get("resumo") and request.headers.get("HX-Request"):
        return render(request, "bookings/_price.html", ctx)
    ctx["forecast"], ctx["tips"] = weather_for(facility, start)
    return render(request, "bookings/confirm.html", ctx)


@neighbour_required
def payment_return(request, pk):
    """Volta da pasarela. **Non decide nada**: mostra o estado que fixou a notificación asinada."""
    booking = get_object_or_404(
        Booking.objects.select_related("facility"),
        municipality=request.tenant,
        pk=pk,
        user=request.user,
    )
    payment = booking.payments.order_by("-created_at").first()
    template = (
        "bookings/_payment_status.html"
        if request.headers.get("HX-Request")
        else "bookings/payment_result.html"
    )
    return render(
        request,
        template,
        {
            "booking": booking,
            "payment": payment,
            "returned": request.GET.get("resultado", ""),
            "nav": "bookings",
            "step": 3,
        },
    )


@neighbour_required
def retry_payment(request, pk):
    booking = get_object_or_404(
        Booking,
        municipality=request.tenant,
        pk=pk,
        user=request.user,
        status=Booking.Status.PENDING_PAYMENT,
    )
    if booking.hold_expires_at and booking.hold_expires_at <= timezone.now():
        services.expire_holds()
        messages.error(request, _("O tempo para pagar esgotouse e a franxa quedou libre."))
        return redirect(treverse(request.tenant, "facilities:detail", booking.facility_id))
    return _go_to_gateway(request, booking)


@neighbour_required
def mine(request):
    qs = (
        Booking.objects.for_tenant(request.tenant)
        .filter(user=request.user)
        .select_related("facility")
    )
    now = timezone.now()
    open_statuses = [
        Booking.Status.CONFIRMED,
        Booking.Status.PENDING_PAYMENT,
        Booking.Status.USED,
        Booking.Status.PENDING_APPROVAL,
        Booking.Status.PENDING_OFFICE,
    ]
    upcoming = qs.filter(end__gt=now, status__in=open_statuses).order_by("start")
    # v5: reservas nos concellos próximos da mesma rede (as do propio concello van arriba)
    elsewhere = []
    if request.tenant.region_id:
        elsewhere = (
            Booking.objects.filter(
                user=request.user,
                municipality__region_id=request.tenant.region_id,
                end__gt=now,
                status__in=open_statuses,
            )
            .exclude(municipality=request.tenant)
            .select_related("facility", "municipality")
            .order_by("start")
        )
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
            "elsewhere": elsewhere,
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


@neighbour_required
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
            "can_rate": can_rate(booking),
            "now": timezone.now(),
            # Só a propia persoa e só se ela decidiu gardalo na conta (art. 9)
            "account_health": getattr(
                getattr(request.user, "health_profile", None), "as_dict", lambda: None
            )(),
        },
    )


@neighbour_required
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


@neighbour_required
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


@neighbour_required
def receipt(request, pk):
    booking = _own_booking(request, pk)
    if booking.paid_cents == 0 and booking.price_cents > 0:
        raise Http404
    if request.GET.get("formato") == "pdf":
        return receipt_pdf(booking)
    return render(request, "bookings/receipt.html", {"booking": booking, "nav": "bookings"})


def receipt_pdf(booking):
    from .pdf import simple_pdf

    start = timezone.localtime(booking.start)
    end = timezone.localtime(booking.end)
    payment = booking.payments.exclude(status="pending").first()
    lines = [
        (_("Concello de %(n)s") % {"n": booking.municipality.name}, 16, True),
        (_("Servizo municipal de deportes · Recibo"), 11, False),
        ("", 8, False),
        (_("Referencia da reserva: %(r)s") % {"r": booking.reference}, 11, True),
        (_("Persoa: %(p)s") % {"p": booking.holder_label or "—"}, 11, False),
        (_("Instalación: %(f)s") % {"f": booking.facility.name}, 11, False),
        (
            _("Uso: %(d)s de %(a)s a %(b)s")
            % {
                "d": start.strftime("%d/%m/%Y"),
                "a": start.strftime("%H:%M"),
                "b": end.strftime("%H:%M"),
            },
            11,
            False,
        ),
        (_("Tarifa: %(t)s") % {"t": booking.tariff_audience}, 11, False),
    ]
    if booking.discount_pct:
        lines.append(
            (
                _("Prezo habitual: %(b)s € · desconto franxa tranquila −%(d)s %%")
                % {
                    "b": f"{booking.base_price_cents / 100:.2f}".replace(".", ","),
                    "d": booking.discount_pct,
                },
                11,
                False,
            )
        )
    if booking.lighting_cents:
        lines.append(
            (
                _("Desglose: %(k)s %(s)s € + luz %(l)s €")
                % {
                    "k": booking.facility.get_kind_display(),
                    "s": f"{booking.slot_cents / 100:.2f}".replace(".", ","),
                    "l": f"{booking.lighting_cents / 100:.2f}".replace(".", ","),
                },
                11,
                False,
            )
        )
    lines.append(
        (_("Forma de pagamento: %(m)s") % {"m": booking.get_payment_method_display()}, 11, False)
    )
    lines += [
        (
            _("Importe pagado: %(p)s €")
            % {"p": f"{booking.paid_cents / 100:.2f}".replace(".", ",")},
            13,
            True,
        ),
    ]
    if booking.refunded_cents:
        lines.append(
            (
                _("Devolto: %(p)s €")
                % {"p": f"{booking.refunded_cents / 100:.2f}".replace(".", ",")},
                11,
                False,
            )
        )
    if payment:
        lines.append(
            (
                _("Operación: %(r)s · %(m)s")
                % {"r": payment.reference, "m": payment.get_method_display()},
                10,
                False,
            )
        )
    lines += [("", 8, False), (_("Documento xerado por Eira (software libre EUPL-1.2)."), 9, False)]
    response = HttpResponse(
        simple_pdf(lines, title=f"Recibo {booking.reference}"), content_type="application/pdf"
    )
    response["Content-Disposition"] = f'attachment; filename="recibo-{booking.reference}.pdf"'
    return response


@neighbour_required
def ics_one(request, pk):
    booking = _own_booking(request, pk)
    url = request.build_absolute_uri(treverse(request.tenant, "bookings:detail", booking.pk))
    body = ics.calendar([booking], url_for=lambda b: url, name=booking.facility.name)
    response = HttpResponse(body, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="reserva-{booking.reference}.ics"'
    return response


@neighbour_required
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


@neighbour_required
def checklist(request, pk):
    booking = _own_booking(request, pk)
    if booking.closed_at:
        messages.info(request, _("Xa enviaches o checklist de peche desta reserva."))
        return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    needs_key = booking.facility.access_level == 1
    form = ChecklistForm(request.POST or None, needs_key=needs_key)
    rating_form = RatingForm(request.POST or None, prefix="v")
    if request.method == "POST" and form.is_valid() and rating_form.is_valid():
        if can_rate(booking):
            rating_form.save(booking)
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
        request,
        "bookings/checklist.html",
        {"booking": booking, "form": form, "rating_form": rating_form, "nav": "bookings"},
    )


@neighbour_required
def rate(request, pk):
    """«Que tal foi?» fóra do checklist (instalacións abertas ou valoración posterior)."""
    booking = _own_booking(request, pk)
    if not can_rate(booking):
        return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    form = RatingForm(request.POST or None, prefix="v", required=True)
    if request.method == "POST" and form.is_valid():
        rating = form.save(booking)
        if rating.incident:
            messages.warning(
                request,
                _("Grazas. Creamos a incidencia #%(n)s para que o concello o revise.")
                % {"n": rating.incident.pk},
            )
        else:
            messages.success(request, _("Grazas pola túa valoración!"))
        return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    return render(
        request, "bookings/rate.html", {"booking": booking, "rating_form": form, "nav": "bookings"}
    )


@neighbour_required
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


class StartStateForm(forms.Form):
    """v5 · D: como está a pista e o material ao entrar."""

    state = forms.ChoiceField(
        label=gettext_lazy("Como atopaches a instalación e o material?"),
        choices=[
            ("ok", gettext_lazy("Todo ben")),
            ("problem", gettext_lazy("Hai un problema")),
        ],
        widget=forms.RadioSelect,
    )
    notes = forms.CharField(
        label=gettext_lazy("Que viches? (opcional)"),
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    photo = forms.ImageField(
        label=gettext_lazy("Foto (opcional)"),
        required=False,
        help_text=gettext_lazy("Quitámoslle a localización e os datos da cámara."),
        widget=forms.ClearableFileInput(attrs={"accept": "image/*", "capture": "environment"}),
    )

    def clean_photo(self):
        from apps.tenants.uploads import clean_image

        photo = self.cleaned_data.get("photo")
        return clean_image(photo) if photo else None


@neighbour_required
def start_state(request, pk):
    booking = _own_booking(request, pk)
    if booking.start_state_at:
        messages.info(request, _("Xa indicaches como estaba a instalación ao entrar."))
        return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    form = StartStateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        incident = services.submit_start_state(
            booking, d["state"] == "ok", d.get("notes", ""), d.get("photo"), by=request.user
        )
        if incident:
            messages.warning(
                request,
                _(
                    "Grazas. Creamos a incidencia #%(n)s e queda rexistrado que xa estaba antes "
                    "da túa reserva."
                )
                % {"n": incident.pk},
            )
        else:
            messages.success(request, _("Grazas! Bo adestramento."))
        return redirect(treverse(request.tenant, "bookings:detail", booking.pk))
    return render(
        request,
        "bookings/start_state.html",
        {"booking": booking, "form": form, "nav": "bookings"},
    )
