# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import twofactor, views

app_name = "accounts"
urlpatterns = [
    path("", views.login_email, name="login"),
    path("codigo/", views.login_code, name="code"),
    path("clave/", views.identity_start, name="identity_start"),
    path("clave/volta/", views.identity_callback, name="identity_callback"),
    path("sair/", views.logout_view, name="logout"),
    path("dobre-factor/", twofactor.verify, name="two_factor"),  # v1.3
]
