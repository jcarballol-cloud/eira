# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import views

app_name = "incidents"
urlpatterns = [
    path("nova/", views.new, name="new"),
    path("<int:pk>/", views.detail, name="detail"),
]
