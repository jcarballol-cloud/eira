# SPDX-License-Identifier: EUPL-1.2
"""v1.4 · A2: volve cifrar os segredos do dobre factor coa chave principal actual.

Úsase despois de definir (ou cambiar) `EIRA_TOTP_KEY`: os segredos cifrados coa chave anterior
derivada de `EIRA_SECRET_KEY` pásanse á nova. Ver docs/seguridade-rxpd.md.
"""

from django.core.management.base import BaseCommand

from apps.accounts.models import TwoFactorDevice


class Command(BaseCommand):
    help = "Volve cifrar os segredos do dobre factor coa chave actual (EIRA_TOTP_KEY)."

    def handle(self, *args, **options):
        done = unreadable = 0
        for device in TwoFactorDevice.objects.all():
            if not device.secret:
                unreadable += 1
                continue
            device.save(update_fields=["secret"])  # get_prep_value cifra coa chave principal
            done += 1
        self.stdout.write(f"{done} segredos cifrados de novo, {unreadable} ilexibles")
        if unreadable:
            self.stdout.write(
                "Os ilexibles cifráronse cunha chave que xa non está: restablece o dobre factor "
                "desas persoas desde Persoal e permisos."
            )
