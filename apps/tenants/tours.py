# SPDX-License-Identifier: EUPL-1.2
"""v1.5.1: guía paso a paso («visita guiada») de cada perfil.

Cada guía empeza na pantalla principal do perfil. Un paso pode sinalar un elemento marcado con
`data-tour="…"` nesa pantalla; se non existe ou non se ve (p. ex. no móbil), o paso móstrase
centrado. Os textos van ao navegador con `json_script` e o JS está en `static/js/tour.js`.

Aparece soa a primeira vez en cada perfil na demo (`EIRA_DEMO_TOOLS`) ou, nunha instalación real,
se o concello a activa en «Configuración». Sempre se pode abrir desde «?» → «Ver a guía».
"""

from django.conf import settings
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

VERSION = 1  # súbese se cambian moito os pasos, para que se volva mostrar soa

# (sinal ou None, título, texto)
TOURS = {
    "neighbour": {
        "start": "app:home",
        "title": gettext_lazy("Guía da app"),
        "steps": [
            (
                "search",
                gettext_lazy("Busca unha instalación"),
                gettext_lazy(
                    "Toca «Reservar» para ver as instalacións do concello: podes buscar por "
                    "deporte, por parroquia ou no mapa."
                ),
            ),
            (
                None,
                gettext_lazy("Horas con ★ e luz"),
                gettext_lazy(
                    "Na ficha de cada instalación, as horas con ★ adoitan ter pouca xente e son "
                    "máis baratas. Se fai falta luz, o suplemento vese antes de pagar."
                ),
            ),
            (
                "booking",
                gettext_lazy("Reservar e pagar"),
                gettext_lazy(
                    "Reservas en tres pasos: hora, persoas e pagamento. A túa próxima reserva "
                    "aparece sempre aquí."
                ),
            ),
            (
                "access-code",
                gettext_lazy("O código da porta"),
                gettext_lazy(
                    "Durante a túa franxa, este código abre a porta. Funciona aínda que a "
                    "instalación non teña internet."
                ),
            ),
            (
                "safety",
                gettext_lazy("Aviso e Alerta"),
                gettext_lazy(
                    "Avisa dunha avaría con foto ou pide axuda nunha emerxencia. En «Alerta» tes o "
                    "DESA máis próximo e o que hai que dicir ao 112."
                ),
            ),
            (
                "listen",
                gettext_lazy("Escoitar"),
                gettext_lazy("«Escoitar» le a pantalla en voz alta coa voz do teu dispositivo."),
            ),
            (
                "nearby",
                gettext_lazy("Concellos próximos"),
                gettext_lazy(
                    "Coa mesma conta podes reservar noutros concellos da rede, coa tarifa de "
                    "persoas non empadroadas."
                ),
            ),
        ],
    },
    "operator": {
        "start": "maintenance:my_orders",
        "title": gettext_lazy("Guía de mantemento"),
        "steps": [
            (
                None,
                gettext_lazy("A túa app de mantemento"),
                gettext_lazy(
                    "Aquí tes o traballo do día. Funciona sen cobertura: os cambios envíanse ao "
                    "recuperar a rede."
                ),
            ),
            (
                "orders",
                gettext_lazy("Ordes do día"),
                gettext_lazy(
                    "As ordes atrasadas van primeiro. Toca unha para ver a instalación e o que hai "
                    "que facer."
                ),
            ),
            (
                "orders",
                gettext_lazy("Foto e peche"),
                gettext_lazy(
                    "Dentro de cada orde engades unha foto e unha nota e pechas a orde. O concello "
                    "veo ao momento."
                ),
            ),
            (
                "alert",
                gettext_lazy("Alerta"),
                gettext_lazy(
                    "Nun accidente ou unha emerxencia, toca «Alerta»: avisa ao persoal de servizo e "
                    "mostra o DESA e o que hai que dicir ao 112."
                ),
            ),
        ],
    },
    "cleaning": {
        "start": "maintenance:my_orders",
        "title": gettext_lazy("Guía de limpeza"),
        "steps": [
            (
                None,
                gettext_lazy("A túa app de limpeza"),
                gettext_lazy(
                    "Aquí tes as zonas e as tarefas do día. Funciona sen cobertura: os rexistros "
                    "envíanse ao recuperar a rede."
                ),
            ),
            (
                "zones",
                gettext_lazy("Un QR por zona"),
                gettext_lazy(
                    "Cada zona ten un QR na parede. Escanéao ou toca a zona aquí para abrir a súa "
                    "lista de limpeza."
                ),
            ),
            (
                "zones",
                gettext_lazy("Rexistro"),
                gettext_lazy(
                    "Marca as tarefas feitas e, se queres, engade unha foto. Queda gardado quen o "
                    "fixo, o día e a hora."
                ),
            ),
            (
                "alert",
                gettext_lazy("Alerta"),
                gettext_lazy(
                    "Nun accidente ou unha emerxencia, toca «Alerta» para avisar ao persoal de "
                    "servizo."
                ),
            ),
        ],
    },
    "monitor": {
        "start": "monitor:today",
        "title": gettext_lazy("Guía da tableta"),
        "steps": [
            (
                None,
                gettext_lazy("A túa tableta"),
                gettext_lazy("Aquí tes os grupos de hoxe. Cada sesión ten o seu rexistro."),
            ),
            (
                "kiosk",
                gettext_lazy("Abecedario"),
                gettext_lazy(
                    "«Abrir o rexistro» deixa a tableta na entrada: cada persoa toca a inicial do "
                    "seu nome e despois o seu nome."
                ),
            ),
            (
                "attendance",
                gettext_lazy("Entrada e saída"),
                gettext_lazy(
                    "Quen chega marca a entrada e, ao marchar, a saída. Coa «Lista rápida» "
                    "pásalas ti dunha vez."
                ),
            ),
            (
                "kiosk",
                gettext_lazy("Esforzo (RPE)"),
                gettext_lazy(
                    "Ao saír, cada persoa indica o esforzo do 0 ao 10. Ves a evolución en "
                    "«Estatísticas»."
                ),
            ),
            (
                "alert",
                gettext_lazy("Alerta"),
                gettext_lazy("Nun accidente durante a sesión, toca «Alerta»."),
            ),
        ],
    },
    "admin": {
        "start": "manage:dashboard",
        "title": gettext_lazy("Guía da xestión municipal"),
        "steps": [
            (
                "admin-today",
                gettext_lazy("Panel do día"),
                gettext_lazy(
                    "As reservas de hoxe, as incidencias e os avisos pendentes, nunha soa pantalla."
                ),
            ),
            (
                "admin-facilities",
                gettext_lazy("Instalacións e tarifas"),
                gettext_lazy(
                    "Dá de alta instalacións con plantillas e define horarios, tarifas, normas e "
                    "como se entra."
                ),
            ),
            (
                "admin-maintenance",
                gettext_lazy("Mantemento"),
                gettext_lazy(
                    "Plans preventivos que crean as ordes de traballo soas, e o calendario "
                    "compartido co persoal."
                ),
            ),
            (
                "admin-performance",
                gettext_lazy("Rendemento e NPS"),
                gettext_lazy(
                    "Uso, enerxía e custo por instalación, e a satisfacción da veciñanza "
                    "(enquisas NPS anónimas)."
                ),
            ),
            (
                "admin-provenance",
                gettext_lazy("Procedencia"),
                gettext_lazy(
                    "De onde vén a xente que usa cada instalación, só con datos agregados (nunca "
                    "menos de 10 persoas)."
                ),
            ),
            (
                "admin-legal",
                gettext_lazy("Textos legais"),
                gettext_lazy(
                    "Privacidade, condicións e normas con versións e rexistro de aceptacións. Son "
                    "modelos de exemplo: revísaos cos servizos xurídicos."
                ),
            ),
        ],
    },
    "region": {
        "start": "region:dashboard",
        "title": gettext_lazy("Guía da deputación"),
        "steps": [
            (
                None,
                gettext_lazy("A túa rede de concellos"),
                gettext_lazy(
                    "Desde aquí ves os concellos adheridos e dás de alta outros novos. Só ves datos "
                    "agregados."
                ),
            ),
            (
                "region-compare",
                gettext_lazy("Comparativa agregada"),
                gettext_lazy(
                    "Reservas, ocupación e satisfacción de toda a rede, comparando as últimas "
                    "catro semanas coas anteriores."
                ),
            ),
            (
                "region-mobility",
                gettext_lazy("Mapa de procedencia"),
                gettext_lazy(
                    "Como se move a xente entre concellos para facer deporte, só con datos "
                    "agregados."
                ),
            ),
            (
                "region-support",
                gettext_lazy("Acceso de soporte de 24 horas"),
                gettext_lazy(
                    "Para ver datos persoais dun concello, ese concello ten que darche acceso de "
                    "soporte. Caduca ás 24 horas e cada consulta queda rexistrada."
                ),
            ),
        ],
    },
}


