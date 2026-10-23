# SPDX-License-Identifier: EUPL-1.2
"""Área de xestión do concello: /c/<slug>/xestion/…"""

from django.urls import path

from apps.access import views as access
from apps.activities import views as activities
from apps.analytics import views as analytics
from apps.bookings import manage as bookings
from apps.facilities import manage as facilities
from apps.incidents import manage as incidents
from apps.maintenance import views as maintenance
from apps.tenants import manage as tenant
from apps.tenants import portability

app_name = "manage"
urlpatterns = [
    path("", bookings.dashboard, name="dashboard"),
    path("axenda/", bookings.agenda, name="agenda"),
    path("reservar/", bookings.on_behalf, name="on_behalf"),
    path("reservas/<int:pk>/chave/<slug:action>/", bookings.key_action, name="key_action"),
    path("reservas/<int:pk>/cancelar/", bookings.staff_cancel, name="staff_cancel"),
    path("instalacions/", facilities.facility_list, name="facilities"),
    path("instalacions/nova/", facilities.facility_new, name="facility_new"),
    path("instalacions/<int:pk>/", facilities.facility_edit, name="facility_edit"),
    path("instalacions/<int:pk>/revisar/", facilities.facility_review, name="facility_review"),
    path("instalacions/<int:pk>/horario/", facilities.facility_hours, name="facility_hours"),
    path("instalacions/<int:pk>/tarifas/", facilities.facility_tariffs, name="facility_tariffs"),
    path("instalacions/<int:pk>/normas/", facilities.facility_rules, name="facility_rules"),
    path("instalacions/<int:pk>/qr/", access.facility_qr, name="facility_qr"),
    path("peches/", facilities.closures, name="closures"),
    path("peches/<int:pk>/eliminar/", facilities.closure_delete, name="closure_delete"),
    path("peches/alerta/", tenant.weather_alert, name="weather_alert"),
    path("incidencias/", incidents.incident_list, name="incidents"),
    path("incidencias/<int:pk>/", incidents.incident_detail, name="incident_detail"),
    path("mantemento/", maintenance.plans, name="maintenance_plans"),
    path("actividades/", activities.manage_groups, name="activities"),
    path("indicadores/", analytics.dashboard, name="indicators"),
    path("configuracion/", tenant.settings_view, name="settings"),
    path("persoal/", tenant.staff, name="staff"),
    path("persoal/empadroamento/", tenant.issue_invitation, name="issue_invitation"),
    path("portabilidade/", portability.page, name="portability"),
    path("portabilidade/exportar.zip", portability.export_view, name="export"),
    path("portabilidade/importar/", portability.import_view, name="import"),
]
