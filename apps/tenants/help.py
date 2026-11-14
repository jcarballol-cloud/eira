# SPDX-License-Identifier: EUPL-1.2
"""v5 · E: axuda contextual do botón «?» en linguaxe sinxela.

Cada pantalla (nome da URL) ten un título e dúas ou tres frases curtas. Se unha pantalla non ten
texto propio, úsase o do tipo de ferramenta (app, tableta, administración). A guía completa
(`/axuda/`) xúntaas todas.
"""

from django.utils.translation import gettext_lazy as _

HELP = {
    # App da veciñanza
    "app:home": (
        _("Inicio"),
        _(
            "Aquí ves a túa próxima reserva e como entrar (código, chave ou QR). "
            "Debaixo tes atallos para reservar, avisar dunha avaría ou xestionar a túa familia."
        ),
    ),
    "app:nearby": (
        _("Concellos próximos"),
        _(
            "Podes reservar noutros concellos da túa rede coa mesma conta. Pagas a tarifa de "
            "persoas non empadroadas dese concello. Tamén podes ver as súas actividades e eventos."
        ),
    ),
    "tenant_home": (
        _("Buscar instalacións"),
        _(
            "Escribe o que buscas (pádel, piscina…) ou usa «Filtros». Toca unha instalación para "
            "ver as horas libres. Co selector de concello podes buscar nos concellos próximos."
        ),
    ),
    "facilities:detail": (
        _("Ficha da instalación"),
        _(
            "Escolle un día e unha hora libre. As horas con ★ adoitan ter pouca xente e son máis "
            "baratas. Á dereita tes como se entra, o material, as normas e que facer se hai un "
            "accidente."
        ),
    ),
    "facilities:book": (
        _("Confirmar a reserva"),
        _(
            "Indica cantas persoas ides e como pagas. O prezo final, coa luz se fai falla, vese "
            "antes de pagar. Le as normas e marca a casiña para confirmar."
        ),
    ),
    "bookings:mine": (
        _("As miñas reservas"),
        _(
            "As próximas arriba e o historial debaixo. Toca unha reserva para ver o código, "
            "cambiar a hora, cancelala ou descargar o recibo."
        ),
    ),
    "bookings:detail": (
        _("A túa reserva"),
        _(
            "Aquí tes como entrar e, ao chegar, podes indicar como está a pista. Ao marchar, "
            "completa o checklist de peche. Se cancelas a tempo, devólvese o importe."
        ),
    ),
    "bookings:start_state": (
        _("Estado ao entrar"),
        _(
            "Se algo xa estaba mal ao chegar, márcao agora. Queda rexistrado que estaba antes da "
            "túa reserva e non se che atribúe."
        ),
    ),
    "bookings:checklist": (
        _("Checklist de peche"),
        _(
            "Tres preguntas antes de marchar: porta, chave e orde. Se algo falla, avisamos ao concello."
        ),
    ),
    "bookings:vouchers": (
        _("Bonos"),
        _(
            "Un bono é un número de usos. Ao reservar, escolle «Bono» e descóntase un uso. "
            "Cómprase aquí co TPV ou na oficina de deportes."
        ),
    ),
    "incidents:new": (
        _("Avisar dunha avaría"),
        _(
            "Escolle a instalación, di que pasa e, se queres, engade unha foto. Avisarémoste "
            "cando estea arranxado. Se é unha emerxencia, chama ao 112."
        ),
    ),
    "safety": (
        _("Incidencia ou seguridade"),
        _(
            "Avisa dunha avaría, dun risco (o concello recibe o aviso ao momento) ou, se é unha "
            "emerxencia, chama ao 112."
        ),
    ),
    "notifications:list": (
        _("Avisos"),
        _(
            "Peches, alertas e cambios nas túas reservas e actividades. Tamén podes ver as "
            "actividades e eventos dos concellos próximos se o activas."
        ),
    ),
    "activities:list": (
        _("Escolas e actividades"),
        _("Escolle unha actividade con prazas e inscribe a quen queiras da túa familia."),
    ),
    "account:household": (
        _("A miña familia"),
        _(
            "Engade aos fillos ou persoas ao teu cargo para inscribilos nas escolas e reservar por eles."
        ),
    ),
    "health": (
        _("Saúde"),
        _(
            "Os teus datos de saúde quedan no teu móbil. Úsanse para darche consellos na túa "
            "reserva segundo o tempo que vai facer."
        ),
    ),
    "privacy_custody": (
        _("Quen custodia os teus datos"),
        _(
            "Para cada dato: quen o recibe, para que, canto tempo se garda e como pedir que se borre."
        ),
    ),
    # v1.3
    "privacy_dpia": (
        _("Avaliación de impacto"),
        _(
            "Os datos con máis risco (saúde, menores, accidentes e foto do carné): que pode pasar, "
            "que fai Eira para evitalo e que risco queda."
        ),
    ),
    "account:security": (
        _("Seguridade da conta"),
        _(
            "Activa o dobre factor cunha app de códigos do móbil e garda os códigos de "
            "recuperación nun lugar seguro."
        ),
    ),
    # App do operario
    "maintenance:my_orders": (
        _("As túas ordes"),
        _(
            "Tarefas de hoxe e atrasadas. Abre unha, marca o checklist e péchaa. Funciona sen "
            "cobertura: envíase ao recuperar a rede."
        ),
    ),
    "maintenance:calendar": (
        _("Calendario de mantemento"),
        _("As tarefas programadas por día. Toca un día para ver as ordes."),
    ),
    # Tableta da persoa monitora
    "monitor:today": (
        _("Os teus grupos de hoxe"),
        _("Escolle un grupo para pasar lista e recoller o esforzo ao final da sesión."),
    ),
    # Administración
    "manage:dashboard": (
        _("Panel do día"),
        _(
            "Reservas de hoxe, chaves, incidencias por validar, reservas para aprobar e pagamentos "
            "pendentes na oficina. É o punto de partida de cada mañá."
        ),
    ),
    "manage:agenda": (
        _("Axenda"),
        _(
            "Todas as reservas por día, semana ou mes. Toca unha para ver a ficha e cobrar ou cancelar."
        ),
    ),
    "manage:booking": (
        _("Ficha da reserva"),
        _(
            "Datos, cobros e estado ao entrar e ao saír. Se a instalación é con aprobación, aquí "
            "aprobas ou rexeitas (cun motivo; se xa pagou, devólvese só)."
        ),
    ),
    "manage:on_behalf": (
        _("Reservar por alguén"),
        _(
            "Para reservas por teléfono ou no mostrador. Escolle instalación e hora e cobra se fai falla."
        ),
    ),
    "manage:payments": (
        _("Cobros e conciliación"),
        _(
            "Todos os cobros e, arriba, o resumo por forma de pagamento: TPV, oficina, gratuíta, "
            "bono e aprazado. Exporta a CSV ou ODS para Intervención."
        ),
    ),
    "manage:vouchers": (
        _("Bonos"),
        _("Crea tipos de bono e véndeos na oficina. Tamén se poden comprar na app co TPV."),
    ),
    "manage:incidents": (
        _("Incidencias"),
        _(
            "Valida os avisos, crea a orde de traballo e marca como resolta. Os riscos van primeiro."
        ),
    ),
    "manage:facilities": (
        _("Instalacións"),
        _("Alta con plantillas, horarios, tarifas, normas, ficha de seguridade e cartel da porta."),
    ),
    "manage:facility_edit": (
        _("Datos da instalación"),
        _(
            "Usa as lapelas: datos, foto, acceso, accesibilidade, reserva e pagamento, e "
            "seguridade (material, protocolo de accidentes e DEA)."
        ),
    ),
    "manage:notices": (
        _("Avisos do concello"),
        _("Envía peches, alertas ou novidades por app, correo e Telegram, con vista previa."),
    ),
    "manage:provenance": (
        _("Procedencia"),
        _(
            "De que parroquias e concellos vén a xente a cada instalación. Só se mostran grupos de "
            "polo menos 10 persoas, despois de filtrar; o resto vai en «outras procedencias». "
            "Nunca se usa o GPS."
        ),
    ),
    "region:mobility": (
        _("Mobilidade entre concellos"),
        _(
            "Fluxos entre os concellos da rede, sempre agregados. Os puntos quentes axudan a "
            "planificar transporte e instalacións."
        ),
    ),
    "region:legal": (
        _("Documentos legais"),
        _(
            "O teu repositorio de modelos. Cada concello adóptaos tal cal ou adáptaos. Son modelos "
            "de exemplo: revísaos cos servizos xurídicos e o DPD."
        ),
    ),
    "manage:legal": (
        _("Documentos legais"),
        _(
            "Adopta os modelos tal cal ou adáptaos cos datos do concello. Ao publicar, as apps "
            "móstranos para aceptalos. Son modelos de exemplo: revísaos cos servizos xurídicos e o "
            "DPD. O rexistro de aceptacións descárgase en CSV."
        ),
    ),
    "manage:accreditations": (
        _("Acreditacións"),
        _(
            "Marca que comprobaches a acreditación na contratación. Eira non garda o certificado: "
            "só quen o marcou e cando. Sen a marca non se pode asignar a persoa a un grupo con menores."
        ),
    ),
    "manage:settings": (
        _("Configuración"),
        _(
            "Regras de reserva, formas de pagamento, luz, concellos próximos, pesos do índice de "
            "vida activa e módulos."
        ),
    ),
    "manage:audit": (
        _("Rexistro de auditoría"),
        _(
            "Quen cambiou tarifas ou permisos, quen exportou datos, os accesos de soporte, as "
            "brechas, os accidentes e o dobre factor. Filtra por categoría e datas."
        ),
    ),
    "manage:privacy_steps": (
        _("Protección de datos: primeiros pasos"),
        _(
            "Os sete pasos para usar Eira cumprindo o RXPD. Cada un leva ao seu documento ou á "
            "pantalla onde se fai; ao marcalo queda a data e a persoa no rexistro de auditoría."
        ),
    ),
    "manage:privacy_doc": (
        _("Documentos do paquete RXPD"),
        _("Modelos de exemplo para o concello. Revísaos co DPD e cos servizos xurídicos."),
    ),
    "manage:breaches": (
        _("Rexistro de brechas"),
        _(
            "Anota calquera incidente cos datos persoais. Se hai risco, notifica á AEPD en 72 "
            "horas; se é alto, informa tamén ás persoas afectadas."
        ),
    ),
    # v1.1 · limpeza
    "maintenance:cleaning_zone": (
        _("Limpeza da zona"),
        _(
            "Marca o que fixeches e toca «Rexistrar limpeza». Queda gardado quen, o día e a hora. "
            "Sen cobertura gárdase no móbil e envíase ao volver a rede."
        ),
    ),
    "manage:cleaning": (
        _("Limpeza"),
        _(
            "Zonas de cada instalación co seu QR, a última limpeza e as atrasadas. Exporta o "
            "rexistro dun período en CSV, ODS ou PDF para unha inspección ou para a empresa."
        ),
    ),
    "region:dashboard": (
        _("Rede de concellos"),
        _("Indicadores agregados e comparativa dos concellos da rede, co índice de vida activa."),
    ),
}

