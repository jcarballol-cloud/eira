# SPDX-License-Identifier: EUPL-1.2
import logging

from django.conf import settings
from django.core.mail import send_mail

log = logging.getLogger("eira.mail")


class MailAdapter:
    def send(self, to, subject, body):
        raise NotImplementedError


class DevMailboxAdapter(MailAdapter):
    """Desenvolvemento: garda o correo na bandexa local (/dev/mailbox) e escríbeo na consola."""

    def send(self, to, subject, body):
        from .models import DevMail

        DevMail.objects.create(to=to, subject=subject, body=body)
        log.info("[correo simulado] para=%s asunto=%s", to, subject)


class SmtpMailAdapter(MailAdapter):
    """Produción: usa o SMTP configurado en Django (EMAIL_HOST, …) do propio concello."""

    def send(self, to, subject, body):
        send_mail(subject, body, settings.EIRA_DEFAULT_FROM_EMAIL, [to])
