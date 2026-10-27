# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · H: abonos dos servizos deportivos municipais e carné municipal único.

- Tipos de abono configurables (xeral, mocidade, maiores, familiar…) con prezo, validez e desconto
  nas tarifas (súmase ás regras que xa existen: empadroamento, baixa demanda e luz).
- Carné dixital na app cun QR dinámico asinado que caduca en poucos minutos; carné imprimible en
  PDF accesible (tamaño tarxeta) cun QR estático que se pode revogar (versión)."""

import secrets

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import TenantModel


class PassType(TenantModel):
    class Kind(models.TextChoices):
        GENERAL = "general", _("Xeral")
        YOUTH = "youth", _("Mocidade")
        SENIOR = "senior", _("Maiores")
        FAMILY = "family", _("Familiar")
        OTHER = "other", _("Outro")

    name = models.CharField(_("nome"), max_length=120)
    kind = models.CharField(_("tipo"), max_length=10, choices=Kind.choices, default=Kind.GENERAL)
    price_cents = models.PositiveIntegerField(_("prezo (céntimos)"))
    valid_days = models.PositiveIntegerField(_("validez (días)"), default=365)
    discount_pct = models.PositiveSmallIntegerField(
        _("desconto nas tarifas (%)"),
        default=10,
        validators=[MaxValueValidator(100)],
        help_text=_(
            "Aplícase despois da tarifa (empadroada ou non) e do desconto de baixa demanda."
        ),
    )
    description = models.CharField(_("descrición"), max_length=200, blank=True)
    active = models.BooleanField(_("á venda"), default=True)

    class Meta:
        verbose_name = _("tipo de abono")
        verbose_name_plural = _("tipos de abono")
        ordering = ["price_cents", "name"]

    def __str__(self):
        return self.name


class SportsPass(TenantModel):
    """Condición de abonado/a: alta e renovación por TPV ou na oficina."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pendente de pagamento")
        ACTIVE = "active", _("Activo")
        EXPIRED = "expired", _("Caducado")
        CANCELLED = "cancelled", _("Anulado")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sports_passes"
    )
    type = models.ForeignKey(PassType, on_delete=models.CASCADE, related_name="passes")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    starts_on = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    price_cents = models.PositiveIntegerField(default=0)
    channel = models.CharField(max_length=10, default="online")  # online | office
    sold_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("abono")
        verbose_name_plural = _("abonos")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type} · {self.user}"

    def is_valid(self, day=None):
        day = day or timezone.localdate()
        return (
            self.status == self.Status.ACTIVE
            and self.starts_on is not None
            and self.starts_on <= day <= (self.expires_on or day)
        )


def card_number():
    return "".join(secrets.choice("0123456789") for _ in range(8))


class MemberCard(TenantModel):
    """Carné municipal: un por persoa e concello. A foto é opcional."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="member_cards"
    )
    number = models.CharField(_("número"), max_length=12, default=card_number)
    photo = models.ImageField(_("foto (opcional)"), upload_to="cards/", blank=True)
    version = models.PositiveIntegerField(default=1)  # súbese para anular o carné impreso
    external_id = models.CharField(
        _("carné xa existente do concello"),
        max_length=60,
        blank=True,
        help_text=_("Vinculado polo adaptador `municipal_card` (biblioteca, piscina…)."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("carné municipal")
        verbose_name_plural = _("carnés municipais")
        constraints = [
            models.UniqueConstraint(fields=["municipality", "user"], name="uniq_member_card"),
            models.UniqueConstraint(
                fields=["municipality", "number"], name="uniq_member_card_number"
            ),
        ]

    def __str__(self):
        return f"{self.municipality.initials}-{self.number}"

    @property
    def display_number(self):
        return f"{self.municipality.initials}-{self.number[:4]} {self.number[4:]}"
