# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import monitor

app_name = "monitor"
urlpatterns = [
    path("", monitor.today, name="today"),
]
