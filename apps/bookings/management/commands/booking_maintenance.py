# SPDX-License-Identifier: EUPL-1.2
"""Tarefas periódicas das reservas. Para cron cada 15 minutos:

*/15 * * * *  python manage.py booking_maintenance
"""

from django.core.management.base import BaseCommand

from apps.bookings.services import expire_holds, mark_no_shows


class Command(BaseCommand):
    help = "Libera as reservas pendentes de pago caducadas e marca as non presentadas."

    def handle(self, *args, **options):
        self.stdout.write(
            f"{expire_holds()} reservas pendentes caducadas, {mark_no_shows()} non presentadas"
        )