BY_KIND = {
    "neighbour": _("Usa as lapelas de abaixo para reservar, ver as túas reservas e a túa familia."),
    "operator": _("Aquí tes as túas ordes de traballo. Funciona tamén sen cobertura."),
    "cleaning": _(
        "Aquí tes as túas tarefas de limpeza e as zonas. Escanea o QR da parede de cada zona "
        "para marcar o feito. Funciona tamén sen cobertura."
    ),
    "monitor": _("Escolle un grupo para pasar lista e recoller o esforzo."),
    "admin": _(
        "No modo básico tes o día a día. Activa o modo avanzado para ver todo o menú; os "
        "permisos son os mesmos."
    ),
    "region": _("Ves os concellos da túa rede con datos agregados."),
    "public": _("Busca unha instalación e consulta as horas libres sen rexistrarte."),
}


# v1.1: a mesma pantalla co texto propio do persoal de limpeza
HELP_KIND = {
    ("maintenance:my_orders", "cleaning"): (
        _("As túas tarefas de limpeza"),
        _(
            "Arriba, as zonas atrasadas. Escanea o QR da zona (ou tócaa) para marcar o feito; "
            "tamén podes abrir unha tarefa e pechala. Funciona sen cobertura."
        ),
    ),
    ("maintenance:cleaning_zone", "public"): (
        _("Limpeza da zona"),
        _(
            "Aquí ves cando se limpou esta zona por última vez. Se algo está sucio ou "
            "estragado, avisa ao concello."
        ),
    ),
    ("maintenance:calendar", "cleaning"): (
        _("Calendario de limpeza"),
        _("As limpezas programadas por día. Toca un día para ver as tarefas."),
    ),
}


def help_for(view_name, kind):
    if view_name == "maintenance:cleaning_zone" and kind in ("neighbour", "monitor", "region"):
        kind = "public"  # quen non rexistra limpezas ve a páxina pública do QR
    if (view_name, kind) in HELP_KIND:
        title, body = HELP_KIND[(view_name, kind)]
        return {"title": title, "body": body, "key": view_name}
    if view_name in HELP:
        title, body = HELP[view_name]
        return {"title": title, "body": body, "key": view_name}
    return {"title": _("Axuda"), "body": BY_KIND.get(kind, BY_KIND["public"]), "key": ""}