def target_selector(name):
    return f'[data-tour="{name}"]' if name else None


def tour_payload(kind, auto):
    """Datos da guía para `json_script`: textos xa traducidos e selectores."""
    tour = TOURS[kind]
    return {
        "id": f"{kind}-v{VERSION}",
        "title": str(tour["title"]),
        "auto": auto,
        "steps": [
            {"target": target_selector(t), "title": str(title), "body": str(body)}
            for t, title, body in tour["steps"]
        ],
        "labels": {
            "prev": _("Anterior"),
            "next": _("Seguinte"),
            "done": _("Rematar"),
            "close": _("Saír"),
            # %(n)s e %(total)s substitúeos o JS
            "step": _("Paso %(n)s de %(total)s"),
        },
    }


def tour_enabled(kind, tenant, region=None):
    """Na demo, sempre; nunha instalación real, se o concello (ou un da rede) a activou."""
    if settings.EIRA_DEMO_TOOLS:
        return True
    if tenant is not None:
        return bool(getattr(tenant, "guided_tour", False))
    if region is not None:
        return region.municipalities.filter(guided_tour=True).exists()
    return False


def tour_context(request, kind, tenant, nav_region):
    """`tour_available` (para «Ver a guía») e `tour` (só na pantalla onde empeza)."""
    if kind not in TOURS or not tour_enabled(kind, tenant, nav_region):
        return {"tour_available": False, "tour": None}
    match = getattr(request, "resolver_match", None)
    here = match.view_name if match else ""
    if here != TOURS[kind]["start"]:
        return {"tour_available": True, "tour": None}
    # Na demo sae soa a primeira vez; nunha instalación real, se o concello a activou
    return {"tour_available": True, "tour": tour_payload(kind, auto=True)}
