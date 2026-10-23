# SPDX-License-Identifier: EUPL-1.2
import json

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods

from .models import Municipality, Region
from .prefs import KEYS, read_prefs, write_prefs


def home(request):
    request.layout_override = "public"
    municipalities = Municipality.objects.filter(is_active=True).select_related("region")
    ctx = {"municipalities": municipalities, "regions": Region.objects.all()}
    if settings.EIRA_DEMO_TOOLS:
        # Portada da demo en dous pasos: 1) concello (ou deputación) e 2) quen es nese concello
        from apps.integrations.demo import DEMO_PERSONAS, DEMO_TENANTS

        by_slug = {m.slug: m for m in municipalities}
        tenants = [{**t, "m": by_slug[t["slug"]]} for t in DEMO_TENANTS if t["slug"] in by_slug]
        chosen = next((t for t in tenants if t["slug"] == request.GET.get("concello")), None)
        ctx.update(
            {
                "demo_tenants": tenants,
                "chosen": chosen,
                "personas": [p for p in DEMO_PERSONAS if chosen and p["tenant"] == chosen["slug"]],
                "region_persona": next((p for p in DEMO_PERSONAS if p.get("region")), None),
            }
        )
    return render(request, "core/home.html", ctx)


def _safe_next(request, fallback="/"):
    nxt = request.POST.get("next") or request.GET.get("next") or fallback
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = fallback
    return nxt


@require_http_methods(["GET", "POST"])
def preferences(request):
    request.layout_override = "public"
    if request.method == "POST":
        response = HttpResponse(status=303)
        response["Location"] = _safe_next(request)
        return write_prefs(response, {k: request.POST.get(k) == "on" for k in KEYS})
    return render(
        request,
        "core/preferences.html",
        {"next": _safe_next(request), "current": read_prefs(request)},
    )


def health(request):
    """A miña saúde: no dispositivo por defecto; na conta só con consentimento explícito (art. 9)."""
    from decimal import Decimal, InvalidOperation

    from django.contrib import messages
    from django.shortcuts import redirect

    from apps.accounts.models import HealthProfile, audit

    user = request.user if request.user.is_authenticated else None
    profile = HealthProfile.objects.filter(user=user).first() if user else None
    error = ""
    if request.method == "POST" and user:
        if request.POST.get("action") == "forget":
            if profile:
                profile.delete()
                audit("health.delete", user, obj=user)
            messages.success(request, _("Borramos os teus datos de saúde da conta."))
            return redirect("health")
        if request.POST.get("consent") != "1":
            error = _("Para gardalos na conta tes que marcar o consentimento.")
        else:

            def num(key, cast, lo, hi):
                try:
                    v = cast(request.POST.get(key, "").replace(",", "."))
                except (ValueError, InvalidOperation):
                    return None
                return v if lo <= v <= hi else None

            HealthProfile.objects.update_or_create(
                user=user,
                defaults={
                    "weight_kg": num("weight", Decimal, 15, 250),
                    "age": num("age", int, 5, 110),
                    "weekly_minutes": num("minutes", int, 0, 3000),
                    "consent_version": HealthProfile.CONSENT_VERSION,
                    "consent_at": profile.consent_at if profile else timezone.now(),
                },
            )
            audit("health.store", user, obj=user)
            messages.success(request, _("Gardado na túa conta. Podes borralo cando queiras."))
            return redirect("health")
    return render(
        request,
        "core/health.html",
        {
            "nav": "health",
            "account_profile": profile.as_dict() if profile else None,
            "error": error,
        },
    )


def offline(request):
    return render(request, "core/offline.html")


@cache_control(no_cache=True)
def service_worker(request):
    response = render(
        request, "core/sw.js", {"version": "eira-v1"}, content_type="application/javascript"
    )
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
            {
                "src": static("img/eira-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {"src": static("img/eira.svg"), "sizes": "any", "type": "image/svg+xml"},
        ],
        "shortcuts": [
            {"name": _("A miña saúde"), "url": reverse("health")},
        ],
    }
    return HttpResponse(
        json.dumps(data, ensure_ascii=False), content_type="application/manifest+json"
    )


def theme_css(request):
    color = request.tenant.accent_color
    css = f":root {{ --accent: {color}; }}\n"
    response = HttpResponse(css, content_type="text/css")
    response["Cache-Control"] = "public, max-age=300"
    return response


def credits(request):
    """Créditos das fotos de referencia (atribución esixida por CC BY e CC BY-SA)."""
    from apps.facilities.photos import ALT
    from apps.facilities.photos import credits as photo_credits

    items = [{**c, "alt": ALT.get(c["file"], "")} for c in photo_credits()]
    return render(request, "core/credits.html", {"items": items})


def privacy(request):
    return render(request, "core/privacy.html", {"min_aggregation": settings.EIRA_MIN_AGGREGATION})


def accessibility(request):
    return render(request, "core/accessibility.html")


def not_found(request, exception=None):
    return render(
        request,
        "core/error.html",
        {"code": 404, "title": _("Non atopamos esta páxina")},
        status=404,
    )


def forbidden(request, exception=None):
    ctx = {"code": 403, "title": _("Non tes permiso para ver isto")}
    if getattr(request, "support_denied", False):
        # Deputación sen acceso de soporte: explícase e pódese solicitar ao concello
        ctx.update(
            {
                "title": _("Datos persoais: precisa acceso de soporte"),
                "support_denied": True,
                "region_slug": request.tenant.region.slug if request.tenant.region else "",
            }
        )
    return render(request, "core/error.html", ctx, status=403)
