# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import views

app_name = "maintenance"
urlpatterns = [
    path("", views.my_orders, name="my_orders"),
    path("orde/<int:pk>/", views.order_detail, name="order"),
    path("calendario/", views.operator_calendar, name="calendar"),
]
