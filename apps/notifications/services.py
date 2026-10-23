# SPDX-License-Identifier: EUPL-1.2
"""Avisos multicanle: na aplicación (sempre), correo, Telegram e push segundo preferencias."""

import logging

from apps.integrations.registry import get_adapter

from .models import Notification

log = logging.getLogger("eira.notify")


def notify(
    user, title, body="", url="", municipality=None, level=Notification.Level.INFO, email=True
):
    if user is None:
        return None
    channels = ["app"]
    try:
        if email and user.notify_email:
            get_adapter("mail").send(user.email, f"Eira · {title}", f"{body}\n\n{url}".strip())
            channels.append("email")
        if user.notify_telegram and user.telegram_chat:
            get_adapter("telegram").send(user.telegram_chat, f"{title}\n{body}")
            channels.append("telegram")
        for sub in user.push_subscriptions.all()[:5]:
            get_adapter("push").send(sub, title, body, url)
            channels.append("push")
    except Exception:  # un fallo de canle nunca impide o aviso na aplicación
        log.exception("Fallo enviando aviso")
    return Notification.objects.create(
        user=user,
        municipality=municipality,
        title=title[:160],
        body=body,
        url=url,
        level=level,
        channels=",".join(dict.fromkeys(channels)),
    )


def notify_email_only(address, subject, body):
    get_adapter("mail").send(address, subject, body)
