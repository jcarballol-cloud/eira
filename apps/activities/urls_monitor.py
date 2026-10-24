# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import monitor

app_name = "monitor"
urlpatterns = [
    path("", monitor.today, name="today"),
    path("sesion/<int:pk>/rexistro/", monitor.kiosk, name="kiosk"),
    path("sesion/<int:pk>/rexistro/api/", monitor.kiosk_api, name="kiosk_api"),
    path("sesion/<int:pk>/asistencia/", monitor.attendance, name="attendance"),
    path("sesion/<int:pk>/engadir/", monitor.add_pending, name="add_pending"),
    path("sesion/<int:pk>/esforzo/", monitor.effort, name="effort"),
    path("grupo/<int:pk>/probas/", monitor.fitness, name="fitness"),
    path("estatisticas/", monitor.stats, name="stats"),
]
