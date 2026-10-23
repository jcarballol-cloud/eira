# SPDX-License-Identifier: EUPL-1.2
"""Plantillas de alta asistida: precargan normas, franxas, tarifas e plan de mantemento."""

import datetime as dt

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .models import FacilityKind, OpeningHours, RulesVersion, Tariff

COMMON_RULES = [
    _("Respecta o horario reservado: entra e sae á hora."),
    _("Deixa a instalación como a atopaches: luces apagadas, material recollido e porta pechada."),
    _("Comunica calquera desperfecto co botón «Avisar dunha avaría»."),
    _("Non se permite fumar nin introducir vidro."),
    _("Se non podes vir, cancela con antelación: outra persoa poderá usala."),
]

T = dt.time


def _week(opens, closes, days=range(7)):
    return [(d, opens, closes) for d in days]


TEMPLATES = {
    "outdoor_court": {
        "label": _("Pista exterior"),
        "kind": FacilityKind.OUTDOOR_COURT,
        "description": _("Pista polideportiva descuberta para fútbol sala, baloncesto ou balonmán."),
        "capacity": 1, "slot_minutes": 60, "indoor": False, "lighting": True, "access_level": 0,
        "hours": _week(T(9), T(22)),
        "rules": COMMON_RULES + [_("Calzado deportivo. Non se permiten bicicletas nin patíns na pista.")],
        "tariffs": {"resident": 0, "non_resident": 300},
        "maintenance": [
            (_("Revisión visual da pista e redes"), "weekly", "Redes e canastras\nPavimento sen fochas\nLuminarias"),
            (_("Limpeza de follas e drenaxes"), "monthly", "Varrer a pista\nLimpar sumidoiros"),
            (_("Revisión eléctrica das torres de luz"), "yearly", "Cadro eléctrico\nLuminarias\nToma de terra"),
        ],
    },
    "sports_hall": {
        "label": _("Pavillón"),
        "kind": FacilityKind.SPORTS_HALL,
        "description": _("Pavillón cuberto con pista central e vestiarios."),
        "capacity": 1, "slot_minutes": 60, "indoor": True, "lighting": True, "access_level": 1,
        "hours": _week(T(9), T(23), range(0, 6)) + [(6, T(10), T(14))],
        "rules": COMMON_RULES + [_("Calzado deportivo limpo e de sola clara."), _("Os vestiarios péchanse 30 minutos despois da última franxa.")],
        "tariffs": {"resident": 1200, "non_resident": 2400, "youth": 600},
        "maintenance": [
            (_("Limpeza de vestiarios"), "daily", "Duchas\nInodoros\nReposición de xabón e papel"),
            (_("Revisión de desfibrilador (DEA)"), "monthly", "Luz de estado\nCaducidade de eléctrodos"),
            (_("Revisión de extintores"), "yearly", "Presión\nPrecinto\nEtiqueta de revisión"),
        ],
    },
    "grass_field": {
        "label": _("Campo de herba"),
        "kind": FacilityKind.GRASS_FIELD,
        "description": _("Campo de fútbol de herba (natural ou artificial)."),
        "capacity": 1, "slot_minutes": 90, "indoor": False, "lighting": True, "access_level": 1,
        "hours": _week(T(10), T(22, 30)),
        "rules": COMMON_RULES + [_("Botas de tacos de goma; prohibidos os tacos metálicos."), _("Non se pode usar o campo con alerta laranxa ou vermella.")],
        "tariffs": {"resident": 2500, "non_resident": 5000},
        "maintenance": [
            (_("Cepillado e reposición de caucho"), "weekly", "Cepillar áreas de porterías\nRevisar caucho"),
            (_("Revisión de porterías e redes"), "monthly", "Ancoraxes\nRedes"),
        ],
    },
    "gym": {
        "label": _("Ximnasio"),
        "kind": FacilityKind.GYM,
        "description": _("Sala de musculación e cardio de uso compartido."),
        "capacity": 10, "slot_minutes": 60, "indoor": True, "lighting": True, "access_level": 2,
        "hours": _week(T(7), T(22), range(0, 5)) + _week(T(9), T(14), range(5, 7)),
        "rules": COMMON_RULES + [_("Toalla obrigatoria. Limpa as máquinas despois de usalas."), _("Idade mínima: 16 anos.")],
        "tariffs": {"resident": 200, "non_resident": 400, "senior": 0},
        "maintenance": [
            (_("Desinfección de máquinas"), "daily", "Bancos\nAgarradoiras\nEsteiras"),
            (_("Revisión de cables e poleas"), "monthly", "Cables\nPoleas\nPasadores"),
        ],
    },
    "pool": {
        "label": _("Piscina"),
        "kind": FacilityKind.POOL,
        "description": _("Piscina climatizada con rúas de nado libre."),
        "capacity": 24, "slot_minutes": 60, "indoor": True, "lighting": True, "access_level": 3,
        "hours": _week(T(7), T(21, 30), range(0, 6)),
        "rules": COMMON_RULES + [_("Ducha obrigatoria antes do baño. Gorro obrigatorio."), _("Menores de 14 anos acompañados.")],
        "tariffs": {"resident": 300, "non_resident": 550, "youth": 150, "senior": 150},
        "maintenance": [
            (_("Control de cloro e pH"), "daily", "Medir cloro libre\nMedir pH\nAnotar no rexistro"),
            (_("Limpeza de fondo"), "weekly", "Robot limpafondos\nSkimmers"),
            (_("Revisión sanitaria anual"), "yearly", "Analítica\nInforme sanitario"),
        ],
    },
    "padel": {
        "label": _("Pista de pádel"),
        "kind": FacilityKind.PADEL,
        "description": _("Pista de pádel con cristal."),
        "capacity": 1, "slot_minutes": 90, "indoor": False, "lighting": True, "access_level": 2,
        "hours": _week(T(9), T(22, 30)),
        "rules": COMMON_RULES + [_("Calzado de pádel ou tenis. Non pendurarse da rede.")],
        "tariffs": {"resident": 400, "non_resident": 800, "youth": 200},
        "maintenance": [
            (_("Revisión de cristais e rede"), "weekly", "Cristais sen fendas\nTensión da rede\nPortas"),
            (_("Cepillado da herba"), "monthly", "Cepillar\nRepoñer area"),
        ],
    },
}


