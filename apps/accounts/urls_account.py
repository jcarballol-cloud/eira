# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import views

app_name = "account"
urlpatterns = [
    path("", views.profile, name="profile"),
    path("privacidade/", views.privacy_centre, name="privacy"),
    path("empadroamento/", views.redeem_residency, name="residency"),
    path("os-meus-datos.json", views.export_data, name="export"),
    path("eliminar/", views.delete_account, name="delete"),
    path("familia/", views.household, name="household"),
    path(
        "familia/<int:dependent_id>/consentimento/<slug:kind>/",
        views.consent_toggle,
        name="consent_toggle",
    ),
]
