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
        # v1.2 · B: peches sen confirmar (recordatorios e aviso á persoa responsable)
        from apps.safety.services import escalate_closings, purge_accidents

        self.stdout.write(f"Peches sen confirmar: {escalate_closings()}")
        # v1.2 · F: recordatorios con acción e lista de espera
        from apps.bookings.waitlist import process, send_reminders

        self.stdout.write(f"Recordatorios: {send_reminders()} · Lista de espera: {process()}")
        self.stdout.write(f"Accidentes borrados por conservación: {purge_accidents()}")
        # v1.4 · A1: prazo de conservación do rexistro de auditoría (por concello)
        from apps.accounts.auditlog import purge_expired

        self.stdout.write(
            f"Rexistro de auditoría: {purge_expired()} entradas borradas por antigüidade"
        )
        # v1.5 · E: aviso ao concello cando toca volver confirmar unha acreditación
        from apps.activities.accreditation import notify_due_reviews

        self.stdout.write(f"Acreditacións por revisar: {notify_due_reviews()} avisos")
