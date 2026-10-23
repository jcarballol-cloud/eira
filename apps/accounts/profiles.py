# SPDX-License-Identifier: EUPL-1.2
"""Tipo de perfil de cada persona e a súa pantalla principal.

Cada perfil ten a súa ferramenta, co seu formato:
- `public`:    sen sesión → web pública do concello (consulta sen rexistro)
- `neighbour`: veciñanza → app móbil (reservar, reservas, familia, saúde, avisos)
- `operator`:  mantemento → app móbil coas súas ordes
- `monitor`:   monitora → tableta cos seus grupos
- `admin`:     administración do concello → web de escritorio
- `region`:    deputación → web de escritorio coa súa rede

Unha mesma persoa pode ter varios roles noutros concellos; no concello activo manda o de máis
responsabilidade. Para usar a app como veciña, o persoal ten que usar outra conta (decisión
documentada en DECISIONS.md).
"""

from django.urls import reverse

STAFF_ROLES = frozenset({"admin", "maintenance", "monitor", "region_admin"})
LAYOUT = {
    "public": "public",
    "neighbour": "app",
    "operator": "app",
    "monitor": "tablet",
    "admin": "desk",
    "region": "desk",
}


def kind_in_tenant(user, roles):
    if not user.is_authenticated:
        return "public"
    if "admin" in roles:
        return "admin"
    if "region_admin" in roles:
        return "region"
    if "maintenance" in roles:
        return "operator"
    if "monitor" in roles:
        return "monitor"
    return "neighbour"


def kind_global(user):
    """Tipo de perfil fóra dun concello (portada, conta, deputación)."""
    if not user.is_authenticated:
        return "public"
    if user.region_memberships.exists():
        return "region"
    roles = set(user.memberships.values_list("role", flat=True))
    return kind_in_tenant(user, roles & STAFF_ROLES)


def home_tenant(user):
    """Concello principal da persoa: o do seu rol de persoal, se non o do seu empadroamento ou alta."""
    from apps.tenants.models import Municipality

    m = (
        user.memberships.exclude(role="citizen").select_related("municipality").first()
        or user.memberships.select_related("municipality").first()
    )
    if m:
        return m.municipality
    r = user.residencies.select_related("municipality").first()
    return r.municipality if r else Municipality.objects.filter(is_active=True).first()


def home_url(user, tenant=None, roles=None):
    """Pantalla principal do perfil: a que abre o logo de Eira."""
    if not user.is_authenticated:
        return reverse("tenant_home", args=[tenant.slug]) if tenant else reverse("home")
    region = user.region_memberships.select_related("region").first()
    if tenant is None:
        if region and not user.memberships.exclude(role="citizen").exists():
            return reverse("region:dashboard", args=[region.region.slug])
        tenant = home_tenant(user)
        if tenant is None:
            return reverse("home")
        from apps.accounts.models import Membership

        roles = set(
            Membership.objects.filter(user=user, municipality=tenant).values_list("role", flat=True)
        )
    kind = kind_in_tenant(user, roles or set())
    if kind == "region" and region:
        return reverse("region:dashboard", args=[region.region.slug])
    target = {
        "admin": "manage:dashboard",
        "operator": "maintenance:my_orders",
        "monitor": "monitor:today",
        "neighbour": "app:home",
    }[kind]
    return reverse(target, args=[tenant.slug])
