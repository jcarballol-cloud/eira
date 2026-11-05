# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from apps.legal import views as legal

from . import twofactor, views

app_name = "account"
urlpatterns = [
    path("", views.profile, name="profile"),
    path("privacidade/", views.privacy_centre, name="privacy"),
    path("empadroamento/", views.redeem_residency, name="residency"),
    path("os-meus-datos.json", views.export_data, name="export"),
    path("eliminar/", views.delete_account, name="delete"),
    path("familia/", views.household, name="household"),
    # v1.5 · D: o que aceptou a persoa e retirada de consentimentos
    path("documentos/", legal.my_documents, name="legal"),
    path("documentos/<int:pk>/retirar/", legal.withdraw, name="legal_withdraw"),
    # v1.3 · C: dobre factor e códigos de recuperación
    path("seguridade/", twofactor.security, name="security"),
    path("seguridade/codigos/", twofactor.security_codes, name="security_codes"),
    path(
        "familia/<int:dependent_id>/consentimento/<slug:kind>/",
        views.consent_toggle,
        name="consent_toggle",
    ),
]
