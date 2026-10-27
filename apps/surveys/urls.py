# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import views

app_name = "surveys"
urlpatterns = [path("", views.answer, name="answer")]
