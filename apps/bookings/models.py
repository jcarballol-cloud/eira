# SPDX-License-Identifier: EUPL-1.2
"""Reservas: estados, pagamento, aceptación das normas, check-in e checklist de peche."""

import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.facilities.models import Facility, RulesVersion
from apps.tenants.models import TenantModel


def booking_reference():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


class BookingQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        return self.filter(municipality=tenant)

    def holding(self):
        """Reservas que ocupan praza: confirmadas, usadas ou pendentes de pago non caducadas."""
        now = timezone.now()
        return self.filter(
            models.Q(status__in=[Booking.Status.CONFIRMED, Booking.Status.USED])
            | models.Q(status=Booking.Status.PENDING_PAYMENT, hold_expires_at__gt=now)
        )

    def overlapping(self, start, end):
        return self.filter(start__lt=end, end__gt=start)


class Booking(TenantModel):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", _("Pendente de pagamento")
        CONFIRMED = "confirmed", _("Confirmada")
        CANCELLED = "cancelled", _("Cancelada")
        USED = "used", _("Usada")
        NO_SHOW = "no_show", _("Non presentada")

    class Channel(models.TextChoices):
        ONLINE = "online", _("En liña")
        PHONE = "phone", _("Teléfono")
        COUNTER = "counter", _("Mostrador")

    reference = models.CharField(
        max_length=8, unique=True, default=booking_reference, editable=False
    )
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="bookings")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bookings",
    )
    start = models.DateTimeField(_("inicio"), db_index=True)
    end = models.DateTimeField(_("fin"))
    status = models.CharField(
        _("estado"), max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT
    )
    channel = models.CharField(
        _("canle"), max_length=10, choices=Channel.choices, default=Channel.ONLINE
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Reserva no nome dunha persoa sen conta (teléfono ou mostrador): mínimo imprescindible
    holder_name = models.CharField(_("nome da persoa"), max_length=120, blank=True)
    holder_phone = models.CharField(_("teléfono de contacto"), max_length=20, blank=True)
    tariff_audience = models.CharField(max_length=20, blank=True)
    price_cents = models.PositiveIntegerField(default=0)
    paid_cents = models.PositiveIntegerField(default=0)
    refunded_cents = models.PositiveIntegerField(default=0)
    payment_reference = models.CharField(max_length=40, blank=True)
    hold_expires_at = models.DateTimeField(null=True, blank=True)
    rules_version = models.ForeignKey(RulesVersion, null=True, on_delete=models.PROTECT)
    rules_accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=200, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    # Checklist de peche
    closed_at = models.DateTimeField(null=True, blank=True)
    close_door_ok = models.BooleanField(null=True)
    close_key_ok = models.BooleanField(null=True)
    close_all_ok = models.BooleanField(null=True)
    close_notes = models.TextField(blank=True)

    objects = BookingQuerySet.as_manager()

    class Meta:
        verbose_name = _("reserva")
        verbose_name_plural = _("reservas")
        ordering = ["-start"]
        indexes = [
            models.Index(fields=["facility", "start"]),
            models.Index(fields=["municipality", "status"]),
        ]

    def __str__(self):
        return f"{self.reference} · {self.facility} · {self.start:%Y-%m-%d %H:%M}"

    @property
    def holder_label(self):
        if self.user:
            return str(self.user)
        return self.holder_name

    @property
    def is_active_now(self):
        now = timezone.now()
        return (
            self.status in (self.Status.CONFIRMED, self.Status.USED)
            and self.start <= now < self.end
        )

    @property
    def is_upcoming(self):
        return self.status == self.Status.CONFIRMED and self.start > timezone.now()

    @property
    def is_finished(self):
        return self.end <= timezone.now()

    @property
    def needs_closing_checklist(self):
        return (
            self.status in (self.Status.CONFIRMED, self.Status.USED)
            and self.closed_at is None
            and self.start <= timezone.now()
            and timezone.now() <= self.end + timezone.timedelta(hours=12)
        )

    @property
    def duration_minutes(self):
        return int((self.end - self.start).total_seconds() // 60)

    def cancellation_cutoff(self):
        return self.start - timezone.timedelta(hours=self.municipality.cancellation_hours)

    def can_modify(self):
        return self.status == self.Status.CONFIRMED and timezone.now() < self.cancellation_cutoff()

    def can_cancel(self):
        return (
            self.status in (self.Status.CONFIRMED, self.Status.PENDING_PAYMENT)
            and timezone.now() < self.start
        )

    def penalty_if_cancelled_now(self):
        if self.status != self.Status.CONFIRMED or timezone.now() < self.cancellation_cutoff():
            return 0
        return self.paid_cents * self.municipality.late_cancel_penalty_pct // 100
