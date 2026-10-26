# SPDX-License-Identifier: EUPL-1.2
"""Concellos (tenants) e agrupacións supramunicipais (deputacións, mancomunidades)."""

import datetime as dt

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

hex_color = RegexValidator(r"^#[0-9A-Fa-f]{6}$", _("Cor en formato #RRGGBB."))

# Módulos que un concello pode activar ou desactivar (feature flags por concello).
DEFAULT_MODULES = {
    "bookings": True,
    "access": True,
    "incidents": True,
    "maintenance": True,
    "activities": True,
    "monitor": True,
    "observatory": True,
    "weather": True,
    "health": True,
    "ai_summary": False,
    "opendata": True,
}


def default_modules():
    return dict(DEFAULT_MODULES)


class PaymentMethod(models.TextChoices):
    """v5: formas de pagamento dunha reserva, configurables por concello e por instalación."""

    TPV = "tpv", _("TPV en liña")
    OFFICE = "office", _("Pagamento na oficina")
    FREE = "free", _("Gratuíta")
    VOUCHER = "voucher", _("Bono")
    DEFERRED = "deferred", _("Aprazado")


def default_payment_methods():
    # Como ata a v4: só TPV. O aprazado vai sempre desactivado por defecto.
    return [PaymentMethod.TPV.value]


class LightingRule(models.TextChoices):
    SUNSET = "sunset", _("Segundo a hora do solpor e do amencer")
    FIXED = "fixed", _("Horario fixo do concello")


