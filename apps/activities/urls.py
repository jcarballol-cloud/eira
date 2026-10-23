# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import views

app_name = "activities"
urlpatterns = [
    path("", views.activity_list, name="list"),
]
