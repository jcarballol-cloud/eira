# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import opengames_views, views, vouchers, waitlist_views

app_name = "bookings"
urlpatterns = [
    path("", views.mine, name="mine"),
    path("calendario.ics", views.ics_all, name="ics_all"),
    path("bonos/", vouchers.my_vouchers, name="vouchers"),
    path("<int:pk>/", views.detail, name="detail"),
    # v1.2 · F
    path("<int:pk>/confirmo/", waitlist_views.confirm, name="confirm"),
    path("<int:pk>/cancelo/", waitlist_views.quick_cancel, name="quick_cancel"),
    path("agardar/<int:facility_pk>/", waitlist_views.join, name="waitlist_join"),
    path("lista-de-espera/<int:pk>/", waitlist_views.offer, name="waitlist_offer"),
    # v1.2 · G
    path("<int:pk>/busco-xente/", opengames_views.publish, name="game_publish"),
    path("partidas/", opengames_views.games, name="games"),
    path("partidas/<int:pk>/", opengames_views.game, name="game"),
    path("<int:pk>/pagamento/", views.payment_return, name="payment_return"),
    path("<int:pk>/pagar/", views.retry_payment, name="retry_payment"),
    path("<int:pk>/cancelar/", views.cancel, name="cancel"),
    path("<int:pk>/cambiar/", views.modify, name="modify"),
    path("<int:pk>/recibo/", views.receipt, name="receipt"),
    path("<int:pk>/reserva.ics", views.ics_one, name="ics"),
    path("<int:pk>/peche/", views.checklist, name="checklist"),
    path("<int:pk>/estado-inicial/", views.start_state, name="start_state"),
    path("<int:pk>/valorar/", views.rate, name="rate"),
    path("<int:pk>/abrir/", views.open_lock, name="open"),
]
