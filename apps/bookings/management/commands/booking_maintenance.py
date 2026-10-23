# SPDX-License-Identifier: EUPL-1.2
"""Tarefas periódicas das reservas. Para cron cada 15 minutos:

*/15 * * * *  python manage.py booking_maintenance
"""

import datetime as dt

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import AppRequest
from apps.bookings.services import expire_holds, mark_no_shows


def purge_app_requests(months=12):
    """Conservación (RAT n.º 10): as solicitudes da app bórranse aos 12 meses."""
    limit = timezone.now() - dt.timedelta(days=30 * months)
    return AppRequest.objects.filter(created_at__lt=limit).delete()[0]


class Command(BaseCommand):
    help = (
        "Libera as reservas pendentes de pago caducadas, marca as non presentadas e "
        "aplica os prazos de conservación."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            f"{expire_holds()} reservas pendentes caducadas, {mark_no_shows()} non presentadas, "
            f"{purge_app_requests()} solicitudes da app borradas por antigüidade"
        )
