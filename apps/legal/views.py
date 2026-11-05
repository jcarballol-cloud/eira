# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · D: documentos legais na app, na xestión do concello e no repositorio da deputación."""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST

from apps.accounts.models import audit
from apps.analytics.views import _csv
from apps.tenants.markup import render as render_markup
from apps.tenants.region import region_admin_required
from apps.tenants.urlutils import aggregate_view, role_required, treverse

from . import services
from .models import REVOCABLE, DocKind, LegalAcceptance, LegalDocument


def _kind_or_404(value):
    if value not in DocKind.values:
        raise Http404
    return DocKind(value)


def _channel(request):
    return (
        LegalAcceptance.Channel.APP
        if request.user.is_authenticated and not (request.roles or set()) - {"citizen"}
        else LegalAcceptance.Channel.WEB
    )


# ---------------------------------------------------------------- app
def document_list(request):
    documents = LegalDocument.objects.for_tenant(request.tenant)
    rows = []
    for document in documents:
        current = document.current
        if current is None:
            continue
        rows.append(
            {
                "document": document,
                "current": current,
                "status": services.status_for(request.user, document)
                if request.user.is_authenticated
                else "",
            }
        )
    return render(request, "legal/list.html", {"rows": rows, "nav": "app_home"})


def document_detail(request, kind):
    kind = _kind_or_404(kind)
    document = get_object_or_404(LegalDocument, municipality=request.tenant, kind=kind)
    version = document.current
    number = request.GET.get("v", "")
    if number.isdigit():
        version = get_object_or_404(document.versions, number=int(number))
    if version is None:
        raise Http404
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if version.pk != document.current.pk:
            messages.error(request, _("Só se pode aceptar a versión vixente."))
        elif request.POST.get("accepted") != "1":
            messages.error(request, _("Marca a casiña para aceptar o documento."))
        else:
            services.accept(request.user, version, _channel(request))
            messages.success(
                request,
                _("Aceptado. Podes velo en «A miña conta» → «Documentos aceptados»."),
            )
            pending = services.pending_versions(request.user, request.tenant)
            if pending:
                return redirect(treverse(request.tenant, "legal:detail", pending[0].document.kind))
            return redirect(treverse(request.tenant, "legal:list"))
        return redirect(request.path)
    # v1.5 · D: as normas de cada instalación intégranse aquí sen perderse
    facility_rules = []
    if kind == DocKind.RULES:
        from apps.facilities.models import Facility

        for facility in Facility.objects.for_tenant(request.tenant).filter(is_published=True):
            rules = facility.current_rules()
            if rules:
                facility_rules.append({"facility": facility, "rules": rules})
    status = services.status_for(request.user, document) if request.user.is_authenticated else ""
    return render(
        request,
        "legal/detail.html",
        {
            "document": document,
            "version": version,
            "is_current": version.pk == document.current.pk,
            "body": render_markup(version.body, base_level=1),
            "status": status,
            "versions": document.versions.all(),
            "facility_rules": facility_rules,
            "revocable": kind in REVOCABLE,
            "nav": "app_home",
        },
    )


# ---------------------------------------------------------------- conta da persoa
@login_required
def my_documents(request):
    return render(
        request,
        "legal/my_documents.html",
        {"rows": services.history(request.user), "revocable": REVOCABLE, "nav": "account"},
    )


@login_required
@require_POST
def withdraw(request, pk):
    acceptance = get_object_or_404(LegalAcceptance, pk=pk, user=request.user)
    try:
        services.withdraw(acceptance, request.user)
    except services.LegalError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, _("Consentimento retirado. O rexistro conserva a data."))
    return redirect("account:legal")


# ---------------------------------------------------------------- concello
class PublishForm(forms.Form):
    responsible = forms.CharField(label=gettext_lazy("Responsable do tratamento"), max_length=160)
    dpo = forms.CharField(label=gettext_lazy("Contacto do DPD"), max_length=200)
    address = forms.CharField(label=gettext_lazy("Enderezo"), max_length=200)
    substantial = forms.BooleanField(
        label=gettext_lazy("Cambios substanciais: pedir que se volva aceptar"),
        required=False,
        initial=True,
    )
    adapt = forms.BooleanField(label=gettext_lazy("Adaptar o texto"), required=False)
    title_gl = forms.CharField(
        label=gettext_lazy("Título en galego"), required=False, max_length=160
    )
    title_es = forms.CharField(
        label=gettext_lazy("Título en castelán"), required=False, max_length=160
    )
    body_gl = forms.CharField(
        label=gettext_lazy("Texto en galego"), required=False, widget=forms.Textarea({"rows": 12})
    )
    body_es = forms.CharField(
        label=gettext_lazy("Texto en castelán"), required=False, widget=forms.Textarea({"rows": 12})
    )
    reviewed = forms.BooleanField(
        label=gettext_lazy(
            "Revisamos este texto adaptado cos servizos xurídicos e o DPD (quita o aviso de modelo)"
        ),
        required=False,
    )

    def clean(self):
        data = super().clean()
        if data.get("adapt"):
            for name in ("title_gl", "title_es", "body_gl", "body_es"):
                if not (data.get(name) or "").strip():
                    self.add_error(name, _("Cubre este campo para adaptar o texto."))
        elif data.get("reviewed"):
            self.add_error(
                "reviewed", _("O aviso de modelo só se quita ao adaptar e revisar o texto.")
            )
        return data


