# SPDX-License-Identifier: EUPL-1.2
import json

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods

from .models import Municipality, Region
from .prefs import KEYS, read_prefs, write_prefs


def home(request):
    municipalities = Municipality.objects.filter(is_active=True).select_related("region")
    personas = []
    if settings.EIRA_DEMO_TOOLS:
        from apps.integrations.demo import DEMO_PERSONAS

        personas = DEMO_PERSONAS
    return render(request, "core/home.html", {
        "municipalities": municipalities, "regions": Region.objects.all(), "personas": personas,
    })


def _safe_next(request, fallback="/"):
    nxt = request.POST.get("next") or request.GET.get("next") or fallback
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = fallback
    return nxt


@require_http_methods(["GET", "POST"])
def preferences(request):
    if request.method == "POST":
        response = HttpResponse(status=303)
        response["Location"] = _safe_next(request)
        return write_prefs(response, {k: request.POST.get(k) == "on" for k in KEYS})
    return render(request, "core/preferences.html", {"next": _safe_next(request), "current": read_prefs(request)})


def health(request):
    return render(request, "core/health.html", {"nav": "health"})


def offline(request):
    return render(request, "core/offline.html")


@cache_control(no_cache=True)
def service_worker(request):
    response = render(request, "core/sw.js", {"version": "eira-v1"}, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response


def manifest(request):
    data = {
        "name": "Eira · Deportes municipais",
        "short_name": "Eira",
        "description": _("Reserva e acceso ás instalacións deportivas municipais."),
        "lang": "gl",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#F7F4EC",
        "theme_color": "#16252B",
        "icons": [
            {"src": static("img/eira-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("img/eira-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            {"src": static("img/eira.svg"), "sizes": "any", "type": "image/svg+xml"},
        ],
        "shortcuts": [
            {"name": _("A miña saúde"), "url": reverse("health")},
        ],
    }
    return HttpResponse(json.dumps(data, ensure_ascii=False), content_type="application/manifest+json")


def theme_css(request):
    color = request.tenant.accent_color
    css = f":root {{ --accent: {color}; }}\n"
    response = HttpResponse(css, content_type="text/css")
    response["Cache-Control"] = "public, max-age=300"
    return response


def privacy(request):
    return render(request, "core/privacy.html", {"min_aggregation": settings.EIRA_MIN_AGGREGATION})


def accessibility(request):
    return render(request, "core/accessibility.html")


def not_found(request, exception=None):
    return render(request, "core/error.html", {"code": 404, "title": _("Non atopamos esta páxina")}, status=404)


def forbidden(request, exception=None):
    return render(request, "core/error.html", {"code": 403, "title": _("Non tes permiso para ver isto")}, status=403)
