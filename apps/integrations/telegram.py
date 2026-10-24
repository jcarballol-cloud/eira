# SPDX-License-Identifier: EUPL-1.2
"""Telegram: canle pública do concello e bot persoal de avisos.

O token do bot lese SÓ da variable de contorno EIRA_TELEGRAM_TOKEN (nunca no repositorio nin na
base de datos). En desenvolvemento úsase FakeTelegramAdapter, que garda as mensaxes para o
simulador de chat de /dev/telegram/."""

import json
import logging
import urllib.request

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .models import OutboundMessage

log = logging.getLogger("eira.telegram")


class TelegramAdapter:
    def send(self, chat_id, text):
        """Envía `text` a un chat persoal (id numérico) ou a unha canle pública (@nome)."""
        raise NotImplementedError


class FakeTelegramAdapter(TelegramAdapter):
    def send(self, chat_id, text):
        OutboundMessage.objects.create(
            channel="telegram", target=str(chat_id), payload={"text": text, "from": "bot"}
        )
        return True


class BotApiTelegramAdapter(TelegramAdapter):
    """Bot API de Telegram (https://core.telegram.org/bots/api#sendmessage).

    Configuración: EIRA_TELEGRAM_ADAPTER=apps.integrations.telegram.BotApiTelegramAdapter,
    EIRA_TELEGRAM_TOKEN (contorno), EIRA_TELEGRAM_BOT (nome do bot) e, para recibir o `/start`,
    rexistrar o webhook en /telegram/webhook/<EIRA_TELEGRAM_WEBHOOK_SECRET>/."""

    API = "https://api.telegram.org"
    TIMEOUT = 10

    def __init__(self):
        self.token = getattr(settings, "EIRA_TELEGRAM_TOKEN", "")
        if not self.token:
            raise ImproperlyConfigured("Falta EIRA_TELEGRAM_TOKEN no contorno.")

    def request(self, method, payload):
        req = urllib.request.Request(
            f"{self.API}/bot{self.token}/{method}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:  # noqa: S310 (URL fixa https)
            data = json.loads(resp.read().decode())
        if not data.get("ok"):
            log.warning("Telegram rexeitou %s: %s", method, data.get("description"))
        return data

    def send(self, chat_id, text):
        return self.request(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
        ).get("ok", False)
