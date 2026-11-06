# SPDX-License-Identifier: EUPL-1.2
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from apps.bookings.notifications_view import gateway_notification
from apps.notifications.views import telegram_webhook
from apps.tenants import views as core
from apps.tenants.media import protected_serve

urlpatterns = [
    path("", core.home, name="home"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("acceso/", include("apps.accounts.urls")),
    path("conta/", include("apps.accounts.urls_account")),
    path("preferencias/", core.preferences, name="preferences"),
    path("rexion/<slug:region>/", include("apps.tenants.urls_region")),
    path("saude/", core.health, name="health"),
    path("offline/", core.offline, name="offline"),
    path("creditos/", core.credits, name="credits"),
    path("axuda/", core.help_guide, name="help_guide"),
    path("axuda/leeme/", core.leeme, name="leeme"),  # v1.5 · F
    path("modo-xestion/", core.desk_mode, name="desk_mode"),
    path("sw.js", core.service_worker, name="service_worker"),
    path("manifest.webmanifest", core.manifest, name="manifest"),
    path("pagamentos/notificacion/", gateway_notification, name="payment_notification"),
    path("telegram/webhook/<str:secret>/", telegram_webhook, name="telegram_webhook"),
    path("api/v1/", include("eira.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("c/<slug:tenant>/", include("eira.tenant_urls")),
]

if not settings.EIRA_PUBLIC_DEMO:
    urlpatterns.append(path("admin/", admin.site.urls))

if settings.EIRA_DEMO_TOOLS:
    urlpatterns.append(path("dev/", include("apps.integrations.urls_dev")))

# Ficheiros subidos: públicos (instalacións) ou privados con control de acceso (incidencias, ordes).
urlpatterns.append(path("media/<path:path>", protected_serve, name="media"))

handler404 = "apps.tenants.views.not_found"
handler403 = "apps.tenants.views.forbidden"
