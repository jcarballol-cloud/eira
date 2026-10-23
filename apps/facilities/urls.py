# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from apps.bookings import views as bookings

from . import views

app_name = "facilities"
urlpatterns = [
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/reservar/", bookings.book, name="book"),
]
