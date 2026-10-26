# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import views, vouchers

app_name = "bookings"
urlpatterns = [
    path("", views.mine, name="mine"),
    path("calendario.ics", views.ics_all, name="ics_all"),
    path("bonos/", vouchers.my_vouchers, name="vouchers"),
    path("<int:pk>/", views.detail, name="detail"),
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
