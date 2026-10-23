# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import views

app_name = "access"
urlpatterns = [
    path("entrada/<str:token>/", views.checkin, name="checkin"),
    path("qr/<int:pk>/", views.facility_qr, name="qr"),
]
