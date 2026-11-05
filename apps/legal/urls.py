# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import views

app_name = "legal"
urlpatterns = [
    path("", views.document_list, name="list"),
    path("<slug:kind>/", views.document_detail, name="detail"),
]
