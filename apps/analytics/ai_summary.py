# SPDX-License-Identifier: EUPL-1.2
"""Resumo semanal co asistente (opcional). Cachéase por concello e semana: un modelo local pode
tardar minutos, así que nunca se chama ao cargar o panel, só baixo demanda ou desde cron."""

import logging

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.integrations.registry import get_adapter

from . import indicators

log = logging.getLogger("eira.ai")


def _key(tenant):
    year, week, _ = timezone.localdate().isocalendar()
    return f"eira:ai-summary:{tenant.pk}:{year}-{week}"


def enabled(tenant):
    return settings.EIRA_AI_ENABLED and tenant.module_enabled("ai_summary")


def cached(tenant):
    return cache.get(_key(tenant)) if enabled(tenant) else None


def generate(tenant):
    """Xera e garda o resumo. Devolve o texto ou None se o asistente falla (a plataforma segue igual)."""
    if not enabled(tenant):
        return None
    try:
        text = get_adapter("ai").weekly_summary(indicators.ai_aggregates(tenant))
    except Exception:
        log.exception("Asistente non dispoñible")
        return None
    cache.set(_key(tenant), text, 60 * 60 * 24 * 8)
    return text
