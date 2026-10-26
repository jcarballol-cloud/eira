# SPDX-License-Identifier: EUPL-1.2
"""Reservas: estados, pagamento, aceptación das normas, check-in e checklist de peche."""

import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.facilities.models import Facility, RulesVersion
from apps.tenants.models import PaymentMethod, TenantModel


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
            models.Q(
                status__in=[
                    Booking.Status.CONFIRMED,
                    Booking.Status.USED,
                    Booking.Status.PENDING_APPROVAL,
                ]
            )
            | models.Q(
                status__in=[Booking.Status.PENDING_PAYMENT, Booking.Status.PENDING_OFFICE],
                hold_expires_at__gt=now,
            )
        )

    def overlapping(self, start, end):
        return self.filter(start__lt=end, end__gt=start)


class Booking(TenantModel):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", _("Pendente de pagamento")
        CONFIRMED = "confirmed", _("Confirmada")
        REJECTED = "rejected", _("Pagamento rexeitado")
        EXPIRED = "expired", _("Caducada sen pagar")
        CANCELLED = "cancelled", _("Cancelada")
        USED = "used", _("Usada")
        NO_SHOW = "no_show", _("Non presentada")
        # v5
        PENDING_APPROVAL = "pending_approval", _("Pendente de aprobación")
        PENDING_OFFICE = "pending_office", _("Pendente de pagamento na oficina")
        DECLINED = "declined", _("Rexeitada polo concello")

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
    base_price_cents = models.PositiveIntegerField(default=0)  # antes do desconto
    discount_pct = models.PositiveSmallIntegerField(default=0)  # franxa de baixa demanda
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
    # v5 · Participantes
    participants = models.PositiveIntegerField(_("número de persoas"), default=1)
    participant_names = models.TextField(_("nomes (opcional)"), blank=True)
    # v5 · Forma de pagamento, bono e suplemento de luz
    payment_method = models.CharField(
        _("forma de pagamento"), max_length=10, choices=PaymentMethod.choices, default="tpv"
    )
    voucher = models.ForeignKey(
        "Voucher", null=True, blank=True, on_delete=models.SET_NULL, related_name="bookings"
    )
    lighting_cents = models.PositiveIntegerField(default=0)
    needs_light = models.BooleanField(_("pediu luz"), default=False)
    # v5 · Aprobación do concello
    approved_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decision_reason = models.CharField(_("motivo"), max_length=300, blank=True)
    requested_start = models.DateTimeField(null=True, blank=True)  # cambio pendente de aprobar
    # v5 · Reserva desde outro concello da rede: concello de orixe da persoa (só o nome se mostra)
    network_origin = models.ForeignKey(
        "tenants.Municipality", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # v5 · Estado ao entrar (o de saída é o checklist de peche)
    start_state_at = models.DateTimeField(null=True, blank=True)
    start_state_ok = models.BooleanField(null=True)
    start_state_notes = models.CharField(max_length=500, blank=True)
    start_state_photo = models.ImageField(upload_to="incidents/%Y/%m/", blank=True)

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
            if self.network_origin_id and not self.user.display_name:
                # v5: o concello de destino non ve o correo dunha persoa doutro concello
                return _("Persoa de %(c)s") % {"c": self.network_origin.name}
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
        return (
            self.status in (self.Status.CONFIRMED, self.Status.PENDING_APPROVAL)
            and self.requested_start is None
            and timezone.now() < self.cancellation_cutoff()
        )

    def can_cancel(self):
        return self.status in self.OPEN_STATUSES and timezone.now() < self.start

    OPEN_STATUSES = (
        Status.CONFIRMED,
        Status.PENDING_PAYMENT,
        Status.PENDING_APPROVAL,
        Status.PENDING_OFFICE,
    )

    @property
    def total_cents(self):
        return self.price_cents

    @property
    def slot_cents(self):
        """Prezo da franxa sen o suplemento de luz."""
        return self.price_cents - self.lighting_cents

    @property
    def outstanding_cents(self):
        """O que falta por cobrar (oficina ou aprazado)."""
        if self.status in (self.Status.CANCELLED, self.Status.DECLINED, self.Status.EXPIRED):
            return 0
        if self.payment_method in (PaymentMethod.FREE, PaymentMethod.VOUCHER):
            return 0
        return max(0, self.price_cents - self.paid_cents)

    def participant_name_list(self):
        return [n.strip() for n in self.participant_names.splitlines() if n.strip()]

    @property
    def needs_start_state(self):
        """Ao empezar (check-in ou apertura) pódese marcar como estaba a pista."""
        return (
            self.start_state_at is None
            and self.checked_in_at is not None
            and self.status in (self.Status.CONFIRMED, self.Status.USED)
            and timezone.now() < self.end
        )

    def penalty_if_cancelled_now(self):
        if self.status != self.Status.CONFIRMED or timezone.now() < self.cancellation_cutoff():
            return 0
        return self.paid_cents * self.municipality.late_cancel_penalty_pct // 100


class Payment(TenantModel):
    """Cobro dunha reserva ou dunha inscrición. Só unha notificación verificada (ou o persoal no
    mostrador) pode pasalo a pagado ou rexeitado; un pagamento resolto xa non cambia."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pendente")
        PAID = "paid", _("Pagado")
        REJECTED = "rejected", _("Rexeitado")
        EXPIRED = "expired", _("Caducado")
        REFUNDED = "refunded", _("Devolto")
        PARTIALLY_REFUNDED = "partially_refunded", _("Devolto en parte")

    class Method(models.TextChoices):
        ONLINE = "online", _("TPV en liña")
        CASH = "cash", _("Efectivo no mostrador")
        CARD_TERMINAL = "card_terminal", _("Tarxeta no TPV físico")

    FINAL = {
        Status.PAID,
        Status.REJECTED,
        Status.EXPIRED,
        Status.REFUNDED,
        Status.PARTIALLY_REFUNDED,
    }

    booking = models.ForeignKey(
        Booking, null=True, blank=True, on_delete=models.SET_NULL, related_name="payments"
    )
    enrollment = models.ForeignKey(
        "activities.Enrollment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments",
    )
    voucher = models.ForeignKey(
        "Voucher", null=True, blank=True, on_delete=models.SET_NULL, related_name="payments"
    )
    concept = models.CharField(_("concepto"), max_length=200)
    amount_cents = models.PositiveIntegerField(_("importe"))
    refunded_cents = models.PositiveIntegerField(default=0)
    status = models.CharField(
        _("estado"), max_length=20, choices=Status.choices, default=Status.PENDING
    )
    method = models.CharField(
        _("método"), max_length=20, choices=Method.choices, default=Method.ONLINE
    )
    reference = models.CharField(_("referencia"), max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    provider_code = models.CharField(max_length=10, blank=True)  # p. ex. Ds_Response
    signature_ok = models.BooleanField(default=False)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("cobro")
        verbose_name_plural = _("cobros")

    def __str__(self):
        return f"{self.reference} · {self.amount_cents / 100:.2f} € · {self.status}"

    @property
    def is_final(self):
        return self.status in self.FINAL

    @property
    def net_cents(self):
        return self.amount_cents - self.refunded_cents if self.status != self.Status.PENDING else 0


class Rating(TenantModel):
    """«Que tal foi?» despois de usar unha instalación. Unha por reserva."""

    class Score(models.TextChoices):
        GOOD = "good", _("Ben")
        OK = "ok", _("Regular")
        BAD = "bad", _("Mal")

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="rating")
    facility = models.ForeignKey(
        "facilities.Facility", on_delete=models.CASCADE, related_name="ratings"
    )
    score = models.CharField(_("valoración"), max_length=4, choices=Score.choices)
    tags = models.JSONField(_("etiquetas"), default=list, blank=True)
    comment = models.CharField(_("comentario"), max_length=500, blank=True)
    incident = models.ForeignKey(
        "incidents.Incident", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("valoración")
        verbose_name_plural = _("valoracións")
        ordering = ["-created_at"]


class VoucherType(TenantModel):
    """v5 · Bono: un número de usos que se compra na oficina ou co TPV e se desconta en cada
    reserva. Sen instalación = válido en todas as do concello que admitan bono."""

    name = models.CharField(_("nome"), max_length=120)
    facility = models.ForeignKey(
        Facility,
        verbose_name=_("instalación"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="voucher_types",
    )
    uses = models.PositiveIntegerField(_("usos"), default=10)
    price_cents = models.PositiveIntegerField(_("prezo (céntimos)"))
    valid_days = models.PositiveIntegerField(_("validez (días)"), default=365)
    active = models.BooleanField(_("á venda"), default=True)

    class Meta:
        verbose_name = _("tipo de bono")
        verbose_name_plural = _("tipos de bono")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Voucher(TenantModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pendente de pagamento")
        ACTIVE = "active", _("Activo")
        SPENT = "spent", _("Esgotado")
        EXPIRED = "expired", _("Caducado")

    type = models.ForeignKey(VoucherType, on_delete=models.CASCADE, related_name="vouchers")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vouchers"
    )
    uses_total = models.PositiveIntegerField()
    uses_left = models.PositiveIntegerField()
    price_cents = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    channel = models.CharField(max_length=10, default="online")  # online | counter
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    sold_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = _("bono")
        verbose_name_plural = _("bonos")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type} · {self.uses_left}/{self.uses_total}"

    def usable_for(self, facility, at=None):
        at = at or timezone.now()
        return (
            self.status == self.Status.ACTIVE
            and self.uses_left > 0
            and (self.expires_at is None or self.expires_at > at)
            and self.municipality_id == facility.municipality_id
            and (self.type.facility_id is None or self.type.facility_id == facility.pk)
        )
