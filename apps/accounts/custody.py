# SPDX-License-Identifier: EUPL-1.2
"""v5 · F: «Quen custodia os teus datos», xerada a partir da matriz de visibilidade.

A columna «quen o recibe» lese de `docs/rxpd/matriz.md` (todas as táboas que empezan por
«Dato»), así a páxina non se pode afastar da matriz. Para que, canto tempo e como borralo
explícanse aquí en linguaxe sinxela; un test comproba que cada fila da matriz ten explicación.
"""

import re
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.utils.translation import gettext_lazy as _

MATRIX = Path(settings.BASE_DIR) / "docs" / "rxpd" / "matriz.md"
SKIP_COLUMNS = {"Dato", "Veciña (propio)", "Conservación"}

# Dato da matriz → (para que, canto tempo, como pedir que se borre)
ERASE_ACCOUNT = _(
    "Desde «A miña conta → Privacidade» podes descargar os teus datos e borrar a conta. "
    "Tamén o podes pedir no concello."
)
DETAILS = {
    "Correo e teléfono": (
        _("Para entrar sen contrasinal e para avisarte das túas reservas."),
        _("Mentres teñas a conta."),
        ERASE_ACCOUNT,
    ),
    "Nome para mostrar": (
        _("Para que o persoal saiba de quen é a reserva no mostrador ou na tableta."),
        _("Mentres teñas a conta."),
        _("Podes cambialo ou borralo en «A miña conta»."),
    ),
    "Empadroamento (si/non)": (
        _("Para aplicarche a tarifa de veciñanza."),
        _("Mentres esteas empadroado ou empadroada; o concello revísao coas cargas do padrón."),
        _("Pídeo no concello."),
    ),
    "Colectivo de tarifa reducida": (
        _("Para aplicarche a tarifa reducida que validou o concello (sen gardar documentos)."),
        _("Ata a data de caducidade que fixou o concello."),
        _("Pídeo no concello."),
    ),
    "Reservas": (
        _("Para gardarche a franxa, abrir a porta e levar as contas do servizo."),
        _("2 anos; despois só quedan cifras agregadas sen nomes."),
        ERASE_ACCOUNT,
    ),
    "Pagamentos": (
        _("Para cobrar as taxas e facer devolucións. O banco garda os datos da tarxeta, Eira non."),
        _("6 anos, porque o obriga a normativa tributaria."),
        _("Non se poden borrar antes por obriga legal; si podes pedir que se limiten."),
    ),
    "Menores: nome e ano": (
        _("Para inscribir as crianzas nas escolas deportivas."),
        _("Mentres estean inscritas e ata 2 anos despois."),
        _("Desde «A miña familia» ou no concello."),
    ),
    "Consentimento de imaxe": (
        _("Para saber se se poden usar fotos onde apareces nas comunicacións do concello."),
        _("Ata que o retires."),
        _("Retírao cando queiras en «A miña conta»."),
    ),
    "Asistencia e esforzo (RPE)": (
        _("Para que a persoa monitora adapte as sesións e para o observatorio (só agregado)."),
        _("A tempada e 2 anos máis; no observatorio só quedan cifras sen nomes."),
        _("Retira o consentimento ou pídeo no concello."),
    ),
    "Valoracións «Que tal foi?»": (
        _("Para mellorar as instalacións. O persoal le os comentarios sen o teu nome."),
        _("2 anos."),
        ERASE_ACCOUNT,
    ),
    "Incidencias que comunica": (
        _("Para reparar avarías e avisarte cando estean arranxadas."),
        _("2 anos."),
        _("Pídeo no concello."),
    ),
    "Saúde (peso, idade para recomendacións)": (
        _("Para darche consellos de saúde na túa reserva."),
        _("Quedan no teu móbil. Na conta, só se ti o decides, e ata que o retires."),
        _("Bórrao en «Saúde» cando queiras."),
    ),
    "Padrón": (
        _("Para comprobar se estás empadroado ou empadroada sen que Eira garde o padrón."),
        _("Eira só garda un resumo cifrado ata a seguinte carga do padrón."),
        _("Non hai nada teu que borrar en Eira: o padrón é do concello."),
    ),
    "Nome para mostrar (ou «Persoa de ‹concello›» se non o ten)": (
        _(
            "Cando reservas noutro concello da rede, para que o seu persoal saiba de quen é a reserva."
        ),
        _("Os da reserva nese concello (2 anos)."),
        _("Pídeo ao concello onde reservaches."),
    ),
    "Concello de orixe (só o nome)": (
        _("Para aplicarche a tarifa de persoas non empadroadas e contar as visitas da rede."),
        _("Os da reserva."),
        _("Pídeo ao concello onde reservaches."),
    ),
    "Data, hora, instalación, número de persoas e nomes opcionais dos participantes": (
        _("Para gardarche a franxa no outro concello."),
        _("2 anos."),
        _("Pídeo ao concello onde reservaches."),
    ),
    "Importe, forma de pagamento e referencia do cobro": (
        _("Para cobrar no TPV do concello onde reservas."),
        _("6 anos, por obriga tributaria."),
        _("Non se poden borrar antes por obriga legal."),
    ),
    "Correo, teléfono, ano de nacemento": (
        _("O outro concello non os recibe: os avisos da reserva mándachos Eira."),
        _("—"),
        _("—"),
    ),
    "Empadroamento, familia, menores, saúde, inscricións, valoracións noutros concellos": (
        _("O outro concello non os recibe."),
        _("—"),
        _("—"),
    ),
    "Número de persoas e nomes opcionais dos participantes": (
        _("Para saber cantas persoas usan a instalación e, se queres, quen."),
        _("Os da reserva (2 anos)."),
        ERASE_ACCOUNT,
    ),
    "Estado ao entrar (texto e foto opcional, sen EXIF)": (
        _("Para que, se algo xa estaba mal, non se che atribúa e se poida reparar."),
        _("Os da reserva; se se creou unha incidencia, os da incidencia (2 anos)."),
        _("Pídeo no concello."),
    ),
    "Bonos (usos e caducidade)": (
        _("Para descontar os usos das túas reservas."),
        _("6 anos, coma os cobros."),
        _("Non se poden borrar antes por obriga legal."),
    ),
    "Rexistro de brechas de seguridade": (
        _("Para cumprir os arts. 33 e 34 do RXPD se algunha vez hai un incidente cos datos."),
        _("5 anos."),
        _("Non contén os teus datos: describe o incidente. Se te afectase, informaríamoste."),
    ),
}

