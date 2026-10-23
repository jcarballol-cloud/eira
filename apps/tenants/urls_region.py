# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import region

app_name = "region"
urlpatterns = [
    path("", region.dashboard, name="dashboard"),
    path("novo-concello/", region.new_municipality, name="new_municipality"),
    path(
        "concello/<slug:slug>/reenviar-invitacion/",
        region.resend_invitation,
        name="resend_invitation",
    ),
]
