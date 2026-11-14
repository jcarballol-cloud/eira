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

from .language import apply_tenant_default
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
    "/pagamentos/",
    "/conta/",
    "/preferencias/",
    "/rexion/",
    "/saude/",
    "/offline/",
    "/axuda/",
    "/modo-xestion/",
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
        apply_tenant_default(request, tenant)
        # Lembra o último concello visitado (para volver a el despois de identificarse).
        # Só se xa hai sesión: non se crean sesións para visitantes anónimos.
        session = getattr(request, "session", None)
        if session is not None and session.session_key and session.get("last_tenant") != slug:
            session["last_tenant"] = slug
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
        from .models import tile_settings

        tile = tile_settings(getattr(request, "tenant", None))["origin"]
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


class DemoFrameMiddleware:
    """Modo presentación: na demo, a app móbil e a tableta móstranse dentro dun marco de dispositivo
    nun navegador de escritorio. `?marco=0` ou `?marco=1` cámbiao e recórdao nunha cookie.
    Nun móbil real o CSS ignora o marco (a app ocupa a pantalla enteira)."""

    COOKIE = "eira_marco"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        param = request.GET.get("marco")
        if param in ("0", "1"):
            request.framed = param == "1"
        else:
            request.framed = (
                settings.EIRA_DEMO_TOOLS and request.COOKIES.get(self.COOKIE, "1") == "1"
            )
        response = self.get_response(request)
        if param in ("0", "1"):
            response.set_cookie(
                self.COOKIE, param, max_age=60 * 60 * 24 * 30, samesite="Lax", httponly=True
            )
        self.remember_back(request, response)
        return response

    BACK_KEY = "demo_back"
    SKIP = ("/dev/", "/static/", "/media/", "/api/", "/sw.js", "/manifest", "/i18n/", "/acceso/")

    def remember_back(self, request, response):
        """v4: «← Volver á demo» nas ferramentas leva á última páxina vista co perfil activo."""
        if not (
            settings.EIRA_DEMO_TOOLS
            and request.method == "GET"
            and response.status_code == 200
            and request.user.is_authenticated
            and response.get("Content-Type", "").startswith("text/html")
            and not request.headers.get("HX-Request")
            and not request.path.startswith(self.SKIP)
        ):
            return
        if request.session.get(self.BACK_KEY) != request.get_full_path():
            request.session[self.BACK_KEY] = request.get_full_path()
