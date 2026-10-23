# SPDX-License-Identifier: EUPL-1.2
"""Rexistro no admin técnico de Django (só persoal con is_staff; a xestión diaria faise en /xestion/)."""

from django.apps import apps
from django.contrib import admin

for model in apps.get_app_config("maintenance").get_models():
    if not admin.site.is_registered(model):
        admin.site.register(model)