SYMBOLS = (
    ("agr.", _("só cifras agregadas")),
    ("seud.", _("seudonimizado")),
)


def _humanize(cell):
    text = cell.strip().replace("**", "")
    if text.startswith("✔"):
        rest = text[1:].strip()
        return rest.strip("()") or str(_("si"))
    for code, label in SYMBOLS:
        if text.startswith(code):
            rest = text[len(code) :].strip(" ;")
            return f"{label}{'; ' + rest if rest else ''}"
    return text


@lru_cache(maxsize=1)
def matrix_rows():
    """[(dato, [(perfil, valor), …], conservación|None)] de todas as táboas «Dato» da matriz."""
    try:
        lines = MATRIX.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    rows, header = [], None
    for line in lines:
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == "Dato":
            header = cells
            continue
        if header is None or re.fullmatch(r"[-: ]+", "".join(cells)):
            continue
        record = dict(zip(header, cells, strict=False))
        seen = [
            (col, _humanize(val))
            for col, val in record.items()
            if col not in SKIP_COLUMNS and val.strip() not in ("—", "**—**", "")
        ]
        rows.append((cells[0], tuple(seen), record.get("Conservación")))
    return tuple(rows)


def custody_rows():
    out = []
    for dato, seen, retention in matrix_rows():
        purpose, keep, erase = DETAILS.get(dato, ("", "", ""))
        out.append(
            {
                "data": dato,
                "recipients": seen,
                "purpose": purpose,
                "retention": retention or keep,
                "erase": erase,
            }
        )
    return out
