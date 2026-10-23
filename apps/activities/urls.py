# SPDX-License-Identifier: EUPL-1.2
from django.urls import path

from . import views

app_name = "activities"
urlpatterns = [
    path("", views.activity_list, name="list"),
    path("grupo/<int:pk>/inscribirse/", views.enroll, name="enroll"),
    path("as-minas/", views.mine, name="mine"),
    path("inscricion/<int:pk>/pagamento/", views.payment_return, name="payment_return"),
    path("inscricion/<int:pk>/baixa/", views.cancel, name="cancel"),
    path("observatorio/", views.observatory_view, name="observatory"),
]
