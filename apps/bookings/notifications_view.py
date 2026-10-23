# SPDX-License-Identifier: EUPL-1.2
"""URL de notificación en liña da pasarela de pagamento (servidor a servidor)."""

import logging

from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .payments import InvalidSignature, handle_notification

log = logging.getLogger("eira.payments")


@csrf_exempt  # a pasarela non ten sesión: a autenticidade garántea a sinatura HMAC
@require_POST
def gateway_notification(request):
    try:
        handle_notification(request.POST)
    except InvalidSignature:
        log.warning("Notificación de pagamento con sinatura non válida")
        return HttpResponseForbidden("invalid signature")
    return HttpResponse("OK")