class Region(models.Model):
    class Kind(models.TextChoices):
        PROVINCE = "province", _("Deputación provincial")
        MANCOMUNIDADE = "mancomunidade", _("Mancomunidade")
        OTHER = "other", _("Outra agrupación")

    name = models.CharField(_("nome"), max_length=120)
    slug = models.SlugField(unique=True)
    kind = models.CharField(_("tipo"), max_length=20, choices=Kind.choices, default=Kind.PROVINCE)

    class Meta:
        verbose_name = _("agrupación supramunicipal")
        verbose_name_plural = _("agrupacións supramunicipais")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Municipality(models.Model):
    name = models.CharField(_("nome"), max_length=120)
    slug = models.SlugField(unique=True, help_text=_("Identificador na URL: /c/<slug>/"))
    region = models.ForeignKey(
        Region,
        verbose_name=_("agrupación"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="municipalities",
    )
    ine_code = models.CharField(_("código INE"), max_length=5, blank=True)
    accent_color = models.CharField(
        _("cor de acento"), max_length=7, default="#2E6A4F", validators=[hex_color]
    )
    coat_of_arms = models.ImageField(_("escudo"), upload_to="tenants/coats/", blank=True)
    languages = models.CharField(_("idiomas"), max_length=40, default="gl,es")
    domain = models.CharField(
        _("dominio propio"),
        max_length=190,
        blank=True,
        null=True,
        unique=True,
        help_text=_("Opcional: p. ex. deportes.concello.example"),
    )
    contact_email = models.EmailField(_("correo de contacto"), blank=True)
    contact_phone = models.CharField(_("teléfono de contacto"), max_length=20, blank=True)
    telegram_channel = models.CharField(
        _("canle pública de Telegram"),
        max_length=60,
        blank=True,
        help_text=_("Nome da canle, p. ex. @deportesvilardeiras. Opcional."),
    )
    address = models.CharField(_("enderezo"), max_length=200, blank=True)
    population = models.PositiveIntegerField(_("poboación"), null=True, blank=True)
    postcodes = models.CharField(
        _("códigos postais do termo"),
        max_length=120,
        blank=True,
        help_text=_(
            "Separados por comas. Informativo: as altas automáticas usan o padrón cargado en CSV."
        ),
    )
    privacy_text = models.TextField(_("texto de privacidade"), blank=True)
    dpo_contact = models.CharField(
        _("contacto da persoa delegada de protección de datos"),
        max_length=200,
        blank=True,
        help_text=_(
            "Correo ou enderezo do DPD do concello (ou da deputación que presta o servizo)."
        ),
    )
    accessibility_statement = models.TextField(_("declaración de accesibilidade"), blank=True)
    legal_notice = models.TextField(_("aviso legal"), blank=True)
    modules = models.JSONField(_("módulos activos"), default=default_modules)
    tile_url = models.CharField(
        _("servidor de teselas do mapa"),
        max_length=300,
        blank=True,
        help_text=_(
            "Baleiro = o da instalación (EIRA_TILE_URL). P. ex. o servidor propio da deputación."
        ),
    )
    tile_attribution = models.CharField(_("atribución do mapa"), max_length=200, blank=True)
    tile_attribution_url = models.URLField(_("ligazón da atribución"), blank=True)

    # Regras de reserva configurables por concello
    cancellation_hours = models.PositiveIntegerField(
        _("horas mínimas para cancelar sen penalización"), default=24
    )
    late_cancel_penalty_pct = models.PositiveIntegerField(
        _("penalización por cancelación tardía (%)"), default=50
    )
    max_advance_days = models.PositiveIntegerField(_("días máximos de antelación"), default=14)
    max_active_bookings = models.PositiveIntegerField(
        _("reservas activas máximas por persoa"), default=4
    )
    low_demand_discount_pct = models.PositiveIntegerField(
        _("desconto nas franxas de baixa demanda (%)"),
        default=20,
        help_text=_("Aplícase ás franxas recomendadas (★). 0 = sen desconto."),
    )
    no_show_grace_minutes = models.PositiveIntegerField(
        _("minutos de cortesía para non presentado"), default=15
    )
    # v5 · Formas de pagamento (cada instalación pode restrinxilas)
    payment_methods = models.JSONField(
        _("formas de pagamento"), default=default_payment_methods, blank=True
    )
    office_payment_hours = models.PositiveIntegerField(
        _("prazo para pagar na oficina (horas)"),
        default=48,
        help_text=_("Se non se paga nese prazo (nin antes do inicio), a franxa queda libre."),
    )
    # v5 · Suplemento de iluminación
    lighting_rule = models.CharField(
        _("cando se precisa luz"),
        max_length=10,
        choices=LightingRule.choices,
        default=LightingRule.SUNSET,
    )
    lighting_from = models.TimeField(_("luz desde (horario fixo)"), default=dt.time(21, 0))
    lighting_until = models.TimeField(_("luz ata (horario fixo, pola mañá)"), default=dt.time(8, 0))
    # v5 · Reservas desde outros concellos da mesma rede (deputación ou mancomunidade)
    network_open = models.BooleanField(
        _("abrir as instalacións ás persoas doutros concellos da rede"),
        default=True,
        help_text=_(
            "Poden reservar coa súa conta, pagando a tarifa de persoas non empadroadas deste concello."
        ),
    )
    network_max_active = models.PositiveIntegerField(
        _("reservas activas máximas por persoa doutro concello"), default=2
    )
    network_advance_days = models.PositiveIntegerField(
        _("antelación máxima para persoas doutros concellos (días)"),
        null=True,
        blank=True,
        help_text=_("Baleiro = a mesma ca para a veciñanza."),
    )
    # v5 · Índice de vida activa: pesos de cada compoñente (ver docs/indice-vida-activa.md)
    vitality_weights = models.JSONField(
        _("pesos do índice de vida activa"), default=dict, blank=True
    )
    is_active = models.BooleanField(_("activo"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("concello")
        verbose_name_plural = _("concellos")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def payment_method_list(self):
        values = [m for m in (self.payment_methods or []) if m in PaymentMethod.values]
        return values or default_payment_methods()

    def module_enabled(self, key):
        return bool({**DEFAULT_MODULES, **(self.modules or {})}.get(key, False))

    @property
    def language_list(self):
        return [code.strip() for code in self.languages.split(",") if code.strip()]

    @property
    def initials(self):
        words = [w for w in self.name.split() if len(w) > 2] or self.name.split()
        return "".join(w[0] for w in words[:2]).upper()


class TenantQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        return self.filter(municipality=tenant)


class TenantModel(models.Model):
    """Base para todo dato que pertence a un concello. Illamento: filtrar sempre por `municipality`."""

    municipality = models.ForeignKey(
        Municipality, verbose_name=_("concello"), on_delete=models.CASCADE
    )

    objects = TenantQuerySet.as_manager()

    class Meta:
        abstract = True


def tile_settings(tenant=None):
    """Provedor de teselas efectivo (concello → instancia) e a súa orixe para a CSP."""
    from urllib.parse import urlparse

    from django.conf import settings

    url = tenant.tile_url if tenant and tenant.tile_url else settings.EIRA_TILE_URL
    parsed = urlparse(url.replace("{s}.", "a."))
    host = parsed.netloc.replace("a.", "*.", 1) if "{s}." in url else parsed.netloc
    return {
        "url": url,
        "origin": f"{parsed.scheme}://{host}",
        "attribution": (
            tenant.tile_attribution
            if tenant and tenant.tile_attribution
            else settings.EIRA_TILE_ATTRIBUTION
        ),
        "attribution_url": (
            tenant.tile_attribution_url
            if tenant and tenant.tile_attribution_url
            else settings.EIRA_TILE_ATTRIBUTION_URL
        ),
    }


def contrast_ratio(hex_a, hex_b):
    """Razón de contraste WCAG 2.x entre dúas cores #RRGGBB."""

    def luminance(hex_color):
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return 0.0
        channels = []
        for i in (0, 2, 4):
            c = int(h[i : i + 2], 16) / 255
            channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
        r, g, b = channels
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    la, lb = sorted((luminance(hex_a), luminance(hex_b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class SupportAccess(models.Model):
    """Acceso de soporte da deputación aos datos persoais dun concello.

    Por defecto a deputación só ve datos agregados ou anónimos. O concello autoriza o acceso,
    que caduca ás 24 h (ou antes, se o revoga). Cada páxina vista queda en AuditLog e o
    concello recibe un aviso no primeiro uso."""

    DURATION = timezone.timedelta(hours=24)

    municipality = models.ForeignKey(
        Municipality, on_delete=models.CASCADE, related_name="support_accesses"
    )
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="support_accesses")
    reason = models.CharField(_("motivo"), max_length=200)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    granted_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    first_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("acceso de soporte da deputación")
        verbose_name_plural = _("accesos de soporte da deputación")
        ordering = ["-granted_at"]

    @classmethod
    def active_for(cls, municipality, region_ids):
        return (
            cls.objects.filter(
                municipality=municipality,
                region_id__in=region_ids,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .order_by("-expires_at")
            .first()
        )

    @property
    def is_active(self):
        return self.revoked_at is None and self.expires_at > timezone.now()
