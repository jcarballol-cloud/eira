# SPDX-License-Identifier: EUPL-1.2
"""URLs dun concello: todas colgan de /c/<slug>/ (ou do subdominio do concello)."""

from django.urls import include, path

from apps.facilities import views as facilities
from apps.tenants import views as core

urlpatterns = [
    path("", facilities.home, name="tenant_home"),
    path("tema.css", core.theme_css, name="theme_css"),
    path("privacidade/", core.privacy, name="privacy"),
    path("privacidade/datos/", core.custody, name="privacy_custody"),
    path("privacidade/avaliacion-impacto/", core.dpia, name="privacy_dpia"),  # v1.3 · B
    path("seguridade/", core.safety, name="safety"),
    path("seguridade/", include("apps.safety.urls")),  # v1.2 · A: Aviso e Alerta
    path("accesibilidade/", core.accessibility, name="accessibility"),
    path("app/", include("eira.app_urls")),
    path("instalacions/", include("apps.facilities.urls")),
    path("reservas/", include("apps.bookings.urls")),
    path("acceso/", include("apps.access.urls")),
    path("incidencias/", include("apps.incidents.urls")),
    path("avisos/", include("apps.notifications.urls")),
    path("actividades/", include("apps.activities.urls")),
    path("monitor/", include("apps.activities.urls_monitor")),
    path("operario/", include("apps.maintenance.urls")),
    path("xestion/", include("eira.manage_urls")),
    path("datos-abertos/", include("apps.analytics.urls_open")),
    path("enquisa/", include("apps.surveys.urls")),  # v1.2 · E
    path("carne/", include("apps.members.urls")),  # v1.2 · H
]