def template_choices():
    return [(key, t["label"]) for key, t in TEMPLATES.items()]


@transaction.atomic
def apply_template(facility, key, user=None):
    """Crea horario, normas, tarifas, plan de mantemento e dispositivo de acceso dunha plantilla."""
    from apps.access.models import LockDevice
    from apps.maintenance.models import MaintenancePlan, MaintenanceTask

    t = TEMPLATES[key]
    for weekday, opens, closes in t["hours"]:
        OpeningHours.objects.create(facility=facility, weekday=weekday, opens=opens, closes=closes)
    RulesVersion.publish(facility, "\n".join(f"- {r}" for r in t["rules"]), user)
    for audience, cents in t["tariffs"].items():
        Tariff.objects.update_or_create(facility=facility, audience=audience, defaults={"price_cents": cents})
    plan = MaintenancePlan.objects.create(municipality=facility.municipality, facility=facility,
                                          name=str(_("Plan preventivo básico")))
    for title, freq, checklist in t["maintenance"]:
        MaintenanceTask.objects.create(plan=plan, title=str(title), frequency=freq, checklist=checklist)
    ensure_lock(facility)
    return facility


def ensure_lock(facility):
    from apps.access.models import LockDevice

    if facility.access_level in (2, 3):
        kind = LockDevice.Kind.OFFLINE if facility.access_level == 2 else LockDevice.Kind.CONNECTED
        LockDevice.objects.update_or_create(
            facility=facility,
            defaults={"municipality": facility.municipality, "kind": kind,
                      "step_minutes": 30 if facility.slot_minutes % 30 == 0 else 15,
                      "controls_lights": facility.lighting and facility.access_level == 3,
                      "label": f"PCH-{facility.pk:04d}"},
        )
