# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import views

app_name = "safety"
urlpatterns = [
    path("alerta/", views.alert_choice, name="alert"),
    path("alerta/accidente/", views.alert_accident, name="alert_accident"),
    path("alerta/emerxencia/", views.alert_security, name="alert_security"),
    path("emerxencia/", views.emergency, name="emergency"),
    path("accidente/", views.protocol, name="protocol"),
    path("accidente/<int:facility_pk>/", views.protocol, name="protocol_facility"),
    path("accidente/<int:facility_pk>/rexistrar/", views.accident_register, name="register"),
    path("peche/<str:token>/", views.closing_contact, name="closing"),
]
