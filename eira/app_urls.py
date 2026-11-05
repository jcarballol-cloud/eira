# SPDX-License-Identifier: EUPL-1.2
"""App móbil da veciñanza: /c/<slug>/app/…"""

from django.urls import path

from apps.accounts import signup
from apps.tenants import app_home, network

app_name = "app"
urlpatterns = [
    path("", app_home.home, name="home"),
    path("solicitar/", signup.request_app, name="request"),
    path("solicitar/enviada/", signup.request_done, name="request_done"),
    path("instalar/", signup.install, name="install"),
    path("benvida/", signup.welcome, name="welcome"),
    path("proximos/", network.nearby, name="nearby"),
    path("proximos/ir/", network.go, name="nearby_go"),
    path("proximos/seguir/", network.follow, name="nearby_follow"),
    path("proximos/residencia/", network.residence, name="residence"),  # v1.5 · C
]
