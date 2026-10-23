# SPDX-License-Identifier: EUPL-1.2
"""Xera as ordes de traballo das tarefas periódicas (idempotente). Para cron diario:

0 5 * * *  python manage.py generate_work_orders --days 14
"""

from django.core.management.base import BaseCommand

from apps.maintenance.services import generate_orders


class Command(BaseCommand):
    help = "Xera ordes de traballo de mantemento preventivo para os próximos días."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=14)

    def handle(self, *args, **options):
        n = generate_orders(days=options["days"])
        self.stdout.write(f"{n} ordes novas")
