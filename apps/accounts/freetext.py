# SPDX-License-Identifier: EUPL-1.2
"""Aviso común nos campos de texto libre (auditoría RXPD do 14/11/2026).

Un texto libre é onde se pode colar un dato de saúde ou doutra persoa sen querer («Pablo
mancou o nocello»). Eira non o pide nunca: o aviso dío xusto ao lado do campo.
"""

from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy

NO_SENSITIVE = gettext_lazy("Non escribas datos de saúde nin datos persoais doutras persoas.")


def hint(before=None):
    """Texto de axuda co aviso ao final (e, se o hai, a axuda propia do campo antes)."""
    return format_lazy("{} {}", before, NO_SENSITIVE) if before else NO_SENSITIVE
