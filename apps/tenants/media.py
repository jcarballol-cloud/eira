# SPDX-License-Identifier: EUPL-1.2
"""Servizo de ficheiros subidos con control de acceso.

As fotos de instalacións e escudos son públicas. As fotos de incidencias e ordes de traballo poden
mostrar persoas ou lugares privados: só as ven quen as enviou e o persoal do concello.
En produción, o proxy pode delegar aquí só as rutas privadas (ver docs/despregamento.md).
"""

from django.conf import settings
from django.http import Http404
from django.views.static import serve

from apps.accounts.models import Membership, Role

PRIVATE_PREFIXES = ("incidents/", "workorders/")
STAFF = (Role.ADMIN, Role.MAINTENANCE)


def _can_see(user, municipality_id, reporter_id=None):
    if not user.is_authenticated:
        return False
    if user.is_superuser or (reporter_id and reporter_id == user.pk):
        return True
    if Membership.objects.filter(
        user=user, municipality_id=municipality_id, role__in=STAFF
    ).exists():
        return True
    return user.region_memberships.filter(region__municipalities__id=municipality_id).exists()


def protected_serve(request, path):
    if path.startswith(PRIVATE_PREFIXES):
        from apps.bookings.models import Booking
        from apps.incidents.models import Incident
        from apps.maintenance.models import WorkOrderPhoto

        incident = (
            Incident.objects.filter(photo=path).values("municipality_id", "reporter_id").first()
        )
        # v5: foto do estado ao entrar (vai coa reserva; se había un problema, tamén coa incidencia)
        start_photo = (
            None
            if incident
            else Booking.objects.filter(start_state_photo=path)
            .values("municipality_id", "user_id")
            .first()
        )
        if incident:
            allowed = _can_see(request.user, incident["municipality_id"], incident["reporter_id"])
        elif start_photo:
            allowed = _can_see(request.user, start_photo["municipality_id"], start_photo["user_id"])
        else:
            photo = (
                WorkOrderPhoto.objects.filter(image=path).values("order__municipality_id").first()
            )
            allowed = bool(photo) and _can_see(request.user, photo["order__municipality_id"])
        if not allowed:
            raise Http404
    response = serve(request, path, document_root=settings.MEDIA_ROOT)
    if path.startswith(PRIVATE_PREFIXES):
        response["Cache-Control"] = "private, no-store"
    return response
