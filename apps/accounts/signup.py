# SPDX-License-Identifier: EUPL-1.2
"""Alta como na vida real.

1. «Solicitar a app» na web do concello → contraste co padrón (adaptador) → correo coa ligazón
   de instalación e o código de empadroamento. Se non hai coincidencia, revisa o concello.
2. Axuda para instalar en Android e iPhone.
3. Primeira apertura: entrar co correo, introducir o código (xa cuberto se se chega pola
   ligazón) e preguntar pola familia.
4. Mostrador: alta asistida cunha folla imprimible con QR.
"""

import re

from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST

from apps.access.views import qr_svg
from apps.integrations.registry import get_adapter
from apps.tenants.urlutils import neighbour_required, role_required, treverse

from .models import AppRequest, ResidencyInvitation, audit

ADMIN_ROLES = ("admin", "region_admin")


class AppRequestForm(forms.ModelForm):
    """v4: contraste automático co padrón por DNI/NIE + data de nacemento (nunca polo nome)."""

    resident = forms.BooleanField(
        label=gettext_lazy("Vivo no concello e teño o empadroamento aquí"),
        required=False,
        help_text=gettext_lazy(
            "Se non o estás, tamén podes usar a app: entra co teu correo e paga a tarifa xeral."
        ),
    )

    class Meta:
        model = AppRequest
        fields = ["name", "surnames", "email", "id_number", "birth_date", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "surnames": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "inputmode": "email"}),
            "id_number": forms.TextInput(
                attrs={"autocomplete": "off", "autocapitalize": "characters", "spellcheck": "false"}
            ),
            "birth_date": forms.DateInput(attrs={"type": "date", "autocomplete": "bday"}),
            "address": forms.TextInput(attrs={"autocomplete": "street-address"}),
        }
        labels = {"name": gettext_lazy("Nome")}
        help_texts = {
            "id_number": gettext_lazy(
                "Co DNI/NIE e a data de nacemento comprobamos o padrón ao momento. "
                "Despois borrámolos."
            ),
            "address": gettext_lazy("Só se o concello ten que revisar a solicitude."),
        }

    def __init__(self, *args, require_email=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = require_email
        for name in ("surnames", "id_number", "birth_date"):
            self.fields[name].required = True

    def clean_id_number(self):
        from .padron import normalize_id, valid_id

        value = normalize_id(self.cleaned_data.get("id_number"))
        if not valid_id(value):
            raise forms.ValidationError(
                _("Revisa o DNI/NIE: 8 números e letra (ou X/Y/Z, 7 números e letra).")
            )
        return value

    def clean_birth_date(self):
        d = self.cleaned_data.get("birth_date")
        today = timezone.localdate()
        if d and not (today.replace(year=today.year - 110) <= d <= today):
            raise forms.ValidationError(_("Revisa a data de nacemento."))
        return d

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").lower()


class CounterSignupForm(forms.ModelForm):
    """Alta no mostrador: o persoal comproba o empadroamento en persoa; non se pide o DNI."""

    checked = forms.BooleanField(
        label=gettext_lazy("Comprobei o empadroamento no mostrador"), required=True
    )

    class Meta:
        model = AppRequest
        fields = ["name", "surnames", "email"]
        labels = {"name": gettext_lazy("Nome")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = False
        self.fields["email"].help_text = _(
            "Opcional. Se non ten correo, entrégaselle a folla impresa co código."
        )

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").lower()


def install_url(request, tenant, code=""):
    url = request.build_absolute_uri(treverse(tenant, "app:install"))
    return f"{url}?codigo={code}" if code else url


def forget_identity(app_request):
    """Minimización: resolta a solicitude, xa non fan falta o DNI/NIE, a data nin o enderezo."""
    app_request.id_number, app_request.birth_date, app_request.address = "", None, ""


def send_app_code(request, app_request, actor=None, parish=None):
    """Xera o código de empadroamento (ligado ao correo se o hai) e envía a ligazón da app."""
    tenant = app_request.municipality
    inv = ResidencyInvitation.issue(
        tenant,
        note=_("Solicitude da app · %(n)s") % {"n": app_request.name},
        email=app_request.email,
    )
    if parish is not None:  # v1.5 · C: só a parroquia do padrón; a persoa pode cambiala
        inv.parish = parish
        inv.save(update_fields=["parish"])
    app_request.invitation = inv
    app_request.status = AppRequest.Status.SENT
    app_request.resolved_at = timezone.now()
    app_request.resolved_by = actor
    forget_identity(app_request)
    app_request.save()
    audit("app_request.sent", actor, tenant, app_request, channel=app_request.channel)
    if app_request.email:
        get_adapter("mail").send(
            app_request.email,
            _("A túa app de deportes de %(m)s") % {"m": tenant.name},
            _(
                "Ola, %(n)s:\n\n"
                "Xa podes usar a app de instalacións deportivas de %(m)s.\n\n"
                "1. Abre esta ligazón no teu teléfono e instálaa:\n   %(u)s\n\n"
                "2. A primeira vez que a abras pedirache este código de empadroamento:\n"
                "   %(c)s\n   (válido 30 días; só funciona con este correo)\n\n"
                "Android: «Instalar a app» ou menú ⋮ → «Engadir á pantalla de inicio».\n"
                "iPhone: en Safari, botón Compartir → «Engadir á pantalla de inicio».\n\n"
                "Se non pediches isto, ignora esta mensaxe."
            )
            % {
                "n": app_request.name,
                "m": tenant.name,
                "u": install_url(request, tenant, inv.code),
                "c": inv.code,
            },
        )
    return inv


# ---------------------------------------------------------------- veciñanza


def request_app(request):
    from .views import _client_ip, _rate_limited

    request.layout_override = "public"
    form = AppRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        if _rate_limited(d["email"], _client_ip(request)):
            form.add_error(None, _("Demasiadas solicitudes. Téntao de novo nun anaco."))
        else:
            app_request = form.save(commit=False)
            app_request.municipality = request.tenant
            app_request.birth_year = d["birth_date"].year
            if d["resident"]:
                # O nome non entra no contraste: só DNI/NIE + data de nacemento
                result = get_adapter("padron").check(
                    request.tenant, id_number=d["id_number"], birth_date=d["birth_date"]
                )
                app_request.padron_match = result.found
                app_request.review_reason = result.reason
            else:
                forget_identity(app_request)  # sen padrón, a identidade non fai falta
            app_request.save()
            if app_request.padron_match:
                send_app_code(request, app_request, parish=getattr(result, "parish", None))
                outcome = "sent"
            elif d["resident"]:
                outcome = "review"
                get_adapter("mail").send(
                    app_request.email,
                    _("Recibimos a túa solicitude da app de %(m)s") % {"m": request.tenant.name},
                    _(
                        "Non puidemos comprobar automaticamente o empadroamento. O concello revisará "
                        "a solicitude e enviarache o código. Mentres, podes entrar na app co teu "
                        "correo: %(u)s"
                    )
                    % {"m": request.tenant.name, "u": install_url(request, request.tenant)},
                )
            else:
                outcome = "guest"
                app_request.status = AppRequest.Status.SENT
                app_request.save(update_fields=["status"])
                get_adapter("mail").send(
                    app_request.email,
                    _("A túa app de deportes de %(m)s") % {"m": request.tenant.name},
                    _("Instala a app desde esta ligazón e entra co teu correo: %(u)s")
                    % {"u": install_url(request, request.tenant)},
                )
            request.session["app_request"] = {"outcome": outcome, "email": app_request.email}
            return redirect(treverse(request.tenant, "app:request_done"))
    return render(request, "app/request.html", {"form": form, "nav": "app_request"})


def request_done(request):
    request.layout_override = "public"
    info = request.session.get("app_request")
    if not info:
        return redirect(treverse(request.tenant, "app:request"))
    return render(request, "app/request_done.html", {"info": info})


def _platform(request):
    ua = request.headers.get("User-Agent", "")
    if re.search(r"iPhone|iPad|iPod", ua):
        return "ios"
    if "Android" in ua:
        return "android"
    return ""


def install(request):
    request.layout_override = "public"
    code = request.GET.get("codigo", "").strip().upper()[:12]
    if code:
        request.session["residency_code"] = code
    return render(
        request,
        "app/install.html",
        {"platform": _platform(request), "code": code or request.session.get("residency_code", "")},
    )


@neighbour_required
def welcome(request):
    """Primeira apertura da app: código de empadroamento e familia."""
    step = request.GET.get("paso", "")
    resident = request.user.is_resident(request.tenant)
    if step != "familia" and not resident:
        code = request.POST.get("code") or request.session.get("residency_code", "")
        error = ""
        if request.method == "POST":
            municipality = ResidencyInvitation.redeem(request.user, code)
            if municipality == request.tenant:
                request.session.pop("residency_code", None)
                messages.success(
                    request,
                    _("Empadroamento validado: aplicaráseche a tarifa de veciñanza de %(m)s.")
                    % {"m": municipality.name},
                )
                return redirect(treverse(request.tenant, "app:welcome") + "?paso=familia")
            if municipality:  # código doutro concello: válido igualmente
                request.session.pop("residency_code", None)
                return redirect(treverse(municipality, "app:welcome") + "?paso=familia")
            error = _("O código non é válido, xa se usou ou foi enviado a outro correo.")
        return render(request, "app/welcome.html", {"step": "code", "code": code, "error": error})
    household = getattr(request.user, "household", None)
    return render(
        request,
        "app/welcome.html",
        {"step": "family", "dependents": list(household.dependents.all()) if household else []},
    )


# ---------------------------------------------------------------- concello


def _signups_url(request):
    return treverse(request.tenant, "manage:signups")


@role_required(*ADMIN_ROLES)
def signups(request):
    form = CounterSignupForm(request.POST or None, prefix="c")
    if request.method == "POST" and form.is_valid():
        app_request = form.save(commit=False)
        app_request.municipality = request.tenant
        app_request.channel = AppRequest.Channel.COUNTER
        app_request.padron_match = True
        app_request.save()
        send_app_code(request, app_request, actor=request.user)
        return redirect(treverse(request.tenant, "manage:signup_sheet", app_request.pk))
    qs = AppRequest.objects.filter(municipality=request.tenant).select_related("invitation")
    return render(
        request,
        "manage/signups.html",
        {
            "form": form,
            "pending": qs.filter(status=AppRequest.Status.PENDING),
            "recent": qs.exclude(status=AppRequest.Status.PENDING)[:25],
            "nav": "manage",
            "sub": "signups",
        },
    )


@role_required(*ADMIN_ROLES)
@require_POST
def signup_resolve(request, pk):
    app_request = get_object_or_404(
        AppRequest, municipality=request.tenant, pk=pk, status=AppRequest.Status.PENDING
    )
    if request.POST.get("action") == "approve":
        send_app_code(request, app_request, actor=request.user)
        messages.success(request, _("Código enviado a %(e)s.") % {"e": app_request.email})
    else:
        app_request.status = AppRequest.Status.REJECTED
        app_request.resolved_at, app_request.resolved_by = timezone.now(), request.user
        forget_identity(app_request)
        app_request.save()
        audit("app_request.rejected", request.user, request.tenant, app_request)
        if app_request.email:
            get_adapter("mail").send(
                app_request.email,
                _("A túa solicitude da app de %(m)s") % {"m": request.tenant.name},
                _(
                    "Non atopamos o empadroamento cos datos indicados. Podes usar a app coa "
                    "tarifa xeral ou achegarte ao mostrador de deportes para revisalo."
                ),
            )
        messages.success(request, _("Solicitude marcada como non empadroada."))
    return redirect(_signups_url(request))


@role_required(*ADMIN_ROLES)
def signup_sheet(request, pk):
    app_request = get_object_or_404(
        AppRequest.objects.select_related("invitation"), municipality=request.tenant, pk=pk
    )
    code = app_request.invitation.code if app_request.invitation else ""
    url = install_url(request, request.tenant, code)
    return render(
        request,
        "manage/signup_sheet.html",
        {
            "r": app_request,
            "code": code,
            "url": url,
            "svg": qr_svg(url),
            "nav": "manage",
            "sub": "signups",
        },
    )


# ---------------------------------------------------------------- padrón (v4)


class PadronUploadForm(forms.Form):
    file = forms.FileField(
        label=gettext_lazy("CSV do padrón"),
        help_text=gettext_lazy(
            "Columnas dni_nie e data_nacemento. Substitúe a carga anterior. O ficheiro non se garda."
        ),
        widget=forms.ClearableFileInput(attrs={"accept": ".csv,text/csv"}),
    )


@role_required("admin")
def padron_page(request):
    from . import padron

    form = PadronUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        batch = padron.import_csv(request.tenant, form.cleaned_data["file"], by=request.user)
        messages.success(
            request,
            _("Padrón cargado: %(n)s persoas. Liñas rexeitadas: %(r)s.")
            % {"n": batch.count, "r": batch.rejected},
        )
        return redirect(treverse(request.tenant, "manage:padron"))
    from .models import PadronImport

    return render(
        request,
        "manage/padron.html",
        {
            "form": form,
            "imports": PadronImport.objects.filter(municipality=request.tenant).select_related(
                "imported_by"
            )[:20],
            "current": padron.current(request.tenant),
            "pending": AppRequest.objects.filter(
                municipality=request.tenant, status=AppRequest.Status.PENDING
            ).count(),
            "nav": "manage",
            "sub": "signups",
        },
    )


@role_required("admin")
def padron_template(request):
    from django.http import HttpResponse

    from .padron import TEMPLATE

    resp = HttpResponse(TEMPLATE, content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="padron-modelo.csv"'
    return resp
