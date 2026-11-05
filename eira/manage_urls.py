# SPDX-License-Identifier: EUPL-1.2
"""Área de xestión do concello: /c/<slug>/xestion/…"""

from django.urls import path

from apps.access import views as access
from apps.accounts import auditlog, breaches, signup
from apps.activities import views as activities
from apps.analytics import performance_views as performance
from apps.analytics import provenance_views as provenance
from apps.analytics import views as analytics
from apps.bookings import manage as bookings
from apps.bookings import vouchers
from apps.facilities import manage as facilities
from apps.incidents import manage as incidents
from apps.legal import views as legal
from apps.maintenance import cleaning_views as cleaning
from apps.maintenance import views as maintenance
from apps.members import views as members
from apps.notifications import manage as notices
from apps.safety import manage as safety
from apps.surveys import views as surveys
from apps.tenants import manage as tenant
from apps.tenants import portability

app_name = "manage"
urlpatterns = [
    path("", bookings.dashboard, name="dashboard"),
    path("axenda/", bookings.agenda, name="agenda"),
    path("reservar/", bookings.on_behalf, name="on_behalf"),
    path("reservas/<int:pk>/", bookings.booking_detail, name="booking"),
    path("reservas/<int:pk>/chave/<slug:action>/", bookings.key_action, name="key_action"),
    path("cobros/", bookings.payments_list, name="payments"),
    path("cobros/bonos/", vouchers.manage_vouchers, name="vouchers"),
    path("valoracions/", bookings.ratings_view, name="ratings"),
    path("cobros/<int:pk>/devolver/", bookings.payment_refund, name="payment_refund"),
    path("reservas/<int:pk>/cancelar/", bookings.staff_cancel, name="staff_cancel"),
    path("instalacions/", facilities.facility_list, name="facilities"),
    path("instalacions/nova/", facilities.facility_new, name="facility_new"),
    path("instalacions/<int:pk>/", facilities.facility_edit, name="facility_edit"),
    path("instalacions/<int:pk>/revisar/", facilities.facility_review, name="facility_review"),
    path("instalacions/<int:pk>/horario/", facilities.facility_hours, name="facility_hours"),
    path("instalacions/<int:pk>/tarifas/", facilities.facility_tariffs, name="facility_tariffs"),
    path("instalacions/<int:pk>/normas/", facilities.facility_rules, name="facility_rules"),
    path("instalacions/<int:pk>/qr/", access.facility_qr, name="facility_qr"),
    # v1.2 · D: rendemento
    path(
        "instalacions/<int:pk>/rendemento/",
        performance.facility_performance,
        name="facility_performance",
    ),
    path("rendemento/", performance.overview, name="performance"),
    path("instalacions/<int:pk>/cartel.pdf", facilities.facility_poster, name="facility_poster"),
    path("instalacions/cartel-modelo.pdf", facilities.poster_template, name="poster_template"),
    path(
        "instalacions/<int:pk>/revision-seguridade/",
        facilities.safety_review,
        name="facility_safety_review",
    ),
    path("peches/", facilities.closures, name="closures"),
    path("peches/<int:pk>/eliminar/", facilities.closure_delete, name="closure_delete"),
    path("peches/alerta/", tenant.weather_alert, name="weather_alert"),
    path("avisos/", notices.notice_list, name="notices"),
    path("avisos/novo/", notices.notice_new, name="notice_new"),
    path("avisos/<int:pk>/", notices.notice_detail, name="notice"),
    path("incidencias/", incidents.incident_list, name="incidents"),
    path("incidencias/<int:pk>/", incidents.incident_detail, name="incident_detail"),
    path("mantemento/", maintenance.plans, name="maintenance_plans"),
    path("mantemento/calendario/", maintenance.manage_calendar, name="maintenance_calendar"),
    path("ordes/", maintenance.manage_orders, name="work_orders"),
    path("ordes/<int:pk>/", maintenance.manage_order, name="work_order"),
    path("limpeza/", cleaning.manage_cleaning, name="cleaning"),
    path("limpeza/rexistro/", cleaning.cleaning_export, name="cleaning_export"),
    path("limpeza/zona/<int:pk>/qr/", cleaning.zone_qr, name="cleaning_qr"),
    path("actividades/", activities.manage_groups, name="activities"),
    path("actividades/grupo/<int:pk>/", activities.manage_group, name="group"),
    path("actividades/acreditacions/", activities.accreditations, name="accreditations"),  # v1.5
    path("indicadores/", analytics.dashboard, name="indicators"),
    path("procedencia/", provenance.panel, name="provenance"),  # v1.5 · C
    path("configuracion/", tenant.settings_view, name="settings"),
    path("persoal/", tenant.staff, name="staff"),
    path("altas/", signup.signups, name="signups"),
    path("altas/<int:pk>/resolver/", signup.signup_resolve, name="signup_resolve"),
    path("altas/<int:pk>/folla/", signup.signup_sheet, name="signup_sheet"),
    path("altas/padron/", signup.padron_page, name="padron"),
    path("altas/padron/modelo.csv", signup.padron_template, name="padron_template"),
    path("actividades/pendentes/<int:pk>/", activities.pending_resolve, name="pending_resolve"),
    path("persoal/empadroamento/", tenant.issue_invitation, name="issue_invitation"),
    path("portabilidade/", portability.page, name="portability"),
    path("privacidade/brechas/", breaches.breach_list, name="breaches"),
    path("privacidade/auditoria/", auditlog.audit_log, name="audit"),  # v1.3 · C
    path("privacidade/brechas/nova/", breaches.breach_edit, name="breach_new"),
    path("privacidade/brechas/<int:pk>/", breaches.breach_edit, name="breach"),
    path(
        "privacidade/brechas/<int:pk>/comunicacion/",
        breaches.breach_communication,
        name="breach_communication",
    ),
    # v1.2 · A e B: alertas, responsables, protocolo, peches sen confirmar e accidentes
    path("seguridade/", safety.safety_home, name="safety"),
    path(
        "seguridade/responsables/<int:pk>/eliminar/",
        safety.contact_delete,
        name="safety_contact_delete",
    ),
    path("seguridade/protocolo/", safety.protocol_edit, name="safety_protocol"),
    path("seguridade/peches/<int:pk>/", safety.escalation_detail, name="safety_escalation"),
    path("seguridade/accidentes/", safety.accidents, name="accidents"),
    # v1.5 · D: documentos legais
    path("legal/", legal.manage_list, name="legal"),
    path("legal/rexistro.csv", legal.manage_register, name="legal_register"),
    path("legal/<slug:kind>/", legal.manage_publish, name="legal_publish"),
    # v1.2 · H: abonos e carné
    path("abonos/", members.manage_passes, name="passes"),
    path("carne/", members.reader, name="card_reader"),
    path("carne/<int:pk>/anular/", members.revoke, name="card_revoke"),
    # v1.2 · E: enquisa anual con NPS
    path("enquisas/", surveys.manage_list, name="surveys"),
    path("enquisas/<int:pk>/", surveys.manage_detail, name="survey"),
    path("enquisas/<int:pk>/avisar/", surveys.announce, name="survey_announce"),
    path("portabilidade/exportar.zip", portability.export_view, name="export"),
    path("portabilidade/importar/", portability.import_view, name="import"),
]
