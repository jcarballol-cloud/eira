# SPDX-License-Identifier: EUPL-1.2
"""Resolución do concello activo e cabeceiras de seguridade.

Un concello resólvese de dúas maneiras equivalentes:
- por ruta: /c/<slug>/… (desenvolvemento e instalacións cun só dominio);
- por host: <slug>.EIRA_BASE_DOMAIN ou o dominio propio do concello. Nese caso a ruta
  reescríbese internamente a /c/<slug>/… para que o enrutado sexa único.
"""

from django.conf import settings
from django.core.cache import cache
from django.http import Http404

from .models import Municipality

PASSTHROUGH_PREFIXES = (
    "/c/",
    "/static/",
    "/media/",
    "/api/",
    "/dev/",
    "/admin/",
    "/i18n/",
    "/sw.js",
    "/manifest.webmanifest",
    "/acceso/",
    "/conta/",
    "/preferencias/",
    "/rexion/",
    "/saude/",
    "/offline/",
)


def _slug_for_host(host):
    host = host.split(":")[0].lower()
    cache_key = f"eira:host:{host}"
    slug = cache.get(cache_key)
    if slug is None:
        slug = ""
        base = settings.EIRA_BASE_DOMAIN.lower()
        candidate = (
            Municipality.objects.filter(domain=host, is_active=True)
            .values_list("slug", flat=True)
            .first()
        )
        if candidate:
            slug = candidate
        elif base and host.endswith("." + base):
            sub = host[: -len(base) - 1]
            if "." not in sub and Municipality.objects.filter(slug=sub, is_active=True).exists():
                slug = sub
        cache.set(cache_key, slug, 300)
    return slug


class SubdomainTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        slug = _slug_for_host(request.get_host())
        request.host_tenant_slug = slug
        if slug and not request.path_info.startswith(PASSTHROUGH_PREFIXES):
            request.path_info = f"/c/{slug}{request.path_info}"
        return self.get_response(request)


class TenantMiddleware:
    """Converte o kwarg `tenant` da URL en `request.tenant` e carga os roles da persoa."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        request.roles = set()
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        slug = view_kwargs.pop("tenant", None)
        if slug is None:
            return None
        try:
            tenant = Municipality.objects.select_related("region").get(slug=slug, is_active=True)
        except Municipality.DoesNotExist as exc:
            raise Http404("Concello descoñecido") from exc
        request.tenant = tenant
        if request.user.is_authenticated:
            from apps.accounts.models import Membership

            request.roles = set(
                Membership.objects.filter(user=request.user, municipality=tenant).values_list(
                    "role", flat=True
                )
            )
            if request.user.is_superuser:
                request.roles |= {"admin"}
            if (
                tenant.region_id
                and request.user.region_memberships.filter(region_id=tenant.region_id).exists()
            ):
                request.roles |= {"region_admin"}
        return None


class SecurityHeadersMiddleware:
    """CSP estrita (sen unsafe-inline), Permissions-Policy e outras cabeceiras."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        tile = settings.EIRA_TILE_ORIGIN
        if request.path.startswith("/admin/"):
            # O admin de Django usa algúns estilos en liña; só se relaxa nesa área interna.
            csp = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'"
        else:
            csp = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                f"img-src 'self' data: blob: {tile}; font-src 'self'; connect-src 'self'; "
                "worker-src 'self'; manifest-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
                "form-action 'self'; object-src 'none'"
            )
        response.setdefault("Content-Security-Policy", csp)
        response.setdefault(
            "Permissions-Policy", "geolocation=(self), camera=(self), microphone=(), payment=()"
        )
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response
