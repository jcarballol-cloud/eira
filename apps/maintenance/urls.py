# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import cleaning_views, views

app_name = "maintenance"
urlpatterns = [
    path("", views.my_orders, name="my_orders"),
    path("orde/<int:pk>/", views.order_detail, name="order"),
    path("calendario/", views.operator_calendar, name="calendar"),
    # v1.1 · QR de limpeza de cada zona
    path("limpeza/<str:token>/", cleaning_views.cleaning_zone, name="cleaning_zone"),
]
