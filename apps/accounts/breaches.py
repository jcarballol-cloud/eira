# SPDX-License-Identifier: EUPL-1.2
"""v5 · F: rexistro de brechas de seguridade (arts. 33 e 34 do RXPD).

Só a administración do concello e a persoa delegada de protección de datos (DPD). A deputación
non entra, nin sequera co acceso de soporte (ver docs/rxpd/brechas.md)."""

from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.tenants.urlutils import treverse

from .models import DataBreach, audit

BREACH_ROLES = {"admin", "dpo"}


def breach_access(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        # `admin` só se é do concello (non o superusuario nin a deputación por herdanza)
        from .models import Membership

        roles = set(
            Membership.objects.filter(
                user=request.user, municipality=request.tenant, role__in=BREACH_ROLES
            ).values_list("role", flat=True)
        )
        if not roles:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def format_value(self, value):
        if hasattr(value, "strftime"):
            if timezone.is_aware(value):
                value = timezone.localtime(value)
            return value.strftime("%Y-%m-%dT%H:%M")
        return value


class BreachForm(forms.ModelForm):
    class Meta:
        model = DataBreach
        fields = [
            "detected_at",
            "occurred_at",
            "description",
            "data_affected",
            "people_affected",
            "risk",
            "measures",
            "aepd_notified",
            "aepd_notified_at",
            "aepd_not_needed_reason",
            "people_informed",
            "people_informed_at",
            "status",
        ]
        widgets = {
            "detected_at": DateTimeInput(),
            "occurred_at": DateTimeInput(),
            "aepd_notified_at": DateTimeInput(),
            "people_informed_at": DateTimeInput(),
            "description": forms.Textarea(attrs={"rows": 3}),
            "data_affected": forms.Textarea(attrs={"rows": 2}),
            "measures": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        data = super().clean()
        if data.get("aepd_notified") and not data.get("aepd_notified_at"):
            self.add_error("aepd_notified_at", _("Indica cando se notificou á AEPD."))
        if (
            data.get("risk") in (DataBreach.Risk.RISK, DataBreach.Risk.HIGH)
            and not data.get("aepd_notified")
            and not data.get("aepd_not_needed_reason")
        ):
            self.add_error(
                "aepd_not_needed_reason",
                _("Con risco hai que notificar á AEPD en 72 h ou explicar por que non."),
            )
        if data.get("people_informed") and not data.get("people_informed_at"):
            data["people_informed_at"] = timezone.now()
        return data


@breach_access
def breach_list(request):
    return render(
        request,
        "manage/breaches.html",
        {
            "breaches": DataBreach.objects.filter(municipality=request.tenant),
            "nav": "manage",
            "sub": "breaches",
            "now": timezone.now(),
        },
    )


@breach_access
def breach_edit(request, pk=None):
    breach = (
        get_object_or_404(DataBreach, municipality=request.tenant, pk=pk)
        if pk
        else DataBreach(municipality=request.tenant, detected_at=timezone.now())
    )
    form = BreachForm(request.POST or None, instance=breach)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if obj.pk is None:
            obj.created_by = request.user
        if obj.status == DataBreach.Status.CLOSED and obj.closed_at is None:
            obj.closed_at = timezone.now()
        obj.save()
        audit("breach.save", request.user, request.tenant, obj, status=obj.status)
        messages.success(request, _("Rexistro gardado."))
        return redirect(treverse(request.tenant, "manage:breach", obj.pk))
    return render(
        request,
        "manage/breach_edit.html",
        {"form": form, "breach": breach, "nav": "manage", "sub": "breaches"},
    )


def communication_text(breach):
    """Comunicación modelo ás persoas afectadas (art. 34): linguaxe clara, sen tecnicismos."""
    m = breach.municipality
    return _(
        "Asunto: Información sobre un incidente cos teus datos no servizo de deportes de "
        "%(c)s\n\n"
        "Ola:\n\n"
        "Escribímosche porque o %(d)s detectamos un incidente de seguridade no servizo "
        "municipal de deportes que afecta a datos teus.\n\n"
        "Que pasou: %(what)s\n\n"
        "Que datos: %(data)s\n\n"
        "Que fixemos: %(measures)s\n\n"
        "Que podes facer: desconfía de mensaxes que pidan os teus datos ou pagamentos en nome "
        "do concello e, se tes dúbidas, contacta connosco antes de responder.\n\n"
        "Se queres máis información ou exercer os teus dereitos, contacta coa persoa delegada "
        "de protección de datos: %(dpo)s. Tamén podes reclamar ante a Axencia Española de "
        "Protección de Datos (www.aepd.es).\n\n"
        "Sentímolo e grazas pola túa comprensión.\n"
        "Concello de %(c)s"
    ) % {
        "c": m.name,
        "d": timezone.localtime(breach.detected_at).strftime("%d/%m/%Y"),
        "what": breach.description,
        "data": breach.data_affected,
        "measures": breach.measures or _("Estamos a revisalo e informarémoste."),
        "dpo": m.dpo_contact or m.contact_email or m.contact_phone or "—",
    }


@breach_access
def breach_communication(request, pk):
    breach = get_object_or_404(DataBreach, municipality=request.tenant, pk=pk)
    text = communication_text(breach)
    if request.GET.get("descargar"):
        response = HttpResponse(text, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="comunicacion-brecha-{breach.pk}.txt"'
        )
        return response
    return render(
        request,
        "manage/breach_communication.html",
        {"breach": breach, "text": text, "nav": "manage", "sub": "breaches"},
    )
