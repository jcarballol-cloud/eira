# SPDX-License-Identifier: EUPL-1.2
"""Auditoría RXPD (14/11/2026): «Protección de datos: primeiros pasos».

Lista de comprobación para a administración do concello e o DPD cos sete pasos do paquete RXPD
(`docs/rxpd/paquete/`). Cada paso liga co seu documento (que se le e se descarga dentro de Eira)
ou coa pantalla onde se fai. Marcalo garda a data e a persoa e deixa unha entrada no rexistro de
auditoría. Dous pasos compróbanse cos datos do concello e non se poden marcar se non se cumpren:
o contacto do DPD e o dobre factor obrigatorio.
"""

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy
from django.utils.translation import gettext as _

from apps.tenants.urlutils import treverse

from .breaches import breach_access
from .models import PrivacyStep, audit

PACKAGE = Path(settings.BASE_DIR) / "docs" / "rxpd" / "paquete"

# slug → (ficheiro en galego, ficheiro en castelán, título)
DOCS = {
    "guia": ("00-guia-rapida.md", "es/00-guia-rapida.md", gettext_lazy("Guía rápida")),
    "rexistro": (
        "01-rexistro-actividades.md",
        "es/01-registro-actividades.md",
        gettext_lazy("Rexistro de actividades"),
    ),
    "eipd": ("02-eipd.md", "es/02-eipd.md", gettext_lazy("Avaliación de impacto (EIPD)")),
    "capas": (
        "03-informacion-por-capas.md",
        "es/03-informacion-por-capas.md",
        gettext_lazy("Información por capas"),
    ),
    "encargado": (
        "04-contrato-encargado.md",
        "es/04-contrato-encargado.md",
        gettext_lazy("Contrato de encargado do tratamento"),
    ),
    "conservacion": (
        "05-conservacion.md",
        "es/05-conservacion.md",
        gettext_lazy("Política de conservación"),
    ),
    "dereitos": ("06-dereitos.md", "es/06-derechos.md", gettext_lazy("Dereitos das persoas")),
    "brechas": ("07-brechas.md", "es/07-brechas.md", gettext_lazy("Protocolo de brechas")),
    "minimizacion": (
        "08-minimizacion.md",
        "es/08-minimizacion.md",
        gettext_lazy("Que non garda Eira"),
    ),
}


@dataclass
class Step:
    key: str
    title: str
    body: str
    doc: str = ""
    screen: str = ""  # nome da vista de xestión onde se fai
    screen_label: str = ""
    needs_date: bool = False  # p. ex. data en que o DPD revisou a EIPD
    allows_na: bool = False  # «non procede»
    extra: dict = field(default_factory=dict)


STEPS = [
    Step(
        "dpo",
        gettext_lazy("DPD designado"),
        gettext_lazy(
            "Os concellos teñen que designar unha persoa delegada de protección de datos "
            "(art. 37.1.a RXPD). Pode ser a da deputación. O seu contacto sae na páxina de "
            "privacidade."
        ),
        doc="guia",
        screen="manage:settings",
        screen_label=gettext_lazy("Configuración → Contacto"),
    ),
    Step(
        "legal",
        gettext_lazy("Textos legais adoptados"),
        gettext_lazy(
            "Revisar e adoptar a política de privacidade, as condicións e os consentimentos. "
            "Mentres non se revisen, Eira mostra o aviso de modelo de exemplo."
        ),
        doc="capas",
        screen="manage:legal",
        screen_label=gettext_lazy("Documentos legais"),
    ),
    Step(
        "rat",
        gettext_lazy("Rexistro de actividades descargado e revisado"),
        gettext_lazy(
            "Completar os datos do concello, revisar as actividades e publicar o inventario "
            "(art. 31.2 LOPDGDD)."
        ),
        doc="rexistro",
    ),
    Step(
        "dpia",
        gettext_lazy("EIPD revisada polo DPD"),
        gettext_lazy(
            "Obrigatoria para saúde, menores e accidentes. Anota a data en que o DPD deu a súa "
            "opinión."
        ),
        doc="eipd",
        needs_date=True,
    ),
    Step(
        "processor",
        gettext_lazy("Contrato de encargado asinado (se procede)"),
        gettext_lazy(
            "Só se Eira a aloxa a deputación, unha empresa ou engram. Se a aloxa o propio "
            "concello, marca «Non procede»."
        ),
        doc="encargado",
        allows_na=True,
    ),
    Step(
        "retention",
        gettext_lazy("Prazos de conservación confirmados"),
        gettext_lazy(
            "Eira borra ou anonimiza os datos caducados automaticamente. Confirma os prazos co "
            "DPD ou pide que se cambien."
        ),
        doc="conservacion",
    ),
    Step(
        "twofa",
        gettext_lazy("Dobre factor obrigatorio para a administración"),
        gettext_lazy(
            "Protexe as contas de administración e do DPD aínda que alguén se faga co seu correo."
        ),
        screen="manage:settings",
        screen_label=gettext_lazy("Configuración → Seguridade das contas e rexistro de auditoría"),
    ),
]
BY_KEY = {s.key: s for s in STEPS}


