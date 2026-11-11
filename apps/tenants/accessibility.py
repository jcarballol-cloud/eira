# SPDX-License-Identifier: EUPL-1.2
"""v1.5.1: datos da declaración de accesibilidade (RD 1112/2018, art. 15).

A avaliación é a de Eira; a canle de comunicación e reclamación é de cada concello
(«Configuración → Declaración de accesibilidade»). `AXE_PAGES` compróbao
`tests/e2e/test_accessibility.py`: se cambian as páxinas revisadas, hai que actualizar a declaración.
"""

import datetime as dt

EVALUATED_ON = dt.date(2026, 11, 11)
AXE_PAGES = 175  # páxinas revisadas con axe-core en cada tamaño de pantalla
AXE_SIZES = 3  # móbil, tableta e escritorio
AXE_DARK_PAGES = 81  # en tema escuro


def statement_context(tenant):
    """Datos da declaración. Sen concello: páxinas comúns, con ligazón á de cada concello."""
    from .models import Municipality

    ctx = {
        "evaluated_on": EVALUATED_ON,
        "axe_pages": AXE_PAGES,
        "axe_sizes": AXE_SIZES,
        "axe_dark_pages": AXE_DARK_PAGES,
    }
    if tenant is None:
        ctx["municipalities"] = Municipality.objects.filter(is_active=True).order_by("name")
        return ctx
    ctx.update(
        {
            "reviewed_on": tenant.accessibility_reviewed_on or EVALUATED_ON,
            "unit": tenant.accessibility_unit,
            "email": tenant.accessibility_email or tenant.contact_email,
            "phone": tenant.accessibility_phone or tenant.contact_phone,
            "complaint_url": tenant.accessibility_complaint_url,
        }
    )
    return ctx
