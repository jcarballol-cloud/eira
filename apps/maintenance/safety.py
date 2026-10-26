# SPDX-License-Identifier: EUPL-1.2
"""v5 · H: plantilla de mantemento «Revisión de seguridade inicial Eira».

Faise ao dar de alta cada instalación (ou como servizo de consultoría, ver docs/servizos.md).
É unha orde de traballo co seu checklist; ao pechala, a ficha pública mostra «Revisada o ‹data›»
e conta como última supervisión."""

from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.accounts.models import audit

from .models import WorkOrder

SAFETY_TITLE = gettext_lazy("Revisión de seguridade inicial Eira")
SAFETY_CHECKLIST = [
    gettext_lazy("Pavimento: sen fendas, buracos nin zonas esvaradías"),
    gettext_lazy("Ancoraxes de porterías e canastras: fixas e sen risco de envorcar"),
    gettext_lazy("Iluminación: todas as luminarias funcionan e as de emerxencia acenden"),
    gettext_lazy("Valado e redes: sen arames soltos nin bordos cortantes"),
    gettext_lazy("Sinalización: normas, saídas e teléfono de emerxencias visibles"),
    gettext_lazy("Botiquín: completo e dentro de data"),
    gettext_lazy("DEA: localizado, sinalizado e coa revisión ao día (ou o máis próximo anotado)"),
    gettext_lazy("Vías de evacuación: libres e ben sinalizadas"),
    gettext_lazy("Accesibilidade física: acceso sen chanzos, aseo e aparcadoiro como se declaran"),
    gettext_lazy("Protocolo na porta: cartel de Eira co 112, o DEA e o teléfono do concello"),
]


def create_safety_review(facility, by=None, due=None):
    """Crea a orde (ou devolve a aberta, se xa hai unha)."""
    open_order = (
        WorkOrder.objects.filter(facility=facility, kind="safety_review")
        .exclude(status=WorkOrder.Status.DONE)
        .first()
    )
    if open_order:
        return open_order
    order = WorkOrder.objects.create(
        municipality=facility.municipality,
        facility=facility,
        kind="safety_review",
        title=f"{SAFETY_TITLE} · {facility.name}",
        description=_(
            "Revisión completa antes de abrir (ou de volver abrir) a instalación. Anota en cada "
            "punto o que falte e crea unha orde para corrixilo. Ao pechar esta orde, a ficha "
            "mostrará «Revisada o ‹data›»."
        ),
        due_date=due or timezone.localdate(),
        checklist_state=[{"label": str(item), "done": False} for item in SAFETY_CHECKLIST],
    )
    audit("safety_review.create", by, facility.municipality, order)
    return order
