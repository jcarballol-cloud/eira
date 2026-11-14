# SPDX-License-Identifier: EUPL-1.2
"""Idioma da interface (14/11/2026): o galego é sempre o de partida.

Orde: o que a persoa escolleu no selector (no perfil se ten sesión; nunha cookie se non) → o idioma
por defecto do concello (galego de serie) → `LANGUAGE_CODE` (galego). **Nunca** a cabeceira
Accept-Language do navegador: un móbil configurado en castelán non debe cambiar o idioma de
partida dun servizo municipal galego.
"""

from django.conf import settings
from django.utils import translation
from django.utils.cache import patch_vary_headers


def valid(code):
    return code if code in dict(settings.LANGUAGES) else ""


def uses_profile(user):
    """Na demo pública as contas son compartidas (Uxía é de todo o mundo): a escolla queda só na
    cookie de cada navegador, para que quen entre despois siga vendo o galego."""
    return (
        user is not None
        and user.is_authenticated
        and not settings.EIRA_PUBLIC_DEMO
        and bool(valid(user.preferred_language))
    )


def chosen(request):
    """O idioma que a persoa escolleu, ou "" se nunca escolleu ningún."""
    user = getattr(request, "user", None)
    if uses_profile(user):
        return user.preferred_language
    return valid(request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME, ""))


def default_for(tenant):
    return valid(getattr(tenant, "default_language", "")) or settings.LANGUAGE_CODE


def use(request, code):
    translation.activate(code)
    request.LANGUAGE_CODE = code


def _tenant_outside_its_urls(request):
    """Fóra de /c/<slug>/ (entrar, axuda, accesibilidade…): o concello do dominio ou o último
    visitado, se o hai, para usar o seu idioma por defecto."""
    from .models import Municipality

    slug = getattr(request, "host_tenant_slug", "")
    if not slug:
        session = getattr(request, "session", None)
        slug = session.get("last_tenant", "") if session is not None else ""
    if not slug:
        return None
    return Municipality.objects.filter(slug=slug, is_active=True).only("default_language").first()


class LanguageMiddleware:
    """Substitúe a `LocaleMiddleware` de Django, que lería Accept-Language."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        code = chosen(request)
        request.language_chosen = bool(code)
        use(request, code or default_for(_tenant_outside_its_urls(request)))
        response = self.get_response(request)
        response.headers.setdefault("Content-Language", translation.get_language())
        patch_vary_headers(response, ("Cookie",))
        # Co perfil gardado, a cookie segue o perfil: ao saír da sesión mantense o idioma
        user = getattr(request, "user", None)
        cookie = settings.LANGUAGE_COOKIE_NAME
        if (
            uses_profile(user)
            and request.COOKIES.get(cookie) != user.preferred_language
            and cookie not in response.cookies
        ):
            response.set_cookie(
                cookie,
                user.preferred_language,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE or "Lax",
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
            )
        return response


def apply_tenant_default(request, tenant):
    """Chamado ao resolver o concello da URL: se a persoa non escolleu idioma, o do concello."""
    if not getattr(request, "language_chosen", True):
        use(request, default_for(tenant))