@role_required("admin", "dpo", "region_admin")
@aggregate_view
def manage_list(request):
    return render(
        request,
        "legal/manage_list.html",
        {"rows": services.concello_rows(request.tenant), "nav": "manage", "sub": "legal"},
    )


@role_required("admin")
def manage_publish(request, kind):
    kind = _kind_or_404(kind)
    t = request.tenant
    model = services.latest_model(t.region, kind)
    initial = {
        **services.default_values(t),
        "substantial": True,
        "title_gl": model.title_gl,
        "title_es": model.title_es,
        "body_gl": model.body_gl,
        "body_es": model.body_es,
    }
    form = PublishForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        adapted = (
            {k: d[k] for k in ("title_gl", "title_es", "body_gl", "body_es")}
            if d["adapt"]
            else None
        )
        version = services.publish_version(
            t,
            kind,
            model,
            responsible=d["responsible"],
            dpo=d["dpo"],
            address=d["address"],
            adapted=adapted,
            substantial=d["substantial"],
            reviewed=d["reviewed"],
            by=request.user,
        )
        messages.success(
            request,
            _("Publicada a versión %(n)s. As apps xa a mostran.") % {"n": version.number},
        )
        return redirect(treverse(t, "manage:legal"))
    document = LegalDocument.objects.filter(municipality=t, kind=kind).first()
    return render(
        request,
        "legal/manage_publish.html",
        {
            "form": form,
            "kind": kind,
            "kind_label": kind.label,
            "model": model,
            "model_html": render_markup(model.body, base_level=2),
            "current": document.current if document else None,
            "nav": "manage",
            "sub": "legal",
        },
    )


@role_required("admin", "dpo")
def manage_register(request):
    """CSV para xustificar o consentimento. Ten datos persoais: nin a deputación o ve."""
    audit("legal.register_export", request.user, request.tenant)
    return _csv(
        "rexistro-aceptacions.csv",
        services.REGISTER_HEADER,
        list(services.register_rows(request.tenant)),
    )


# ---------------------------------------------------------------- deputación
class ModelForm(forms.Form):
    title_gl = forms.CharField(label=gettext_lazy("Título en galego"), max_length=160)
    title_es = forms.CharField(label=gettext_lazy("Título en castelán"), max_length=160)
    body_gl = forms.CharField(
        label=gettext_lazy("Texto en galego"), widget=forms.Textarea({"rows": 14})
    )
    body_es = forms.CharField(
        label=gettext_lazy("Texto en castelán"), widget=forms.Textarea({"rows": 14})
    )
    substantial = forms.BooleanField(
        label=gettext_lazy("Cambios substanciais"), required=False, initial=True
    )


@region_admin_required
def region_list(request):
    return render(
        request,
        "legal/region_list.html",
        {
            "region": request.region,
            "rows": services.repository(request.region),
            "nav": "region_legal",
        },
    )


@region_admin_required
def region_publish(request, kind):
    kind = _kind_or_404(kind)
    model = services.latest_model(request.region, kind)
    form = ModelForm(
        request.POST or None,
        initial={
            "title_gl": model.title_gl,
            "title_es": model.title_es,
            "body_gl": model.body_gl,
            "body_es": model.body_es,
            "substantial": True,
        },
    )
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        new = services.publish_model(request.region, kind, by=request.user, **d)
        messages.success(
            request,
            _("Modelo publicado (versión %(n)s). Os concellos da rede xa o poden adoptar.")
            % {"n": new.version},
        )
        return redirect("region:legal", request.region.slug)
    return render(
        request,
        "legal/region_publish.html",
        {
            "region": request.region,
            "form": form,
            "kind": kind,
            "kind_label": kind.label,
            "nav": "region_legal",
        },
    )
