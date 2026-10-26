# SPDX-License-Identifier: EUPL-1.2
"""Rexistros das integracións simuladas (só para desenvolvemento e demostración)."""

from django.db import models


class DevMail(models.Model):
    """Bandexa local de correo: o adaptador de desenvolvemento escribe aquí (visible en /dev/mailbox)."""

    to = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]


class OutboundMessage(models.Model):
    """Mensaxes simuladas doutras canles (Telegram, push, pechaduras) para inspección."""

    channel = models.CharField(max_length=20)
    target = models.CharField(max_length=200)
    payload = models.JSONField(default=dict)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]


class FakePayment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        PAID = "paid"
        FAILED = "failed"
        REFUNDED = "refunded"

    reference = models.CharField(max_length=40, unique=True)
    amount_cents = models.PositiveIntegerField()
    description = models.CharField(max_length=200)
    # v5: comercio (TPV) do concello que cobra; nas reservas en concellos da rede, o do destino
    merchant = models.CharField(max_length=160, blank=True)
    return_url = models.CharField(max_length=300)
    return_url_ko = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    refunded_cents = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
