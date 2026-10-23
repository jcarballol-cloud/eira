# SPDX-License-Identifier: EUPL-1.2
"""Pagamentos detrás dun adaptador, ao estilo Redsys.

Fluxo (igual que nun TPV virtual real):
1. A plataforma crea unha orde e redirixe a persoa á pasarela.
2. A persoa paga ou cancela na pasarela, que a devolve á URL OK ou KO. **Esta volta non decide nada.**
3. A pasarela envía unha **notificación servidor a servidor asinada** (HMAC-SHA256 dos parámetros
   en base64). Só esta notificación, verificada, cambia o estado do pagamento.

`FakeRedsysAdapter` simula a pasarela en /dev/tpv/ cunha clave de comercio local.
`RedsysAdapter` queda como esqueleto para o TPV real da entidade do concello.
"""

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass

from django.conf import settings
from django.urls import reverse


class InvalidSignature(Exception):
    pass


@dataclass
class GatewayResult:
    reference: str
    ok: bool
    code: str
    amount_cents: int


def merchant_key():
    """Clave do comercio simulado (en produción, a que facilita a entidade bancaria)."""
    return (settings.EIRA_PAYMENT_SECRET or settings.SECRET_KEY).encode()


def sign(params_b64):
    digest = hmac.new(merchant_key(), params_b64.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def encode_params(params):
    return base64.b64encode(json.dumps(params, sort_keys=True).encode()).decode()


class PaymentAdapter:
    def start(self, payment, url_ok, url_ko):
        """Prepara a orde na pasarela e devolve a URL á que redirixir á persoa."""
        raise NotImplementedError

    def parse_notification(self, data):
        """Verifica a sinatura da notificación e devolve un GatewayResult (ou InvalidSignature)."""
        raise NotImplementedError

    def refund(self, payment, amount_cents):
        raise NotImplementedError


class FakeRedsysAdapter(PaymentAdapter):
    def start(self, payment, url_ok, url_ko):
        from .models import FakePayment

        FakePayment.objects.update_or_create(
            reference=payment.reference,
            defaults={
                "amount_cents": payment.amount_cents,
                "description": payment.concept[:200],
                "return_url": url_ok,
                "return_url_ko": url_ko,
                "status": FakePayment.Status.PENDING,
            },
        )
        return reverse("dev:tpv", args=[payment.reference])

    def build_notification(self, fake, ok):
        """O que enviaría a pasarela ao servidor do concello (Ds_Response < 100 = autorizada)."""
        params = {
            "Ds_Order": fake.reference,
            "Ds_Amount": str(fake.amount_cents),
            "Ds_Response": "0000" if ok else "0190",
            "Ds_Currency": "978",
        }
        b64 = encode_params(params)
        return {
            "Ds_SignatureVersion": "HMAC_SHA256_V1",
            "Ds_MerchantParameters": b64,
            "Ds_Signature": sign(b64),
        }

    def parse_notification(self, data):
        b64 = data.get("Ds_MerchantParameters", "")
        signature = data.get("Ds_Signature", "")
        if not b64 or not hmac.compare_digest(sign(b64), signature):
            raise InvalidSignature("Sinatura non válida")
        params = json.loads(base64.b64decode(b64))
        code = params.get("Ds_Response", "9999")
        ok = code.isdigit() and int(code) < 100
        return GatewayResult(params["Ds_Order"], ok, code, int(params.get("Ds_Amount", 0)))

    def refund(self, payment, amount_cents):
        from .models import FakePayment

        fake = FakePayment.objects.filter(reference=payment.reference).first()
        if not fake or amount_cents <= 0:
            return False
        fake.refunded_cents = min(fake.amount_cents, fake.refunded_cents + amount_cents)
        fake.status = FakePayment.Status.REFUNDED
        fake.save(update_fields=["refunded_cents", "status"])
        return True


class RedsysAdapter(PaymentAdapter):
    """Esqueleto: Redsys (TPV virtual da entidade financeira do concello).

    - Ds_MerchantParameters en base64 e Ds_Signature HMAC-SHA256 cunha clave derivada (3DES) por pedido.
    - URL de notificación en liña (servidor a servidor) → `/pagamentos/notificacion/`.
    - Devolucións mediante a operación de tipo 3 da API REST.
    """

    def start(self, payment, url_ok, url_ko):
        raise NotImplementedError

    def parse_notification(self, data):
        raise NotImplementedError

    def refund(self, payment, amount_cents):
        raise NotImplementedError
