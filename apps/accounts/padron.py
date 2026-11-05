# SPDX-License-Identifier: EUPL-1.2
"""v4: padrón semiautomático.

O concello sobe un CSV do padrón (DNI/NIE e data de nacemento). Eira non garda o ficheiro nin os
datos: de cada liña calcula un HMAC-SHA256 co segredo da instancia e garda só ese resumo. Cando
alguén pide a app, faise o mesmo cos seus datos e compárase. O nome **nunca** se usa para casar.
"""

import csv
import datetime as dt
import hashlib
import hmac
import io
import re

from django.conf import settings
from django.db import transaction

from .models import PadronEntry, PadronImport, audit

LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
NIE_PREFIX = {"X": "0", "Y": "1", "Z": "2"}
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%d/%m/%y")
ID_HEADERS = {"dni", "nie", "dni_nie", "dni/nie", "documento", "nif", "id"}
DATE_HEADERS = {
    "data_nacemento",
    "data",
    "fecha_nacimiento",
    "fecha",
    "nacemento",
    "nacimiento",
    "birth_date",
}
PARISH_HEADERS = {"parroquia", "parish"}  # v1.5 · C: columna opcional
MAX_ROWS = 200_000

TEMPLATE = (
    "dni_nie;data_nacemento\n"
    "# Unha persoa por liña. Data en DD/MM/AAAA ou AAAA-MM-DD. Só se usan estas dúas columnas.\n"
    "# Exemplo (borra esta liña): 12345678Z;31/12/1980\n"
    "# Opcional: unha terceira columna «parroquia». Só se garda a parroquia, para estatísticas.\n"
)


def normalize_id(value):
    """«12.345.678-z» → «12345678Z»; «x1234567l» → «X1234567L». Recheo con ceros no DNI."""
    v = re.sub(r"[^0-9A-Za-z]", "", value or "").upper()
    if re.fullmatch(r"\d{1,8}[A-Z]", v):
        v = v.zfill(9)
    return v


def valid_id(value):
    """DNI (8 díxitos + letra) ou NIE (X/Y/Z + 7 díxitos + letra), coa letra de control."""
    v = normalize_id(value)
    if re.fullmatch(r"\d{8}[A-Z]", v):
        number = int(v[:8])
    elif re.fullmatch(r"[XYZ]\d{7}[A-Z]", v):
        number = int(NIE_PREFIX[v[0]] + v[1:8])
    else:
        return False
    return LETTERS[number % 23] == v[-1]


def parse_date(value):
    if isinstance(value, dt.date):
        return value
    text = (value or "").strip()
    for fmt in DATE_FORMATS:
        try:
            d = dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        if fmt.endswith("%y") and d.year > dt.date.today().year:
            d = d.replace(year=d.year - 100)  # «05/03/48» é 1948, non 2048
        return d
    return None


def _secret():
    key = getattr(settings, "EIRA_PADRON_SECRET", "") or f"{settings.SECRET_KEY}:padron"
    return key.encode()


def digest(municipality, id_number, birth_date):
    """HMAC-SHA256 de «concello|DNI normalizado|AAAA-MM-DD». None se os datos non son válidos."""
    v, d = normalize_id(id_number), parse_date(birth_date)
    if not valid_id(v) or d is None:
        return None
    msg = f"{municipality.pk}|{v}|{d.isoformat()}".encode()
    return hmac.new(_secret(), msg, hashlib.sha256).hexdigest()


def matches(municipality, id_number, birth_date):
    h = digest(municipality, id_number, birth_date)
    return bool(h) and PadronEntry.objects.filter(municipality=municipality, digest=h).exists()


def parish_for(municipality, id_number, birth_date):
    """v1.5 · C: parroquia da persoa no padrón cargado, ou None. Non se garda nada máis."""
    h = digest(municipality, id_number, birth_date)
    if not h:
        return None
    entry = (
        PadronEntry.objects.filter(municipality=municipality, digest=h)
        .select_related("parish")
        .first()
    )
    return entry.parish if entry else None


class _Semicolon(csv.excel):
    delimiter = ";"


def _rows(text):
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return []
    try:
        dialect = csv.Sniffer().sniff(lines[0], delimiters=";,\t")
    except csv.Error:
        dialect = _Semicolon
    reader = csv.reader(io.StringIO("\n".join(lines)), dialect)
    rows = list(reader)
    head = [h.strip().lower() for h in rows[0]]
    id_col = next((i for i, h in enumerate(head) if h in ID_HEADERS), None)
    date_col = next((i for i, h in enumerate(head) if h in DATE_HEADERS), None)
    parish_col = next((i for i, h in enumerate(head) if h in PARISH_HEADERS), None)
    if id_col is None or date_col is None:  # sen cabeceira: primeira columna DNI, segunda data
        id_col, date_col, data = 0, 1, rows
    else:
        data = rows[1:]
    return [
        (
            r[id_col] if len(r) > id_col else "",
            r[date_col] if len(r) > date_col else "",
            r[parish_col].strip() if parish_col is not None and len(r) > parish_col else "",
        )
        for r in data
    ]


@transaction.atomic
def import_csv(municipality, uploaded, by=None):
    """Substitúe o padrón do concello polo do CSV. Le o ficheiro en memoria e non o garda."""
    raw = uploaded.read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    del raw
    rows = _rows(text)[:MAX_ROWS]
    del text
    from apps.facilities.models import Parish

    parishes = {p.name.casefold(): p for p in Parish.objects.filter(municipality=municipality)}
    digests, rejected = {}, 0
    for id_number, birth, parish_name in rows:
        h = digest(municipality, id_number, birth)
        if h:
            # Unha parroquia que non existe no concello ignórase: non se crean datos novos
            digests[h] = parishes.get(parish_name.casefold())
        else:
            rejected += 1
    del rows
    PadronEntry.objects.filter(municipality=municipality).delete()
    batch = PadronImport.objects.create(
        municipality=municipality, imported_by=by, count=len(digests), rejected=rejected
    )
    PadronEntry.objects.bulk_create(
        [
            PadronEntry(municipality=municipality, digest=h, batch=batch, parish=parish)
            for h, parish in digests.items()
        ],
        batch_size=2000,
    )
    audit("padron.import", by, municipality, batch, count=len(digests), rejected=rejected)
    return batch


def current(municipality):
    return PadronImport.objects.filter(municipality=municipality).first()
