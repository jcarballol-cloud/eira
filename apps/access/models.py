# SPDX-License-Identifier: EUPL-1.2
"""Dispositivos de acceso (niveis 2 e 3), eventos de acceso e entregas de chave (nivel 1)."""

import pyotp
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.facilities.models import Facility
from apps.tenants.models import TenantModel

from . import offline_codes


class LockDevice(TenantModel):
    class Kind(models.TextChoices):
        OFFLINE = "offline", _("Teclado con código sen conexión (nivel 2)")
        CONNECTED = "connected", _("Pechadura conectada (nivel 3)")

    facility = models.OneToOneField(Facility, on_delete=models.CASCADE, related_name="lock")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    label = models.CharField(_("identificador"), max_length=60, blank=True)
    secret = models.CharField(max_length=64, default=pyotp.random_base32, editable=False)
    step_minutes = models.PositiveIntegerField(default=30)
    tolerance_minutes = models.PositiveIntegerField(default=10)
    digits = models.PositiveSmallIntegerField(default=6)
    max_blocks = models.PositiveSmallIntegerField(default=8)
    controls_lights = models.BooleanField(_("controla as luces"), default=False)
    # Estado simulado do dispositivo
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    lights_on_until = models.DateTimeField(null=True, blank=True)

    MAX_FAILED = 5
    LOCKOUT_MINUTES = 5

    class Meta:
        verbose_name = _("dispositivo de acceso")
        verbose_name_plural = _("dispositivos de acceso")

    def __str__(self):
        return self.label or f"{self.facility} ({self.get_kind_display()})"

    @property
    def params(self):
        return offline_codes.CodeParams(
            secret=self.secret, step_minutes=self.step_minutes, tolerance_minutes=self.tolerance_minutes,
            digits=self.digits, max_blocks=self.max_blocks,
        )

    def code_for_booking(self, booking):
        return offline_codes.code_for(booking.start, booking.end, self.params)

    def lights_on(self, at=None):
        at = at or timezone.now()
        return bool(self.lights_on_until and self.lights_on_until > at)


class AccessEvent(TenantModel):
    class Kind(models.TextChoices):
        CHECKIN = "checkin", _("Entrada (QR)")
        CODE_OK = "code_ok", _("Código aceptado")
        CODE_DENIED = "code_denied", _("Código rexeitado")
        REMOTE_OPEN = "remote_open", _("Apertura remota")
        LIGHTS_ON = "lights_on", _("Luces acesas")
        LIGHTS_OFF = "lights_off", _("Luces apagadas")
        KEY_OUT = "key_out", _("Chave entregada")
        KEY_IN = "key_in", _("Chave devolta")
        ANONYMOUS_USE = "anonymous_use", _("Uso sen reserva rexistrado")

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="access_events")
    booking = models.ForeignKey("bookings.Booking", null=True, blank=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    at = models.DateTimeField(default=timezone.now, db_index=True)
    detail = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-at"]
        verbose_name = _("evento de acceso")
        verbose_name_plural = _("eventos de acceso")


class KeyHandover(TenantModel):
    booking = models.OneToOneField("bookings.Booking", on_delete=models.CASCADE, related_name="key_handover")
    handed_at = models.DateTimeField(null=True, blank=True)
    handed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    returned_at = models.DateTimeField(null=True, blank=True)
    returned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    custodian_notified_at = models.DateTimeField(null=True, blank=True)
