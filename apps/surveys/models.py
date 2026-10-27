# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · E: enquisa anual de satisfacción con NPS e pregunta NPS opcional despois de cada uso.

«Que tal foi?» (Ben/Regular/Mal) segue igual despois de cada uso; isto engádese.
Resultados só agregados e con n ≥ 10 (ver `services.py`)."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import TenantModel

# Aspectos que se valoran do 1 ao 5 (clave, etiqueta)
ASPECTS = (
    ("cleanliness", _("Limpeza")),
    ("state", _("Estado das instalacións")),
    ("schedule", _("Horarios")),
    ("price", _("Prezo")),
    ("booking", _("Facilidade para reservar")),
    ("accessibility", _("Accesibilidade")),
    ("attention", _("Atención")),
)
NPS_QUESTION = _("Do 0 ao 10, recomendarías os servizos deportivos do teu concello?")


class Survey(TenantModel):
    """Enquisa anual que lanza o concello cunha xanela de datas."""

    year = models.PositiveIntegerField(_("ano"))
    title = models.CharField(_("título"), max_length=120, blank=True)
    opens_on = models.DateField(_("abre o"))
    closes_on = models.DateField(_("pecha o"))
    announced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("enquisa anual")
        verbose_name_plural = _("enquisas anuais")
        ordering = ["-year", "-opens_on"]
        constraints = [
            models.UniqueConstraint(fields=["municipality", "year"], name="uniq_survey_year")
        ]

    def __str__(self):
        return self.title or str(_("Enquisa de satisfacción %(y)s") % {"y": self.year})

    def is_open(self, day=None):
        day = day or timezone.localdate()
        return self.opens_on <= day <= self.closes_on

    def is_closed(self, day=None):
        return (day or timezone.localdate()) > self.closes_on

    @property
    def label(self):
        return str(self)


def score_field(label):
    return models.PositiveSmallIntegerField(
        label,
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )


class SurveyResponse(models.Model):
    """Unha resposta por persoa e enquisa. Nunca se mostra quen respondeu."""

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="responses")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    nps = models.PositiveSmallIntegerField(
        NPS_QUESTION, validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    cleanliness = score_field(_("Limpeza"))
    state = score_field(_("Estado das instalacións"))
    schedule = score_field(_("Horarios"))
    price = score_field(_("Prezo"))
    booking = score_field(_("Facilidade para reservar"))
    accessibility = score_field(_("Accesibilidade"))
    attention = score_field(_("Atención"))
    facility = models.ForeignKey(
        "facilities.Facility",
        verbose_name=_("instalación que máis usas"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    comment = models.CharField(_("comentario (opcional)"), max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("resposta á enquisa")
        verbose_name_plural = _("respostas á enquisa")
        constraints = [
            models.UniqueConstraint(fields=["survey", "user"], name="uniq_survey_response")
        ]


class UseNps(TenantModel):
    """Pregunta NPS opcional despois de cada uso (desactivada por defecto en cada concello)."""

    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.CASCADE, related_name="use_nps"
    )
    facility = models.ForeignKey(
        "facilities.Facility", on_delete=models.CASCADE, related_name="use_nps"
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("NPS despois do uso")
        verbose_name_plural = _("NPS despois do uso")
