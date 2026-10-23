# SPDX-License-Identifier: EUPL-1.2
"""Instalacións, horarios, peches, tarifas e normas versionadas."""

import secrets

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import TenantModel


class Parish(TenantModel):
    name = models.CharField(_("nome"), max_length=80)

    class Meta:
        verbose_name = _("parroquia")
        verbose_name_plural = _("parroquias")
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["municipality", "name"], name="uniq_parish")]

    def __str__(self):
        return self.name


class FacilityKind(models.TextChoices):
    OUTDOOR_COURT = "outdoor_court", _("Pista exterior")
    SPORTS_HALL = "sports_hall", _("Pavillón")
    GRASS_FIELD = "grass_field", _("Campo de herba")
    GYM = "gym", _("Ximnasio")
    POOL = "pool", _("Piscina")
    PADEL = "padel", _("Pista de pádel")
    OTHER = "other", _("Outra")


class AccessLevel(models.IntegerChoices):
    OPEN = 0, _("Aberta (QR de entrada)")
    CUSTODIAN = 1, _("Chave custodiada")
    OFFLINE_CODE = 2, _("Código temporal sen conexión")
    CONNECTED = 3, _("Pechadura conectada")


def new_token():
    return secrets.token_urlsafe(16)


class Facility(TenantModel):
    name = models.CharField(_("nome"), max_length=120)
    kind = models.CharField(_("tipo"), max_length=20, choices=FacilityKind.choices)
    parish = models.ForeignKey(
        Parish, verbose_name=_("parroquia"), null=True, blank=True, on_delete=models.SET_NULL
    )
    description = models.TextField(_("descrición"), blank=True)
    address = models.CharField(_("enderezo"), max_length=200, blank=True)
    latitude = models.DecimalField(
        _("latitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        _("lonxitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    photo = models.ImageField(_("foto"), upload_to="facilities/", blank=True)
    photo_alt = models.CharField(_("texto alternativo da foto"), max_length=200, blank=True)
    indoor = models.BooleanField(_("cuberta"), default=False)
    lighting = models.BooleanField(_("iluminación"), default=False)
    # Accesibilidade física
    step_free = models.BooleanField(_("acceso sen chanzos"), default=False)
    adapted_toilet = models.BooleanField(_("aseo adaptado"), default=False)
    adapted_changing = models.BooleanField(_("vestiario adaptado"), default=False)
    accessible_parking = models.BooleanField(_("aparcadoiro reservado"), default=False)
    accessibility_notes = models.TextField(_("notas de accesibilidade"), blank=True)
    capacity = models.PositiveIntegerField(
        _("prazas simultáneas"),
        default=1,
        help_text=_("1 = uso exclusivo (pista). Máis de 1 = uso compartido (ximnasio, piscina)."),
    )
    slot_minutes = models.PositiveIntegerField(_("duración da franxa (min)"), default=60)
    access_level = models.IntegerField(
        _("nivel de acceso"), choices=AccessLevel.choices, default=AccessLevel.OPEN
    )
    # Nivel 1: chave custodiada
    key_holder_name = models.CharField(_("custodia da chave"), max_length=120, blank=True)
    key_holder_place = models.CharField(_("onde se recolle"), max_length=200, blank=True)
    key_holder_hours = models.CharField(_("horario de recollida"), max_length=120, blank=True)
    key_holder_phone = models.CharField(_("teléfono da custodia"), max_length=20, blank=True)
    key_holder_email = models.EmailField(_("correo da custodia"), blank=True)
    # Nivel 0: QR fixo de entrada
    checkin_token = models.CharField(max_length=32, default=new_token, unique=True, editable=False)
    is_published = models.BooleanField(_("publicada"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("instalación")
        verbose_name_plural = _("instalacións")
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_shared(self):
        return self.capacity > 1

    def current_rules(self):
        return self.rules_versions.order_by("-version").first()

    def accessibility_features(self):
        labels = []
        for field in ("step_free", "adapted_toilet", "adapted_changing", "accessible_parking"):
            if getattr(self, field):
                labels.append(self._meta.get_field(field).verbose_name)
        return labels


class Weekday(models.IntegerChoices):
    MON = 0, _("Luns")
    TUE = 1, _("Martes")
    WED = 2, _("Mércores")
    THU = 3, _("Xoves")
    FRI = 4, _("Venres")
    SAT = 5, _("Sábado")
    SUN = 6, _("Domingo")


class OpeningHours(models.Model):
    """Franxas de apertura por día da semana, opcionalmente limitadas a unha tempada."""

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="opening_hours")
    weekday = models.IntegerField(_("día"), choices=Weekday.choices)
    opens = models.TimeField(_("abre"))
    closes = models.TimeField(_("pecha"))
    season_start = models.DateField(_("inicio de tempada"), null=True, blank=True)
    season_end = models.DateField(_("fin de tempada"), null=True, blank=True)

    class Meta:
        verbose_name = _("horario")
        verbose_name_plural = _("horarios")
        ordering = ["weekday", "opens"]

    def applies_on(self, day):
        if self.season_start and day < self.season_start:
            return False
        return not (self.season_end and day > self.season_end)


class Closure(TenantModel):
    """Festivo, evento, obra ou alerta meteorolóxica. Sen instalación = todo o concello."""

    class Kind(models.TextChoices):
        HOLIDAY = "holiday", _("Festivo")
        EVENT = "event", _("Evento")
        WORKS = "works", _("Obras")
        WEATHER = "weather", _("Alerta meteorolóxica")
        OTHER = "other", _("Outro")

    facility = models.ForeignKey(
        Facility,
        verbose_name=_("instalación"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="closures",
    )
    kind = models.CharField(_("motivo"), max_length=20, choices=Kind.choices, default=Kind.OTHER)
    reason = models.CharField(_("descrición"), max_length=200)
    starts_at = models.DateTimeField(_("desde"))
    ends_at = models.DateTimeField(_("ata"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("peche ou bloqueo")
        verbose_name_plural = _("peches e bloqueos")
        ordering = ["starts_at"]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.reason}"


class Tariff(models.Model):
    class Audience(models.TextChoices):
        RESIDENT = "resident", _("Persoas empadroadas")
        NON_RESIDENT = "non_resident", _("Persoas non empadroadas")
        YOUTH = "youth", _("Mocidade (ata 25 anos, empadroada)")
        SENIOR = "senior", _("Maiores de 65 (empadroadas)")
        REDUCED = "reduced", _("Colectivos con tarifa reducida (validado polo concello)")

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="tariffs")
    audience = models.CharField(_("colectivo"), max_length=20, choices=Audience.choices)
    price_cents = models.PositiveIntegerField(_("prezo por franxa (céntimos)"))

    class Meta:
        verbose_name = _("tarifa")
        verbose_name_plural = _("tarifas")
        constraints = [models.UniqueConstraint(fields=["facility", "audience"], name="uniq_tariff")]


class RulesVersion(models.Model):
    """Normas de uso, dereitos e deberes. Inmutables: cada cambio crea unha versión nova."""

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="rules_versions")
    version = models.PositiveIntegerField()
    text = models.TextField(_("normas"))
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = _("versión das normas")
        verbose_name_plural = _("versións das normas")
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["facility", "version"], name="uniq_rules_version")
        ]

    def __str__(self):
        return f"v{self.version}"

    @classmethod
    def publish(cls, facility, text, user=None):
        last = cls.objects.filter(facility=facility).order_by("-version").first()
        if last and last.text.strip() == text.strip():
            return last
        return cls.objects.create(
            facility=facility, version=(last.version + 1 if last else 1), text=text, created_by=user
        )

    def lines(self):
        return [line.strip("-• ").strip() for line in self.text.splitlines() if line.strip()]
