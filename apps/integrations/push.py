# SPDX-License-Identifier: EUPL-1.2
"""Web Push (RFC 8030 + VAPID RFC 8292) detrás dun adaptador."""

from .models import OutboundMessage


class PushAdapter:
    def send(self, subscription, title, body, url=""):
        raise NotImplementedError


class FakeWebPushAdapter(PushAdapter):
    def send(self, subscription, title, body, url=""):
        OutboundMessage.objects.create(
            channel="push", target=subscription.endpoint[:200], payload={"title": title, "body": body, "url": url}
        )
        return True


class VapidWebPushAdapter(PushAdapter):
    """Esqueleto: envío cifrado (RFC 8291) con claves VAPID propias do concello."""

    def send(self, subscription, title, body, url=""):
        raise NotImplementedError
