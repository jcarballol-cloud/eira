# SPDX-License-Identifier: EUPL-1.2
"""Rexistro no admin técnico de Django (só persoal con is_staff; a xestión diaria faise en /xestion/)."""

from django.apps import apps
from django.contrib import admin

# Os datos de saúde (art. 9) non se amosan nin sequera no admin técnico.
EXCLUDED = {"HealthProfile"}

for model in apps.get_app_config("accounts").get_models():
    if model.__name__ not in EXCLUDED and not admin.site.is_registered(model):
        admin.site.register(model)
