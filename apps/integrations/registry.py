# SPDX-License-Identifier: EUPL-1.2
"""Rexistro de adaptadores. Cada integración externa vive detrás dunha interface e
selecciónase por configuración (EIRA_ADAPTERS). As implementacións por defecto son
simuladas e funcionan sen conexión."""

from functools import cache

from django.conf import settings
from django.utils.module_loading import import_string


@cache
def get_adapter(kind):
    return import_string(settings.EIRA_ADAPTERS[kind])()


def reset_adapters():
    get_adapter.cache_clear()
