# SPDX-License-Identifier: EUPL-1.2
from django.conf import settings

from .models import DEFAULT_MODULES
from .prefs import read_prefs


def eira(request):
    tenant = getattr(request, "tenant", None)
    roles = getattr(request, "roles", set())
    unread = 0
    if request.user.is_authenticated:
        from apps.notifications.models import Notification

        qs = Notification.objects.filter(user=request.user, read_at__isnull=True)
        if tenant:
            qs = qs.filter(municipality=tenant)
        unread = qs.count()
    return {
        "tenant": tenant,
        "modules": {**DEFAULT_MODULES, **(tenant.modules or {})} if tenant else {},
        "roles": roles,
        "is_staff_of_tenant": bool(roles & {"admin", "maintenance", "monitor", "region_admin"}),
        "is_tenant_admin": bool(roles & {"admin", "region_admin"}),
        "demo_tools": settings.EIRA_DEMO_TOOLS,
        "unread_notifications": unread,
        "prefs": read_prefs(request),
    }
