# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import opendata

app_name = "open_data"
urlpatterns = [
    path("", opendata.index, name="index"),
    path("ocupacion.csv", opendata.occupancy_csv, name="csv"),
    path("dcat.jsonld", opendata.dcat, name="dcat"),
]
