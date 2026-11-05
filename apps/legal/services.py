# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · D: regras dos documentos legais: modelos, adopción, aceptación e retirada."""

from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import audit

from .models import (
    MODEL_FILES,
    REQUIRED,
    REVOCABLE,
    DocKind,
    LegalAcceptance,
    LegalDocument,
    LegalModel,
    LegalVersion,
)

MODELS_DIR = Path(settings.BASE_DIR) / "docs" / "legal" / "modelos"
PLACEHOLDERS = ("[RESPONSABLE]", "[DPD]", "[ENDEREZO]", "[CONCELLO]")


class LegalError(Exception):
    pass


# ------------------------------------------------------------------ modelos
def _read_model_file(slug, lang):
    """Devolve (título, corpo) sen a cabeceira SPDX nin o aviso, que a app mostra sempre."""
    lines = (MODELS_DIR / f"{slug}.{lang}.md").read_text(encoding="utf-8").splitlines()
    kept = [ln for ln in lines if not ln.startswith(("<!--", "> **MODELO"))]
    text = "\n".join(kept).strip()
    title, _sep, body = text.partition("\n")
    return title.lstrip("# ").strip(), body.strip()


def included_model(kind):
    """Modelo incluído en Eira. Créase a partir de docs/legal/modelos/ a primeira vez."""
    found = LegalModel.objects.filter(region__isnull=True, kind=kind).order_by("-version").first()
    if found:
        return found
    title_gl, body_gl = _read_model_file(MODEL_FILES[DocKind(kind)], "gl")
    title_es, body_es = _read_model_file(MODEL_FILES[DocKind(kind)], "es")
    return LegalModel.objects.create(
        region=None,
        kind=kind,
        title_gl=title_gl,
        title_es=title_es,
        body_gl=body_gl,
        body_es=body_es,
    )


def latest_model(region, kind):
    """Modelo vixente: o último da deputación ou, se aínda non publicou ningún, o incluído."""
    if region is not None:
        own = LegalModel.objects.filter(region=region, kind=kind).order_by("-version").first()
        if own:
            return own
    return included_model(kind)


def repository(region):
    """Repositorio da deputación: un elemento por tipo de documento."""
    rows = []
    for kind in DocKind:
        own = LegalModel.objects.filter(region=region, kind=kind).order_by("-version").first()
        rows.append(
            {
                "kind": kind,
                "model": own or included_model(kind),
                "published": own is not None,
                "versions": LegalModel.objects.filter(region=region, kind=kind).count(),
            }
        )
    return rows


def publish_model(region, kind, *, title_gl, title_es, body_gl, body_es, substantial=True, by=None):
    last = LegalModel.objects.filter(region=region, kind=kind).order_by("-version").first()
    model = LegalModel.objects.create(
        region=region,
        kind=kind,
        version=(last.version + 1) if last else 1,
        title_gl=title_gl,
        title_es=title_es,
        body_gl=body_gl,
        body_es=body_es,
        substantial=substantial,
        published_by=by,
    )
    audit("legal.model_publish", by, None, model, kind=kind, version=model.version)
    return model


# ------------------------------------------------------------------ adopción polo concello
def fill(text, *, responsible, dpo, address, municipality):
    values = {
        "[RESPONSABLE]": responsible,
        "[DPD]": dpo,
        "[ENDEREZO]": address,
        "[CONCELLO]": municipality.name,
    }
    for token, value in values.items():
        text = text.replace(token, value)
    return text


def default_values(municipality):
    return {
        "responsible": _("Concello de %(n)s") % {"n": municipality.name},
        "dpo": municipality.dpo_contact,
        "address": municipality.address,
    }


@transaction.atomic
def publish_version(
    municipality,
    kind,
    model,
    *,
    responsible,
    dpo,
    address,
    adapted=None,
    substantial=True,
    reviewed=False,
    by=None,
):
    """Publica unha versión. `adapted` = {title_gl, title_es, body_gl, body_es} se o concello
    adapta o texto; se non, adóptase tal cal. Sempre se enchen os datos do concello."""
    if not (responsible and dpo and address):
        raise LegalError(_("Cubre a persoa responsable, o DPD e o enderezo."))
    document, _created = LegalDocument.objects.get_or_create(municipality=municipality, kind=kind)
    last = document.current
    source = adapted or {
        "title_gl": model.title_gl,
        "title_es": model.title_es,
        "body_gl": model.body_gl,
        "body_es": model.body_es,
    }
    texts = {
        key: fill(
            value, responsible=responsible, dpo=dpo, address=address, municipality=municipality
        )
        for key, value in source.items()
    }
    is_adapted = adapted is not None
    version = LegalVersion.objects.create(
        municipality=municipality,
        document=document,
        number=(last.number + 1) if last else 1,
        source_model=model,
        mode=LegalVersion.Mode.ADAPTED if is_adapted else LegalVersion.Mode.AS_IS,
        # A primeira versión sempre se pide aceptar
        substantial=substantial or last is None,
        is_example=not (is_adapted and reviewed),
        reviewed_by=by if (is_adapted and reviewed) else None,
        published_by=by,
        **texts,
    )
    audit(
        "legal.version_publish",
        by,
        municipality,
        version,
        kind=kind,
        number=version.number,
        substantial=version.substantial,
    )
    return version


