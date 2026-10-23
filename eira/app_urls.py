# SPDX-License-Identifier: EUPL-1.2
"""App móbil da veciñanza: /c/<slug>/app/…"""

from django.urls import path

from apps.tenants import app_home

app_name = "app"
urlpatterns = [
    path("", app_home.home, name="home"),
]
