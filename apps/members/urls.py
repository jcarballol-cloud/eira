# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import views

app_name = "members"
urlpatterns = [
    path("", views.card, name="card"),
    path("qr/", views.card_qr, name="card_qr"),
    path("carne.pdf", views.card_pdf, name="card_pdf"),
]
