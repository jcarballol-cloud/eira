# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import views_dev as views

app_name = "dev"
urlpatterns = [
    path("mailbox/", views.mailbox, name="mailbox"),
    path("mailbox/<int:pk>/", views.mailbox, name="mail"),
    path("telegram/", views.telegram, name="telegram"),
    path("saida/", views.outbox, name="outbox"),
    path("tpv/<str:reference>/", views.tpv, name="tpv"),
    path("clave/", views.clave, name="clave"),
    path("lock-simulator/", views.lock_simulator, name="lock_simulator"),
    path("entrar-como/", views.login_as, name="login_as"),
]
