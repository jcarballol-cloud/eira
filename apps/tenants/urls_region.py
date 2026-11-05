# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from apps.analytics.provenance_views import region_panel
from apps.legal import views as legal

from . import region

app_name = "region"
urlpatterns = [
    path("", region.dashboard, name="dashboard"),
    path("novo-concello/", region.new_municipality, name="new_municipality"),
    path("mobilidade/", region_panel, name="mobility"),  # v1.5 · C
    # v1.5 · D: repositorio de modelos de documentos legais
    path("legal/", legal.region_list, name="legal"),
    path("legal/<slug:kind>/", legal.region_publish, name="legal_publish"),
    path(
        "concello/<slug:slug>/reenviar-invitacion/",
        region.resend_invitation,
        name="resend_invitation",
    ),
    path(
        "concello/<slug:slug>/solicitar-soporte/",
        region.request_support,
        name="request_support",
    ),
]
