# SPDX-License-Identifier: EUPL-1.2
"""v1.3 · B: resumo en linguaxe clara da avaliación de impacto (EIPD, art. 35 do RXPD).

A plantilla completa para o concello está en docs/rxpd/eipd-plantilla.md. Aquí só van os
tratamentos de maior risco, o que fai Eira para reducilo e o risco que queda."""

from django.utils.translation import gettext_lazy as _

TREATMENTS = [
    {
        "key": "saude",
        "title": _("Saúde: consellos, esforzo (RPE), probas físicas e observatorio"),
        "data": _(
            "Idade, peso e actividade semanal para os consellos; esforzo percibido e resultados de "
            "probas físicas nas escolas deportivas."
        ),
        "risk": _("Que alguén coñeza o teu estado de saúde ou forma física sen que o saibas."),
        "measures": [
            _(
                "Os datos dos consellos quedan no teu dispositivo; só se gardan na conta se o pides."
            ),
            _("Esforzo e probas físicas de menores só con consentimento da familia, revogable."),
            _("O persoal nunca ve os teus datos de saúde; non van nas exportacións do concello."),
            _("O observatorio só publica grupos de 10 persoas ou máis, por banda de idade."),
            _("Os datos para estudos van cun seudónimo (HMAC), nunca co nome nin a idade exacta."),
        ],
        "residual": _("Baixo"),
    },
    {
        "key": "menores",
        "title": _("Menores nas escolas deportivas"),
        "data": _("Nome, apelidos, ano de nacemento, asistencia e consentimentos da familia."),
        "risk": _("Exposición de datos ou da imaxe de nenas e nenos."),
        "measures": [
            _("Só nome e ano de nacemento; nin DNI nin enderezo."),
            _("Consentimentos separados (datos, imaxe, esforzo), con data e revogables nun clic."),
            _("A tableta da persoa monitora só recibe o nome e o primeiro apelido."),
            _("As partidas abertas non admiten menores de 14 anos."),
        ],
        "residual": _("Baixo"),
    },
    {
        "key": "accidentes",
        "title": _("Rexistro de accidentes"),
        "data": _(
            "Data e hora, instalación, tipo xeral, gravidade percibida, se se chamou ao 112 e o "
            "papel de quen comunica."
        ),
        "risk": _("Que o rexistro acabe tendo datos clínicos dunha persoa."),
        "measures": [
            _("Non hai ningún campo de texto libre: non se poden escribir diagnósticos."),
            _("Só o ven a administración do concello e o DPD; a deputación, nunca."),
            _("Bórrase só pasado o prazo configurado (por defecto, 24 meses despois de pechalo)."),
            _("Cada consulta e cambio queda no rexistro de auditoría."),
        ],
        "residual": _("Baixo"),
    },
    {
        "key": "carne",
        "title": _("Carné municipal con foto"),
        "data": _("Número de carné, foto opcional e abono."),
        "risk": _("Suplantación ou uso da foto para outros fins."),
        "measures": [
            _("A foto é opcional e gárdase sen metadatos (sen localización)."),
            _("O QR non leva datos persoais e o da app caduca aos poucos minutos."),
            _("O carné impreso pódese anular en calquera momento."),
        ],
        "residual": _("Baixo"),
    },
    {
        "key": "padron",
        "title": _("Comprobación do empadroamento"),
        "data": _("DNI e data de nacemento, só mentres se revisa a solicitude."),
        "risk": _("Que se garde unha copia do padrón ou do DNI."),
        "measures": [
            _("O padrón cárgase como resumos HMAC: Eira non pode ler os DNI."),
            _("O DNI da solicitude bórrase en canto se decide."),
        ],
        "residual": _("Baixo"),
    },
    {
        "key": "contas",
        "title": _("Contas do persoal que xestiona datos"),
        "data": _("Correo, roles e accións sensibles (rexistro de auditoría)."),
        "risk": _("Que alguén entre cunha conta de administración e vexa datos persoais."),
        "measures": [
            _("Dobre factor (app de códigos) opcional, e obrigatorio se o concello o decide."),
            _(
                "Rexistro de auditoría de tarifas, permisos, exportacións, soporte, brechas e accidentes."
            ),
            _("A deputación só ve datos persoais cun acceso de soporte de 24 horas autorizado."),
        ],
        "residual": _("Medio-baixo (depende de que o concello active o dobre factor)"),
    },
]
