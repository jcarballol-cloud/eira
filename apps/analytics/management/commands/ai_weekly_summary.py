# SPDX-License-Identifier: EUPL-1.2
"""Xera o resumo semanal do asistente para cada concello que o ten activado. Para cron:

0 6 * * 1  python manage.py ai_weekly_summary
"""

from django.core.management.base import BaseCommand

from apps.analytics.ai_summary import enabled, generate
from apps.tenants.models import Municipality


class Command(BaseCommand):
    help = "Xera o resumo semanal (IA opcional, só con datos agregados)."

    def handle(self, *args, **options):
        for m in Municipality.objects.filter(is_active=True):
            if enabled(m):
                text = generate(m)
                self.stdout.write(f"{m.slug}: {'ok' if text else 'non dispoñible'}")
                if text and options["verbosity"] > 1:
                    self.stdout.write(text)
