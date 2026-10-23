# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import views

app_name = "notifications"
urlpatterns = [
    path("", views.list_view, name="list"),
    path("lidas/", views.mark_all_read, name="mark_all_read"),
    path("push/", views.subscribe_push, name="subscribe_push"),
]
