# SPDX-License-Identifier: EUPL-1.2
"""Perfís ficticios para a demostración. Ningún dato é real.

A portada da demo vai en dous pasos: 1) escoller concello (ou a deputación) e 2) escoller quen es
dentro dese concello. Cada perfil di que verá e onde entra.
"""

from django.utils.translation import gettext_lazy as _

DEMO_TENANTS = [
    {
        "slug": "vilardeiras",
        "kind": _("Rural pequeno"),
        "summary": _(
            "1.840 habitantes e 6 instalacións repartidas por parroquias, a maioría sen conserxe: "
            "chave custodiada, código sen conexión ou QR. Ten escolas deportivas."
        ),
    },
    {
        "slug": "pontedouro",
        "kind": _("Mediano"),
        "summary": _(
            "14.250 habitantes, piscina e pavillóns con pechadura conectada e moitas máis reservas. "
            "Na demo non ten escolas."
        ),
    },
]

# v4.1: veciño novo sen actividade (o seed créao ao final, para que non reciba nada)
NEW_NEIGHBOUR = "brais.novo@demo.eira.example"

# «sees»: a ferramenta que abre; «lands»: a pantalla de inicio; «thumb»: miniatura en static/img/demo/
DEMO_PERSONAS = [
    {
        "email": "uxia@demo.eira.example",
        "name": "Uxía",
        "tenant": "vilardeiras",
        "initials": "U",
        "role": _("Persoa usuaria"),
        "sees": _("App da veciñanza"),
        "lands": _("Abre no inicio da app: a próxima reserva co código de acceso e os atallos."),
        "thumb": "app",
    },
    {
        "email": "manuel@demo.eira.example",
        "name": "Manuel",
        "tenant": "vilardeiras",
        "initials": "M",
        "role": _("Persoa maior, con texto grande"),
        "sees": _("App da veciñanza en texto grande"),
        "lands": _("A mesma app, coas preferencias de lectura activadas."),
        "thumb": "app-grande",
        "prefs": "large_text",
    },
    {
        "email": "irene@demo.eira.example",
        "name": "Irene",
        "tenant": "vilardeiras",
        "initials": "I",
        "role": _("Visitante sen empadroamento"),
        "sees": _("App da veciñanza"),
        "lands": _("Ve as tarifas de non empadroadas."),
        "thumb": "app",
    },
    {
        "email": NEW_NEIGHBOUR,
        "name": "Brais",
        "tenant": "vilardeiras",
        "initials": "B",
        "role": _("Alta nova, sen actividade"),
        "sees": _("App da veciñanza sen actividade"),
        "lands": _(
            "Acaba de darse de alta: sen reservas, avisos nin inscricións (estados baleiros)."
        ),
        "thumb": "app",
    },
    {
        "email": "admin@vilardeiras.demo.eira.example",
        "name": "Concello de Vilardeiras",
        "tenant": "vilardeiras",
        "initials": "CV",
        "role": _("Persoal do concello"),
        "sees": _("Panel do concello (escritorio)"),
        "lands": _("Abre no panel do día: reservas de hoxe, incidencias, cobros e axenda."),
        "thumb": "concello",
    },
    {
        "email": "brais@demo.eira.example",
        "name": "Brais",
        "tenant": "vilardeiras",
        "initials": "B",
        "role": _("Persoal de mantemento"),
        "sees": _("App do operario (móbil)"),
        "lands": _("Abre nas súas ordes de traballo; funciona sen cobertura."),
        "thumb": "operario",
    },
    {
        # v1.1 · rexistro de limpeza
        "email": "noela@demo.eira.example",
        "name": "Noela",
        "tenant": "vilardeiras",
        "initials": "N",
        "role": _("Persoal de limpeza (empresa contratada)"),
        "sees": _("App de limpeza (móbil)"),
        "lands": _(
            "Abre nas súas tarefas e zonas. Escanea o QR de cada zona para rexistrar a "
            "limpeza; funciona sen cobertura. Os aseos do pavillón van atrasados."
        ),
        "thumb": "limpeza",
    },
    {
        "email": "antia@demo.eira.example",
        "name": "Antía",
        "tenant": "vilardeiras",
        "initials": "A",
        "role": _("Persoa monitora"),
        "sees": _("Tableta da monitora"),
        "lands": _("Abre nas sesións de hoxe; o rexistro de asistencia e esforzo vai na tableta."),
        "thumb": "tableta",
    },
    {
        "email": "rosa@demo.eira.example",
        "name": "Rosa",
        "tenant": "pontedouro",
        "initials": "R",
        "role": _("Persoa usuaria"),
        "sees": _("App da veciñanza"),
        "lands": _("Abre no inicio da app de Pontedouro (piscina e pavillóns)."),
        "thumb": "app",
    },
    {
        "email": "admin@pontedouro.demo.eira.example",
        "name": "Concello de Pontedouro",
        "tenant": "pontedouro",
        "initials": "CP",
        "role": _("Persoal do concello"),
        "sees": _("Panel do concello (escritorio)"),
        "lands": _("Abre no panel do día dun concello con máis volume."),
        "thumb": "concello",
    },
    {
        "email": "tino@demo.eira.example",
        "name": "Tino",
        "tenant": "pontedouro",
        "initials": "T",
        "role": _("Persoal de mantemento"),
        "sees": _("App do operario (móbil)"),
        "lands": _("Abre nas súas ordes de traballo."),
        "thumb": "operario",
    },
    {
        "email": "deputacion@demo.eira.example",
        "name": "Deputación das Marismas",
        "tenant": None,
        "region": "marismas",
        "initials": "DM",
        "role": _("Persoal da deputación"),
        "sees": _("Rede de concellos (escritorio)"),
        "lands": _("Abre na comparativa dos dous concellos; pode consultar cada un en só lectura."),
        "thumb": "deputacion",
    },
]

BY_EMAIL = {p["email"]: p for p in DEMO_PERSONAS}
