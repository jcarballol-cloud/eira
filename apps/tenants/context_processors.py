# SPDX-License-Identifier: EUPL-1.2
from django.conf import settings

from apps.accounts.profiles import LAYOUT, home_tenant, home_url, kind_global, kind_in_tenant

from .models import DEFAULT_MODULES
from .prefs import read_prefs


def eira(request):
    tenant = getattr(request, "tenant", None)
    roles = getattr(request, "roles", set())
    user = request.user
    unread = 0
    if user.is_authenticated:
        from apps.notifications.models import Notification

        qs = Notification.objects.filter(user=user, read_at__isnull=True)
        if tenant:
            qs = qs.filter(municipality=tenant)
        unread = qs.count()
    kind = kind_in_tenant(user, roles) if tenant else kind_global(user)
    # Concello da app cando a páxina non ten concello (conta, saúde…): o principal da persoa
    app_tenant = tenant or (home_tenant(user) if user.is_authenticated else None)
    # v5: persoa doutro concello da rede reservando aquí → a app segue sendo a do seu concello
    network_visit = None
    if kind == "neighbour" and tenant is not None and tenant.region_id and user.is_authenticated:
        from apps.bookings.services import linked_home, linked_to

        if not linked_to(tenant, user):
            home = linked_home(user)
            if home and home.pk != tenant.pk and home.region_id == tenant.region_id:
                network_visit = {"home": home, "here": tenant}
                app_tenant = home
    layout = LAYOUT[kind]
    if layout == "app" and app_tenant is None:
        layout = "public"
    if layout in ("desk", "tablet") and kind in ("admin", "monitor") and tenant is None:
        layout = "public"  # páxinas globais (conta, preferencias) do persoal do concello
    layout = getattr(request, "layout_override", None) or layout
    nav_region = None
    if kind == "region":
        nav_region = getattr(request, "region", None) or (tenant.region if tenant else None)
        if nav_region is None:
            rm = user.region_memberships.select_related("region").first()
            nav_region = rm.region if rm else None
    # Barra de demo: concello e perfil activos
    demo_persona = demo_place = None
    if settings.EIRA_DEMO_TOOLS and user.is_authenticated:
        from apps.integrations.demo import BY_EMAIL

        demo_persona = BY_EMAIL.get(user.email)
        if demo_persona:
            demo_place = (
                nav_region.name
                if nav_region and not tenant
                else (tenant or app_tenant).name
                if (tenant or app_tenant)
                else None
            )
    from .help import help_for

    match = getattr(request, "resolver_match", None)
    return {
        "help_topic": help_for(match.view_name if match else "", kind),
        "network_visit": network_visit,
        "desk_mode": getattr(user, "desk_mode", "basic") if user.is_authenticated else "basic",
        "support_access": getattr(request, "support_access", None),
        "demo_persona": demo_persona,
        "demo_place": demo_place,
        "demo_back": (request.session.get("demo_back") if hasattr(request, "session") else None)
        or (home_url(user, tenant, roles) if user.is_authenticated else "/"),
        "demo_change_url": "/?concello=" + (demo_persona["tenant"] or "") + "#perfil"
        if demo_persona and demo_persona.get("tenant")
        else "/#concello",
        "tenant": tenant,
        "nav_region": nav_region,
        "app_tenant": app_tenant,
        "modules": {**DEFAULT_MODULES, **(tenant.modules or {})} if tenant else {},
        "roles": roles,
        "kind": kind,
        "layout": layout,
        "home_url": home_url(user, tenant, roles) if (tenant or user.is_authenticated) else "/",
        "is_neighbour": kind in ("neighbour", "public"),
        "region_consult": bool(tenant and "region_admin" in roles and "admin" not in roles),
        "framed": getattr(request, "framed", False) and layout in ("app", "tablet"),
        "is_staff_of_tenant": bool(
            roles & {"admin", "maintenance", "monitor", "region_admin", "dpo"}
        ),
        "is_tenant_admin": bool(roles & {"admin", "region_admin"}),
        "demo_tools": settings.EIRA_DEMO_TOOLS,
        "unread_notifications": unread,
        "prefs": read_prefs(request),
    }
