# SPDX-License-Identifier: EUPL-1.2
"""Axudas para a instalación detrás dun proxy e para a demo pública (EIRA_PUBLIC_DEMO)."""

from django.conf import settings


def client_ip(request):
    """IP real da persoa visitante.

    Detrás do proxy, REMOTE_ADDR é sempre o do proxy: todas as visitas compartirían o límite de
    peticións. O valor fiable é o último de X-Forwarded-For, o que engade o noso proxy; os
    anteriores pódeos escribir quen fai a petición. Sen proxy declarado, a cabeceira ignórase.
    """
    if settings.EIRA_BEHIND_PROXY:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        last = forwarded.rsplit(",", 1)[-1].strip()
        if last:
            return last
    return request.META.get("REMOTE_ADDR", "")


def rejects_email(email):
    """Na demo pública a bandexa de correo vese desde fóra: só se admiten correos ficticios."""
    return settings.EIRA_PUBLIC_DEMO and not email.lower().endswith(".example")