def check(step, tenant):
    """Comprobación cos datos do concello: (cumpre?, texto). None = non hai nada que comprobar."""
    if step.key == "dpo":
        if tenant.dpo_contact:
            return True, _("Contacto do DPD: %(c)s") % {"c": tenant.dpo_contact}
        return False, _("Falta o contacto do DPD en Configuración → Contacto.")
    if step.key == "twofa":
        if tenant.require_2fa_admin:
            return True, _("Activado: a administración e o DPD entran co dobre factor.")
        return False, _("Aínda non está activado en Configuración.")
    if step.key == "legal":
        from apps.legal.models import LegalDocument

        docs = [d for d in LegalDocument.objects.filter(municipality=tenant) if d.current]
        if not docs:
            return False, _("O concello aínda non publicou ningún documento legal.")
        examples = sum(1 for d in docs if d.current.is_example)
        if examples:
            return None, _(
                "%(n)s documentos publicados; %(e)s aínda co aviso de modelo de exemplo."
            ) % {"n": len(docs), "e": examples}
        return True, _("%(n)s documentos publicados e revisados.") % {"n": len(docs)}
    return None, ""


def blocked(step, tenant):
    """Os pasos que se comproban cos datos non se poden marcar como feitos se non se cumpren."""
    ok, _text = check(step, tenant)
    return step.key in ("dpo", "twofa") and not ok


def rows(tenant):
    done = {
        p.key: p for p in PrivacyStep.objects.filter(municipality=tenant).select_related("done_by")
    }
    out = []
    for step in STEPS:
        ok, text = check(step, tenant)
        out.append(
            {
                "step": step,
                "record": done.get(step.key),
                "check_ok": ok,
                "check_text": text,
                "blocked": blocked(step, tenant),
            }
        )
    return out


@breach_access
def steps_view(request):
    t = request.tenant
    if request.method == "POST":
        step = BY_KEY.get(request.POST.get("step", ""))
        action = request.POST.get("action", "")
        if step is None or action not in ("done", "na", "undo"):
            raise Http404
        url = treverse(t, "manage:privacy_steps") + f"#paso-{step.key}"
        if action == "undo":
            PrivacyStep.objects.filter(municipality=t, key=step.key).delete()
            audit("privacy.step_undo", request.user, t, step=step.key)
            messages.info(request, _("Paso marcado como pendente: %(s)s") % {"s": step.title})
            return redirect(url)
        if action == "na" and not step.allows_na:
            raise Http404
        if action == "done" and blocked(step, t):
            messages.error(request, _("Este paso aínda non se cumpre: %(s)s") % {"s": step.title})
            return redirect(url)
        reviewed = None
        if step.needs_date and action == "done":
            try:
                reviewed = dt.date.fromisoformat(request.POST.get("reviewed_on", ""))
            except ValueError:
                messages.error(request, _("Indica a data da revisión."))
                return redirect(url)
        PrivacyStep.objects.update_or_create(
            municipality=t,
            key=step.key,
            defaults={
                "state": PrivacyStep.State.NOT_APPLICABLE
                if action == "na"
                else PrivacyStep.State.DONE,
                "done_by": request.user,
                "reviewed_on": reviewed,
                "done_at": timezone.now(),
            },
        )
        detail = {"step": step.key}
        if reviewed:
            detail["reviewed_on"] = reviewed.isoformat()
        audit(
            "privacy.step_na" if action == "na" else "privacy.step_done", request.user, t, **detail
        )
        messages.success(request, _("Paso gardado: %(s)s") % {"s": step.title})
        return redirect(url)
    data = rows(t)
    return render(
        request,
        "manage/privacy_steps.html",
        {
            "rows": data,
            "done": sum(1 for r in data if r["record"]),
            "total": len(data),
            "docs": [(slug, title) for slug, (_g, _e, title) in DOCS.items()],
            "today": dt.date.today().isoformat(),
            "nav": "manage",
            "sub": "privacy_steps",
        },
    )


def _doc_path(slug):
    if slug not in DOCS:
        raise Http404
    gl, es, title = DOCS[slug]
    name = es if (get_language() or "").startswith("es") and (PACKAGE / es).exists() else gl
    return PACKAGE / name, title


@breach_access
def doc_view(request, slug):
    """Un documento do paquete RXPD, lido ou descargado (a descarga queda en AuditLog)."""
    from apps.tenants.markup import render as render_markup

    path, title = _doc_path(slug)
    text = path.read_text(encoding="utf-8")
    if request.GET.get("descargar") == "1":
        response = HttpResponse(text, content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="eira-{path.name}"'
        return response
    return render(
        request,
        "manage/privacy_doc.html",
        {
            "title": title,
            "slug": slug,
            "body": render_markup(text),
            "nav": "manage",
            "sub": "privacy_steps",
        },
    )


REPO_PACKAGE = "https://github.com/jcarballol-cloud/eira/tree/master/docs/rxpd/paquete"


def minimization(request):
    """Público: «Que non garda Eira, e por que» (08-minimizacion), enlazado desde «Quen custodia
    os teus datos». O resto do paquete é para o concello."""
    from apps.tenants.markup import render as render_markup

    path, title = _doc_path("minimizacion")
    return render(
        request,
        "core/minimization.html",
        {
            "title": title,
            "body": render_markup(path.read_text(encoding="utf-8")),
            "repo": REPO_PACKAGE,
        },
    )
