# SPDX-License-Identifier: EUPL-1.2
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.facilities.models import Facility
from apps.tenants.models import TenantModel


class Incident(TenantModel):
    class Status(models.TextChoices):
        RECEIVED = "received", _("Recibida")
        VALIDATED = "validated", _("Validada")
        WORK_ORDER = "work_order", _("Orde de traballo creada")
        RESOLVED = "resolved", _("Resolta")
        REJECTED = "rejected", _("Descartada")

    class Source(models.TextChoices):
        CITIZEN = "citizen", _("Veciñanza")
        CHECKLIST = "checklist", _("Checklist de peche")
        STAFF = "staff", _("Persoal municipal")
        START_STATE = "start_state", _("Estado ao entrar (xa estaba antes da reserva)")
        RISK = "risk", _("Aviso de risco")
        ALERT = "alert", _("Alerta (accidente ou emerxencia)")  # v1.2

    class Priority(models.TextChoices):
        NORMAL = "normal", _("Normal")
        HIGH = "high", _("Alta")
        URGENT = "urgent", _("Máxima")  # v1.2: alertas

    class Category(models.TextChoices):
        DAMAGE = "damage", _("Desperfecto")
        CLEANING = "cleaning", _("Limpeza")
        LIGHTING = "lighting", _("Iluminación")
        ACCESS = "access", _("Porta ou pechadura")
        WATER = "water", _("Auga ou duchas")
        SAFETY = "safety", _("Seguridade")
        OTHER = "other", _("Outra")

    facility = models.ForeignKey(
        Facility, verbose_name=_("instalación"), on_delete=models.CASCADE, related_name="incidents"
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="incidents",
    )
    booking = models.ForeignKey(
        "bookings.Booking", null=True, blank=True, on_delete=models.SET_NULL
    )
    category = models.CharField(
        _("tipo"), max_length=20, choices=Category.choices, default=Category.OTHER
    )
    description = models.TextField(_("que pasou?"))
    photo = models.ImageField(_("foto"), upload_to="incidents/%Y/%m/", blank=True)
    status = models.CharField(
        _("estado"), max_length=20, choices=Status.choices, default=Status.RECEIVED
    )
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.CITIZEN)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(_("nota de resolución"), blank=True)
    # v5
    priority = models.CharField(
        _("prioridade"), max_length=10, choices=Priority.choices, default=Priority.NORMAL
    )
    prior_to_booking = models.ForeignKey(
        "bookings.Booking",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="found_on_start",
        help_text=_(
            "Detectada ao comezar esta reserva: xa estaba antes e non é responsabilidade súa."
        ),
    )

    class Meta:
        verbose_name = _("incidencia")
        verbose_name_plural = _("incidencias")
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} {self.facility}: {self.get_category_display()}"

    STEPS = [Status.RECEIVED, Status.VALIDATED, Status.WORK_ORDER, Status.RESOLVED]

    def step_index(self):
        try:
            return self.STEPS.index(self.status)
        except ValueError:
            return -1
