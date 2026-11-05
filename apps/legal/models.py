# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · D: documentos legais versionados: deputación → concello → apps.

A deputación publica modelos no seu repositorio, cada concello adóptaos tal cal ou adáptaos cos
seus datos e, ao publicarse unha versión, as apps móstrana para aceptala. Cada aceptación queda
rexistrada (persoa, documento, versión, data e canle) para xustificar o consentimento."""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import Region, TenantModel


class DocKind(models.TextChoices):
    PRIVACY = "privacy", _("Información de privacidade")
    TERMS = "terms", _("Condicións de uso")
    MINORS = "minors", _("Consentimento para menores (persoa titora)")
    IMAGE = "image", _("Dereitos de imaxe")
    RULES = "rules", _("Normas de uso das instalacións")
    HEALTH = "health", _("Consentimento de datos de saúde")


# Ficheiro de docs/legal/modelos/ de cada tipo
MODEL_FILES = {
    DocKind.PRIVACY: "privacidade",
    DocKind.TERMS: "condicions",
    DocKind.MINORS: "menores",
    DocKind.IMAGE: "imaxe",
    DocKind.RULES: "normas",
    DocKind.HEALTH: "saude",
}
# Consentimentos que a persoa pode retirar. O resto son información ou condicións do servizo.
REVOCABLE = frozenset({DocKind.MINORS, DocKind.IMAGE, DocKind.HEALTH})
# Pídense a toda persoa usuaria. Os outros só cando lle atinxen ou se os aceptou antes.
REQUIRED = frozenset({DocKind.PRIVACY, DocKind.TERMS, DocKind.RULES})


class _Texts(models.Model):
    title_gl = models.CharField(_("título en galego"), max_length=160)
    title_es = models.CharField(_("título en castelán"), max_length=160)
    body_gl = models.TextField(_("texto en galego"))
    body_es = models.TextField(_("texto en castelán"))

    class Meta:
        abstract = True

    @property
    def title(self):
        return self.title_es if (get_language() or "").startswith("es") else self.title_gl

    @property
    def body(self):
        return self.body_es if (get_language() or "").startswith("es") else self.body_gl


class LegalModel(_Texts):
    """Modelo publicado por unha deputación. Sen `region` = modelo incluído en Eira."""

    region = models.ForeignKey(
        Region, null=True, blank=True, on_delete=models.CASCADE, related_name="legal_models"
    )
    kind = models.CharField(_("documento"), max_length=10, choices=DocKind.choices)
    version = models.PositiveIntegerField(default=1)
    substantial = models.BooleanField(_("cambios substanciais"), default=True)
    published_at = models.DateTimeField(default=timezone.now)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = _("modelo de documento legal")
        verbose_name_plural = _("modelos de documentos legais")
        ordering = ["kind", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["region", "kind", "version"], name="uniq_legal_model_version"
            )
        ]

    def __str__(self):
        return f"{self.get_kind_display()} · v{self.version}"


class LegalDocument(TenantModel):
    """Un documento dun concello (un por tipo), coas súas versións publicadas."""

    kind = models.CharField(_("documento"), max_length=10, choices=DocKind.choices)

    class Meta:
        verbose_name = _("documento legal")
        verbose_name_plural = _("documentos legais")
        ordering = ["kind"]
        constraints = [
            models.UniqueConstraint(fields=["municipality", "kind"], name="uniq_legal_document")
        ]

    def __str__(self):
        return self.get_kind_display()

    @property
    def revocable(self):
        return self.kind in REVOCABLE

    @property
    def current(self):
        return self.versions.order_by("-number").first()


class LegalVersion(_Texts, TenantModel):
    """Versión publicada. Inmutable: cada cambio crea unha versión nova."""

    class Mode(models.TextChoices):
        AS_IS = "as_is", _("Adoptado tal cal")
        ADAPTED = "adapted", _("Adaptado polo concello")

    document = models.ForeignKey(LegalDocument, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField()
    source_model = models.ForeignKey(
        LegalModel, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.AS_IS)
    # Con cambios substanciais pídese volver aceptar
    substantial = models.BooleanField(_("cambios substanciais"), default=True)
    # O aviso «MODELO DE EXEMPLO» só desaparece se o concello adapta o texto e declara que o revisou
    is_example = models.BooleanField(default=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    published_at = models.DateTimeField(default=timezone.now)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = _("versión de documento legal")
        verbose_name_plural = _("versións de documentos legais")
        ordering = ["document", "-number"]
        constraints = [
            models.UniqueConstraint(fields=["document", "number"], name="uniq_legal_version")
        ]

    def __str__(self):
        return f"{self.document} · v{self.number}"


class LegalAcceptance(TenantModel):
    """Rexistro de aceptación: persoa, documento, versión, data e canle.

    Ao eliminar a conta queda sen persoa, para que o rexistro siga cadrando sen datos persoais."""

    class Channel(models.TextChoices):
        APP = "app", _("App")
        WEB = "web", _("Web")
        COUNTER = "counter", _("Mostrador")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="legal_acceptances",
    )
    version = models.ForeignKey(LegalVersion, on_delete=models.CASCADE, related_name="acceptances")
    accepted_at = models.DateTimeField(default=timezone.now, db_index=True)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.APP)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("aceptación de documento legal")
        verbose_name_plural = _("aceptacións de documentos legais")
        ordering = ["-accepted_at"]

    def __str__(self):
        return f"{self.version} · {self.accepted_at:%d/%m/%Y}"

    @property
    def is_active(self):
        return self.withdrawn_at is None
