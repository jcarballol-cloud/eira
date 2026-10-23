# SPDX-License-Identifier: EUPL-1.2
from django.urls import include, path
from rest_framework.routers import DefaultRouter, SimpleRouter

from . import api

root = DefaultRouter()
root.register("municipalities", api.MunicipalityViewSet, basename="municipality")

tenant = SimpleRouter(use_regex_path=False)
tenant.register("facilities", api.FacilityViewSet, basename="facility")
tenant.register("bookings", api.BookingViewSet, basename="booking")
tenant.register("incidents", api.IncidentViewSet, basename="incident")

urlpatterns = [
    path("", include(root.urls)),
    path("municipalities/<slug:municipality_slug>/", include(tenant.urls)),
]