def concello_rows(municipality):
    """Estado de cada documento para a xestión do concello."""
    rows = []
    documents = {d.kind: d for d in LegalDocument.objects.filter(municipality=municipality)}
    for kind in DocKind:
        document = documents.get(kind)
        current = document.current if document else None
        model = latest_model(municipality.region, kind)
        rows.append(
            {
                "kind": kind,
                "document": document,
                "current": current,
                "model": model,
                "new_model": bool(current and current.source_model_id != model.pk),
                "accepted": LegalAcceptance.objects.filter(
                    version=current, withdrawn_at__isnull=True
                ).count()
                if current
                else 0,
            }
        )
    return rows


# ------------------------------------------------------------------ aceptación
def _applies(kind, user):
    if kind in REQUIRED:
        return True
    if kind == DocKind.MINORS:
        household = getattr(user, "household", None)
        return bool(household and household.dependents.exists())
    return False


def _last_substantial(document):
    return document.versions.filter(substantial=True).order_by("-number").first()


def status_for(user, document):
    """accepted | pending | withdrawn | optional para a versión vixente deste documento."""
    required_from = _last_substantial(document)
    mine = LegalAcceptance.objects.filter(user=user, version__document=document).select_related(
        "version"
    )
    active = [a for a in mine if a.withdrawn_at is None]
    if required_from and any(a.version.number >= required_from.number for a in active):
        return "accepted"
    if active:
        return "pending"  # aceptou unha versión anterior e houbo cambios substanciais
    if any(a.withdrawn_at for a in mine) and document.kind in REVOCABLE:
        return "withdrawn"
    return "pending" if _applies(document.kind, user) else "optional"


def pending_versions(user, municipality):
    """Versións que as apps teñen que mostrar para aceptar."""
    if not getattr(user, "is_authenticated", False) or municipality is None:
        return []
    out = []
    for document in LegalDocument.objects.filter(municipality=municipality):
        current = document.current
        if current and status_for(user, document) == "pending":
            out.append(current)
    return out


def accept(user, version, channel=LegalAcceptance.Channel.APP):
    acceptance = LegalAcceptance.objects.filter(
        user=user, version=version, withdrawn_at__isnull=True
    ).first()
    if acceptance:
        return acceptance
    acceptance = LegalAcceptance.objects.create(
        municipality=version.municipality, user=user, version=version, channel=channel
    )
    if version.document.kind == DocKind.IMAGE and not user.photo_consent:
        user.photo_consent = True
        user.photo_consent_at = timezone.now()
        user.save(update_fields=["photo_consent", "photo_consent_at"])
    audit(
        "legal.accept",
        user,
        version.municipality,
        version,
        kind=version.document.kind,
        number=version.number,
        channel=channel,
    )
    return acceptance


def withdraw(acceptance, by):
    """Retira un consentimento revogable e aplica o seu efecto. Non borra o rexistro."""
    kind = acceptance.version.document.kind
    if kind not in REVOCABLE:
        raise LegalError(_("Este documento non é un consentimento que se poida retirar."))
    now = timezone.now()
    LegalAcceptance.objects.filter(
        user=acceptance.user,
        version__document=acceptance.version.document,
        withdrawn_at__isnull=True,
    ).update(withdrawn_at=now)
    user = acceptance.user
    if kind == DocKind.IMAGE and user.photo_consent:
        user.photo_consent = False
        user.photo_consent_at = None
        user.save(update_fields=["photo_consent", "photo_consent_at"])
    elif kind == DocKind.HEALTH:
        from apps.accounts.models import HealthProfile

        HealthProfile.objects.filter(user=user).delete()
    audit(
        "legal.withdraw",
        by,
        acceptance.municipality,
        acceptance.version,
        kind=kind,
        number=acceptance.version.number,
    )


def sync_photo_withdrawal(user):
    """O interruptor de imaxe do centro de privacidade tamén retira a aceptación rexistrada."""
    LegalAcceptance.objects.filter(
        user=user, version__document__kind=DocKind.IMAGE, withdrawn_at__isnull=True
    ).update(withdrawn_at=timezone.now())


def history(user):
    return (
        LegalAcceptance.objects.filter(user=user)
        .select_related("version__document", "municipality")
        .order_by("-accepted_at")
    )


# ------------------------------------------------------------------ rexistro para o concello
REGISTER_HEADER = ["persoa", "correo", "documento", "versión", "data", "canle", "retirada"]


def csv_safe(value):
    """Evita que unha folla de cálculo interprete un nome como fórmula."""
    text = str(value or "")
    return f"'{text}" if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def register_rows(municipality):
    rows = (
        LegalAcceptance.objects.filter(municipality=municipality)
        .select_related("user", "version__document")
        .order_by("accepted_at", "pk")
    )
    for a in rows:
        yield [
            csv_safe(a.user.display_name) if a.user else _("(conta eliminada)"),
            csv_safe(a.user.email) if a.user else "",
            a.version.document.get_kind_display(),
            a.version.number,
            timezone.localtime(a.accepted_at).strftime("%Y-%m-%d %H:%M"),
            a.get_channel_display(),
            timezone.localtime(a.withdrawn_at).strftime("%Y-%m-%d %H:%M") if a.withdrawn_at else "",
        ]
