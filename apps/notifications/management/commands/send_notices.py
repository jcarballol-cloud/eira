# SPDX-License-Identifier: EUPL-1.2
"""Envía os avisos programados que xa tocan. Pensado para cron ou un temporizador de systemd
(p. ex. cada 5 minutos): `python manage.py send_notices`."""

from django.core.management.base import BaseCommand

from apps.notifications.notices import purge, send_due


class Command(BaseCommand):
    help = "Envía os avisos do concello programados cuxa hora xa chegou."

    def handle(self, *args, **options):
        done = send_due()
        self.stdout.write(f"Avisos enviados: {len(done)}")
        self.stdout.write(f"Avisos antigos borrados (conservación 12 meses): {purge()}")
        # v1.1: zonas de limpeza que levan máis do previsto sen limpar → aviso ao concello
        from apps.maintenance.cleaning import check_overdue

        self.stdout.write(f"Avisos de limpeza atrasada: {check_overdue()}")
