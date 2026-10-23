# SPDX-License-Identifier: EUPL-1.2
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView

from apps.tenants import views as core

urlpatterns = [
    path("", core.home, name="home"),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("acceso/", include("apps.accounts.urls")),
    path("conta/", include("apps.accounts.urls_account")),
    path("preferencias/", core.preferences, name="preferences"),
    path("rexion/<slug:region>/", include("apps.tenants.urls_region")),
    path("saude/", core.health, name="health"),
    path("offline/", core.offline, name="offline"),
    path("sw.js", core.service_worker, name="service_worker"),
    path("manifest.webmanifest", core.manifest, name="manifest"),
    path("api/v1/", include("eira.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("c/<slug:tenant>/", include("eira.tenant_urls")),
]

if settings.EIRA_DEMO_TOOLS:
    urlpatterns.append(path("dev/", include("apps.integrations.urls_dev")))

# Ficheiros subidos: en produción sérveos o proxy inverso (ver docs/despregamento.md).
urlpatterns.append(path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}))

handler404 = "apps.tenants.views.not_found"
handler403 = "apps.tenants.views.forbidden"
