# SPDX-License-Identifier: EUPL-1.2
"""Perfís ficticios para a demostración (selector na portada). Ningún dato é real."""

from django.utils.translation import gettext_lazy as _

DEMO_PERSONAS = [
    {"email": "uxia@demo.eira.example", "name": "Uxía", "tenant": "vilardeiras", "initials": "U",
     "role": _("Veciña nova, usa o móbil"), "goal": _("Reserva a pista de pádel e abre co código.")},
    {"email": "manuel@demo.eira.example", "name": "Manuel", "tenant": "vilardeiras", "initials": "M",
     "role": _("Veciño maior, lector de pantalla e texto grande"), "goal": _("Reserva o ximnasio por voz e teclado."),
     "prefs": "large_text"},
    {"email": "irene@demo.eira.example", "name": "Irene", "tenant": "vilardeiras", "initials": "I",
     "role": _("Non empadroada (outra tarifa)"), "goal": _("Ve a tarifa de non empadroadas.")},
    {"email": "admin@vilardeiras.demo.eira.example", "name": "Concello de Vilardeiras", "tenant": "vilardeiras",
     "initials": "CV", "role": _("Administración do concello"), "goal": _("Panel do día, alta asistida e indicadores.")},
    {"email": "brais@demo.eira.example", "name": "Brais", "tenant": "vilardeiras", "initials": "B",
     "role": _("Operario de mantemento"), "goal": _("Ordes do día, checklist con foto, sen conexión.")},
    {"email": "antia@demo.eira.example", "name": "Antía", "tenant": "vilardeiras", "initials": "A",
     "role": _("Monitora deportiva"), "goal": _("Asistencia na tableta e escala de esforzo.")},
    {"email": "deputacion@demo.eira.example", "name": "Deputación das Marismas", "tenant": None, "region": "marismas",
     "initials": "DM", "role": _("Administración da deputación"), "goal": _("Compara concellos e dá de alta un novo.")},
]
