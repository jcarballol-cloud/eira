# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · A: «Aviso» e «Alerta» na app (e na tableta), protocolo de accidente paso a paso,
rexistro de accidentes e páxina da persoa responsable para un peche sen confirmar (B)."""

from django import forms
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST

from apps.accounts.profiles import STAFF_ROLES
from apps.bookings.models import Booking
from apps.facilities.models import Facility
from apps.tenants.urlutils import treverse

from . import services
from .models import AccidentReport, Alert, ClosingEscalation


def _facility(request, value):
    if not value:
        return None
    try:
        return Facility.objects.for_tenant(request.tenant).get(pk=int(value))
    except (ValueError, Facility.DoesNotExist):
        return None


def active_booking(request):
    """Reserva en curso da persoa neste concello (para ofrecer os dous botóns sen menú)."""
    if not request.user.is_authenticated:
        return None
    now = timezone.now()
    return (
        Booking.objects.for_tenant(request.tenant)
        .filter(
            user=request.user,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.USED],
            start__lte=now,
            end__gt=now,
        )
        .select_related("facility")
        .first()
    )


def _context(request):
    booking = None
    if request.user.is_authenticated and (
        request.GET.get("reserva") or request.POST.get("reserva")
    ):
        booking = (
            Booking.objects.for_tenant(request.tenant)
            .filter(
                user=request.user, pk=(request.GET.get("reserva") or request.POST.get("reserva"))
            )
            .select_related("facility")
            .first()
        )
    booking = booking or active_booking(request)
    facility = _facility(request, request.GET.get("instalacion") or request.POST.get("instalacion"))
    if facility is None and booking is not None:
        facility = booking.facility
    if facility is None and request.roles & STAFF_ROLES:
        # v1.5 · B: o persoal non ten que buscar a instalación onde está a traballar
        facility = services.current_facility(request.user, request.tenant)
    return facility, booking


def _origin_for(request, booking):
    """v1.5 · B: de que app saíu a alerta, segundo o perfil no concello."""
    roles = request.roles
    if "admin" in roles:
        return Alert.Origin.ADMIN
    if "maintenance" in roles:
        return Alert.Origin.OPERATOR
    if "cleaning" in roles:
        return Alert.Origin.CLEANING
    if "monitor" in roles:
        return Alert.Origin.MONITOR
    return Alert.Origin.BOOKING if booking else Alert.Origin.APP


def alert_choice(request):
    """Alerta: dúas opcións grandes, «Accidente deportivo» e «Emerxencia de seguridade»."""
    facility, booking = _context(request)
    return render(
        request,
        "safety/alert.html",
        {
            "facility": facility,
            "booking": booking,
            "session_id": request.GET.get("sesion", ""),
            "location": services.location_for_112(facility),
            "aed": services.aed_info(facility),
            "facilities": Facility.objects.for_tenant(request.tenant).filter(is_published=True),
            "nav": "incident",
        },
    )


def _raise(request, kind):
    facility, booking = _context(request)
    session = None
    origin = _origin_for(request, booking)
    if request.POST.get("sesion"):
        from apps.activities.models import Session

        session = (
            Session.objects.filter(
                group__municipality=request.tenant, pk=request.POST.get("sesion")
            ).first()
            if request.POST.get("sesion", "").isdigit()
            else None
        )
        if session is not None:
            origin = Alert.Origin.MONITOR
            facility = facility or session.group.facility
    if not request.user.is_authenticated:
        ip = request.META.get("REMOTE_ADDR", "")
        if not services.anonymous_alert_allowed(f"{request.tenant.pk}:{ip}"):
            return None
    return services.raise_alert(
        kind,
        request.tenant,
        user=request.user,
        facility=facility,
        booking=booking,
        session=session,
        origin=origin,
    )


@require_POST
def alert_accident(request):
    alert = _raise(request, Alert.Kind.ACCIDENT)
    if alert is None:
        messages.warning(
            request, _("Xa se enviaron varias alertas desde aquí. Se é grave, chama ao 112.")
        )
        return redirect(treverse(request.tenant, "safety:protocol"))
    url = (
        treverse(request.tenant, "safety:protocol_facility", alert.facility_id)
        if alert.facility_id
        else treverse(request.tenant, "safety:protocol")
    )
    return redirect(f"{url}?alerta={alert.pk}")


@require_POST
def alert_security(request):
    alert = _raise(request, Alert.Kind.SECURITY)
    url = treverse(request.tenant, "safety:emergency")
    return redirect(f"{url}?alerta={alert.pk}" if alert else url)


def _alert_from_query(request):
    value = request.GET.get("alerta", "")
    if not value.isdigit():
        return None
    return Alert.objects.filter(municipality=request.tenant, pk=int(value)).first()


def emergency(request):
    alert = _alert_from_query(request)
    facility = alert.facility if alert else None
    return render(
        request,
        "safety/emergency.html",
        {
            "alert": alert,
            "location": services.location_for_112(facility),
            "aed": services.aed_info(facility),
            "nav": "incident",
        },
    )


def protocol(request, facility_pk=None):
    facility = None
    if facility_pk is not None:
        facility = get_object_or_404(Facility.objects.for_tenant(request.tenant), pk=facility_pk)
    alert = _alert_from_query(request)
    proto = services.protocol_for(request.tenant, facility)
    return render(
        request,
        "safety/protocol.html",
        {
            "facility": facility,
            "alert": alert,
            "protocol": proto,
            "steps": proto.steps(),
            "aed": services.aed_info(facility),
            "location": services.location_for_112(facility),
            "facilities": Facility.objects.for_tenant(request.tenant).filter(is_published=True),
            "nav": "incident",
        },
    )


class AccidentForm(forms.Form):
    occurred_at = forms.DateTimeField(
        label=gettext_lazy("Data e hora"),
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
    )
    kind = forms.ChoiceField(
        label=gettext_lazy("Tipo xeral"),
        choices=AccidentReport.Kind.choices,
        widget=forms.RadioSelect,
    )
    severity = forms.ChoiceField(
        label=gettext_lazy("Gravidade percibida"),
        choices=AccidentReport.Severity.choices,
        widget=forms.RadioSelect,
    )
    called_112 = forms.BooleanField(label=gettext_lazy("Chamouse ao 112"), required=False)
    reporter_role = forms.ChoiceField(
        label=gettext_lazy("Quen o comunica"),
        choices=AccidentReport.ReporterRole.choices,
        widget=forms.RadioSelect,
    )


def accident_register(request, facility_pk):
    facility = get_object_or_404(Facility.objects.for_tenant(request.tenant), pk=facility_pk)
    alert = _alert_from_query(request)
    role = (
        "monitor"
        if "monitor" in request.roles
        else ("staff" if request.roles - {"citizen"} else "user")
    )
    initial = {
        "occurred_at": timezone.localtime(alert.created_at if alert else timezone.now()).strftime(
            "%Y-%m-%dT%H:%M"
        ),
        "reporter_role": role,
    }
    form = AccidentForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        services.register_accident(
            request.tenant,
            facility,
            kind=d["kind"],
            severity=d["severity"],
            called_112=d["called_112"],
            reporter_role=d["reporter_role"],
            occurred_at=d["occurred_at"],
            user=request.user,
            alert=alert,
        )
        return render(
            request, "safety/accident_done.html", {"facility": facility, "nav": "incident"}
        )
    return render(
        request,
        "safety/accident_form.html",
        {"form": form, "facility": facility, "alert": alert, "nav": "incident"},
    )


# ---------------------------------------------------------------- B · persoa responsable
def closing_contact(request, token):
    """Páxina que recibe a persoa responsable (ligazón no aviso, sen necesidade de conta)."""
    esc = (
        ClosingEscalation.objects.filter(municipality=request.tenant, token=token)
        .select_related("booking__facility", "contact")
        .first()
    )
    if esc is None:
        raise Http404
    police_logged = False
    if request.method == "POST":
        action = request.POST.get("accion")
        if action == "revisado" and esc.is_open:
            services.resolve_by_contact(
                esc,
                by=request.user if request.user.is_authenticated else None,
                note=request.POST.get("nota", ""),
            )
            messages.success(request, _("Anotado: instalación revisada."))
            return redirect(treverse(request.tenant, "safety:closing", token))
        if action == "policia" and esc.municipality.police_phone:
            services.log_police_contact(
                esc,
                user=request.user if request.user.is_authenticated else None,
                contact=esc.contact,
            )
            police_logged = True
    return render(
        request,
        "safety/closing_contact.html",
        {"esc": esc, "booking": esc.booking, "police_logged": police_logged},
    )
