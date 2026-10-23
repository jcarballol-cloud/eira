# SPDX-License-Identifier: EUPL-1.2
from .models import OutboundMessage


class TelegramAdapter:
    def send(self, chat_id, text):
        raise NotImplementedError


class FakeTelegramAdapter(TelegramAdapter):
    def send(self, chat_id, text):
        OutboundMessage.objects.create(channel="telegram", target=chat_id, payload={"text": text})
        return True


class BotApiTelegramAdapter(TelegramAdapter):
    """Esqueleto: Bot API de Telegram (token do bot do concello en EIRA_TELEGRAM_TOKEN)."""

    def send(self, chat_id, text):
        raise NotImplementedError
