# SPDX-License-Identifier: EUPL-1.2
"""Concellos (tenants) e agrupacións supramunicipais (deputacións, mancomunidades)."""

import datetime as dt
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
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
    # v1.2
    "open_games": True,
    "cards": True,
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
    # v1.3 · C: dobre factor obrigatorio para o persoal da deputación (configurable no admin técnico)
    require_2fa = models.BooleanField(
        _("esixir dobre factor ao persoal da agrupación"), default=False
    )

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
    # v1.5 · C: posición do concello na rede, para o mapa de procedencia
    latitude = models.DecimalField(
        _("latitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        _("lonxitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
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
    accessibility_statement = models.TextField(
        _("declaración de accesibilidade: texto propio do concello"),
        blank=True,
        help_text=_("Opcional. Engádese ao principio da declaración (modelo do RD 1112/2018)."),
    )
    # v1.5.1: declaración de accesibilidade (RD 1112/2018, art. 15): canle e reclamación do concello
    accessibility_unit = models.CharField(
        _("unidade responsable de accesibilidade"),
        max_length=200,
        blank=True,
        help_text=_("Quen recibe e trata as comunicacións, queixas e reclamacións."),
    )
    accessibility_email = models.EmailField(
        _("correo para accesibilidade"),
        blank=True,
        help_text=_("Baleiro = o correo de contacto do concello."),
    )
    accessibility_phone = models.CharField(
        _("teléfono para accesibilidade"),
        max_length=40,
        blank=True,
        help_text=_("Baleiro = o teléfono do concello."),
    )
    accessibility_complaint_url = models.URLField(
        _("ligazón para presentar reclamacións"),
        blank=True,
        help_text=_("Sede electrónica ou rexistro do concello."),
    )
    # v1.5.1: guía paso a paso de cada perfil (na demo sempre está activa)
    guided_tour = models.BooleanField(
        _("mostrar a guía paso a paso"),
        default=False,
        help_text=_(
            "A primeira vez que cada persoa entra na súa pantalla principal, unha guía curta "
            "explica as funcións. Sempre se pode abrir desde «?» → «Ver a guía»."
        ),
    )
    accessibility_reviewed_on = models.DateField(
        _("data da última revisión da declaración"),
        null=True,
        blank=True,
        help_text=_("Baleiro = a data da avaliación incluída con Eira."),
    )
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
    # v1.2 · A: rexistro de accidentes
    accident_retention_months = models.PositiveIntegerField(
        _("conservación do rexistro de accidentes (meses)"),
        default=24,
        help_text=_("Pasado este prazo, os rexistros pechados bórranse automaticamente."),
    )
    # v1.2 · B: escalado se non se confirma o peche
    close_reminder_minutes = models.PositiveIntegerField(
        _("primeiro recordatorio do peche (min despois do fin)"), default=10
    )
    close_second_minutes = models.PositiveIntegerField(
        _("segundo recordatorio (min despois do primeiro)"), default=10
    )
    close_escalate_minutes = models.PositiveIntegerField(
        _("aviso á persoa responsable (min despois do segundo)"), default=10
    )
    police_phone = models.CharField(
        _("teléfono da Policía Local"),
        max_length=20,
        blank=True,
        help_text=_("Só aparece como botón para que decida unha persoa. Nunca se chama soa."),
    )
    close_breach_enabled = models.BooleanField(
        _("o peche sen confirmar conta como incumprimento"),
        default=False,
        help_text=_("Desactivado por defecto. Queda anotado na reserva igualmente."),
    )
    # v1.2 · E: NPS opcional despois de cada uso (desactivado para non cansar)
    nps_after_use = models.BooleanField(_("preguntar o NPS despois de cada uso"), default=False)
    # v1.2 · F: confirmación de asistencia e lista de espera nas reservas
    confirm_release_enabled = models.BooleanField(
        _("liberar as reservas sen confirmar"),
        default=False,
        help_text=_("Se hai lista de espera e a persoa non confirmou a tempo, a franxa ofrécese."),
    )
    confirm_release_minutes = models.PositiveIntegerField(
        _("prazo para confirmar (min antes do inicio)"), default=120
    )
    waitlist_offer_minutes = models.PositiveIntegerField(
        _("tempo para aceptar unha praza liberada (min)"), default=30
    )
    checkin_release_minutes = models.PositiveIntegerField(
        _("liberar sen check-in (min despois do inicio)"),
        default=15,
        help_text=_("Só nos niveis 0, 2 e 3 e só se hai alguén na lista de espera."),
    )
    # v1.2 · D: rendemento (estimación orientativa)
    energy_price_eur_kwh = models.DecimalField(
        _("prezo da enerxía (€/kWh)"), max_digits=6, decimal_places=4, default=Decimal("0.1800")
    )
    co2_kg_kwh = models.DecimalField(
        _("factor de emisión (kg CO₂/kWh)"),
        max_digits=5,
        decimal_places=3,
        default=Decimal("0.150"),
        help_text=_("Factor orientativo do mix eléctrico. Cámbiao polo da túa comercializadora."),
    )
    # v1.3 · C: dobre factor (TOTP) obrigatorio para a administración e o DPD do concello
    require_2fa_admin = models.BooleanField(
        _("esixir dobre factor á administración e ao DPD"),
        default=False,
        help_text=_(
            "Quen teña eses roles terá que activar unha app de códigos (TOTP) antes de entrar na "
            "xestión. Para o resto de persoas é opcional."
        ),
    )
    # v1.4 · A1: prazo de conservación do rexistro de auditoría (purga en booking_maintenance)
    audit_retention_months = models.PositiveSmallIntegerField(
        _("conservación do rexistro de auditoría (meses)"),
        default=24,
        validators=[MinValueValidator(12), MaxValueValidator(120)],
        help_text=_(
            "As entradas máis antigas bórranse automaticamente. Entre 12 e 120 meses; por "
            "defecto, 2 anos."
        ),
    )
    # v1.5 · E: revisión da acreditación das persoas que traballan con menores
    accreditation_review_months = models.PositiveSmallIntegerField(
        _("revisión da acreditación para actividades con menores (meses)"),
        default=12,
        validators=[MinValueValidator(1), MaxValueValidator(60)],
        help_text=_(
            "Pasado este prazo, o concello recibe un aviso para volver confirmala. Por defecto, cada ano."
        ),
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
