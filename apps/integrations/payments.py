# SPDX-License-Identifier: EUPL-1.2
"""Pagamentos detrás dun adaptador. Por defecto, un TPV simulado tipo Redsys (/dev/tpv/)."""

import secrets
from dataclasses import dataclass

from django.urls import reverse


@dataclass
class PaymentStatus:
    reference: str
    paid: bool
    amount_cents: int
    refunded_cents: int = 0


class PaymentAdapter:
    def create(self, amount_cents, description, return_url):
        """Crea unha orde de pago e devolve (referencia, url_para_redirixir)."""
        raise NotImplementedError

    def status(self, reference):
        raise NotImplementedError

    def refund(self, reference, amount_cents):
        raise NotImplementedError


class FakeRedsysAdapter(PaymentAdapter):
    def create(self, amount_cents, description, return_url):
        from .models import FakePayment

        reference = "FR" + secrets.token_hex(6).upper()
        FakePayment.objects.create(
            reference=reference,
            amount_cents=amount_cents,
            description=description[:200],
            return_url=return_url,
        )
        return reference, reverse("dev:tpv", args=[reference])

    def status(self, reference):
        from .models import FakePayment

        p = FakePayment.objects.filter(reference=reference).first()
        if not p:
            return None
        return PaymentStatus(
            reference, p.status in ("paid", "refunded"), p.amount_cents, p.refunded_cents
        )

    def refund(self, reference, amount_cents):
        from .models import FakePayment

        p = FakePayment.objects.filter(reference=reference).first()
        if not p or amount_cents <= 0:
            return False
        p.refunded_cents = min(p.amount_cents, p.refunded_cents + amount_cents)
        p.status = FakePayment.Status.REFUNDED
        p.save()
        return True


class RedsysAdapter(PaymentAdapter):
    """Esqueleto: Redsys (TPV virtual da entidade financeira do concello).

    Sinatura HMAC-SHA256 dos parámetros (Ds_MerchantParameters) coa clave do comercio,
    redirección ao TPV e notificación en liña (Ds_Signature) validada no servidor.
    """

    def create(self, amount_cents, description, return_url):
        raise NotImplementedError

    def status(self, reference):
        raise NotImplementedError

    def refund(self, reference, amount_cents):
        raise NotImplementedError
