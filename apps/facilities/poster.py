# SPDX-License-Identifier: EUPL-1.2
"""v5 · B: cartel A4 para a porta da instalación, en PDF etiquetado e sen dependencias.

Accesibilidade do PDF:
- PDF etiquetado (`/MarkInfo /Marked true`) con árbore de estrutura: Document → H1, H2, P, L/LI
  e Figure; a orde de lectura é a do contido.
- Idioma do documento (`/Lang`), título visible na barra (`DisplayDocTitle`) e metadatos XMP.
- O QR é unha figura con texto alternativo (`/Alt`) que inclúe o enderezo; o enderezo tamén vai
  escrito debaixo.
- Bandas e liñas decorativas marcadas como artefactos (os lectores de pantalla sáltanas).
- Texto real (non imaxe), tamaño mínimo 11 pt, contraste alto (texto negro sobre branco; o 112
  en branco sobre vermello escuro, 7,3:1).
Limitación: usa as fontes estándar (Helvetica) sen incrustar; os lectores de PDF substitúenas.
Non está validado con PAC nin veraPDF (anotado no informe).
"""

import datetime as dt
import io
import zlib

import qrcode
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.bookings.pdf import _esc

PAGE_W, PAGE_H = 595, 842
MARGIN = 48
# Anchos de Helvetica (AFM, 1/1000 em) para ASCII 32–126; as letras con til miden coma a base
_W = [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
]  # fmt: skip
_BASE = str.maketrans("áéíóúÁÉÍÓÚñÑüÜçÇàèìòù", "aeiouAEIOUnNuUcCaeiou")


def text_width(text, size, bold=False):
    total = 0
    for ch in text.translate(_BASE):
        code = ord(ch)
        total += _W[code - 32] if 32 <= code <= 126 else 556
    return total * size / 1000 * (1.06 if bold else 1)


def wrap(text, size, width, bold=False):
    lines = []
    for para in str(text).splitlines() or [""]:
        words, line = para.split(), ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if text_width(candidate, size, bold) <= width or not line:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def _hex_rgb(color):
    h = color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


class TaggedPage:
    """Unha páxina con contido marcado (MCID) e a lista de elementos de estrutura."""

    def __init__(self):
        self.ops = []
        self.elements = []  # (tipo, [mcid…], atributos)
        self.mcid = 0
        self.images = {}

    def artifact(self, ops):
        self.ops.append("/Artifact BMC")
        self.ops.extend(ops)
        self.ops.append("EMC")

    def _mark(self, tag, ops):
        mcid = self.mcid
        self.mcid += 1
        self.ops.append(f"/{tag} <</MCID {mcid}>> BDC")
        self.ops.extend(ops)
        self.ops.append("EMC")
        return mcid

    def text(self, tag, x, y, lines, size, bold=False, color=(0, 0, 0), leading=1.3, alt=None):
        """Escribe liñas como un elemento (H1, P, LI…). Devolve a y seguinte."""
        font = "/F2" if bold else "/F1"
        ops = [f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg", "BT"]
        for line in lines:
            y -= size * leading
            ops.append(f"{font} {size} Tf 1 0 0 1 {x:.1f} {y:.1f} Tm ({_esc(line)}) Tj")
        ops.append("ET")
        mcid = self._mark(tag, ops)
        self.elements.append((tag, [mcid], {"alt": alt} if alt else {}))
        return y

    def figure(self, ops, alt):
        mcid = self._mark("Figure", ops)
        self.elements.append(("Figure", [mcid], {"alt": alt}))

    def group(self, tag, children):
        """Agrupa elementos xa engadidos (p. ex. L con LI) nun só nivel da árbore."""
        self.elements.append((tag, children, {}))


def qr_ops(data, x, y, size):
    qr = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)
    cell = size / n
    ops = ["0 0 0 rg"]
    for r, row in enumerate(matrix):
        for c, dark in enumerate(row):
            if dark:
                ops.append(
                    f"{x + c * cell:.2f} {y + (n - 1 - r) * cell:.2f} {cell + 0.05:.2f} {cell + 0.05:.2f} re"
                )
    ops.append("f")
    return ops


def _crest_ops(municipality, x, y, size, image_name=None):
    """Escudo: imaxe do concello se a ten; se non, círculo coa cor do concello e as iniciais."""
    if image_name:
        return [f"q {size} 0 0 {size} {x} {y} cm /{image_name} Do Q"]
    r, g, b = _hex_rgb(municipality.accent_color)
    k = 0.5523 * size / 2
    cx, cy, rad = x + size / 2, y + size / 2, size / 2
    circle = (
        f"{cx + rad:.1f} {cy:.1f} m "
        f"{cx + rad:.1f} {cy + k:.1f} {cx + k:.1f} {cy + rad:.1f} {cx:.1f} {cy + rad:.1f} c "
        f"{cx - k:.1f} {cy + rad:.1f} {cx - rad:.1f} {cy + k:.1f} {cx - rad:.1f} {cy:.1f} c "
        f"{cx - rad:.1f} {cy - k:.1f} {cx - k:.1f} {cy - rad:.1f} {cx:.1f} {cy - rad:.1f} c "
        f"{cx + k:.1f} {cy - rad:.1f} {cx + rad:.1f} {cy - k:.1f} {cx + rad:.1f} {cy:.1f} c f"
    )
    initials = municipality.initials
    tw = text_width(initials, 20, True)
    return [
        f"{r:.3f} {g:.3f} {b:.3f} rg",
        circle,
        "1 1 1 rg",
        f"BT /F2 20 Tf 1 0 0 1 {cx - tw / 2:.1f} {cy - 7:.1f} Tm ({_esc(initials)}) Tj ET",
    ]


def _jpeg_logo(municipality):
    """Escudo en JPEG (DCTDecode) se o concello subiu un; se non, None."""
    if not municipality.coat_of_arms:
        return None
    try:
        from PIL import Image

        with municipality.coat_of_arms.open("rb") as fh:
            img = Image.open(fh).convert("RGB")
        img.thumbnail((240, 240))
        canvas = Image.new("RGB", (max(img.size),) * 2, "white")
        canvas.paste(img, ((canvas.width - img.width) // 2, (canvas.height - img.height) // 2))
        buf = io.BytesIO()
        canvas.save(buf, format="JPEG", quality=88)
        return canvas.width, canvas.height, buf.getvalue()
    except Exception:  # noqa: BLE001 — un escudo estragado non debe impedir o cartel
        return None


def build_poster(municipality, facility=None, url="", *, template=False):
    """PDF do cartel dunha instalación ou, con `template=True` (ou sen instalación), a plantilla
    xenérica do concello co seu escudo e os campos en branco para cubrir a man."""
    from django.utils.translation import get_language

    m = municipality
    template = template or facility is None
    page = TaggedPage()
    logo = _jpeg_logo(m)
    width = PAGE_W - 2 * MARGIN
    # Banda superior (decorativa) e escudo
    r, g, b = _hex_rgb(m.accent_color)
    page.artifact([f"{r:.3f} {g:.3f} {b:.3f} rg", f"0 {PAGE_H - 12} {PAGE_W} 12 re f"])
    crest = 64
    page.figure(
        _crest_ops(m, MARGIN, PAGE_H - 40 - crest, crest, "Im1" if logo else None),
        _("Escudo do Concello de %(c)s") % {"c": m.name},
    )
    y = PAGE_H - 34
    y = page.text("P", MARGIN + crest + 16, y, [_("Concello de %(c)s") % {"c": m.name}], 16, True)
    y = page.text("P", MARGIN + crest + 16, y, [_("Servizo municipal de deportes")], 12)
    y = PAGE_H - 40 - crest - 18
    title = facility.name if not template else _("Nome da instalación: ______________________")
    y = page.text("H1", MARGIN, y, wrap(title, 28, width, True), 28, True)
    # QR e indicación
    qr_size = 168
    top = y - 14
    if not template:
        alt = _("Código QR para rexistrar a entrada ou reservar. Enderezo: %(u)s") % {"u": url}
        page.figure(qr_ops(url, MARGIN, top - qr_size, qr_size), alt)
        tx = MARGIN + qr_size + 22
        tw = width - qr_size - 22
        ty = page.text(
            "H2",
            tx,
            top + 4,
            wrap(
                _("Ao entrar, escanea o código")
                if facility.access_level == 0
                else _("Reserva escaneando o código"),
                17,
                tw,
                True,
            ),
            17,
            True,
        )
        ty = page.text(
            "P",
            tx,
            ty - 2,
            wrap(
                _("Rexistra a túa entrada co móbil. Se tes reserva, marcarase como usada.")
                if facility.access_level == 0
                else _("Consulta os horarios libres e reserva desde o móbil."),
                12,
                tw,
            ),
            12,
        )
        page.text("P", tx, ty - 4, wrap(url, 10, tw), 10)
        y = top - qr_size - 18
    else:
        page.artifact(["0.6 0.6 0.6 RG 1 w", f"{MARGIN} {top - 150} 150 150 re S"])
        page.text(
            "P", MARGIN + 170, top + 4, wrap(_("Pega aquí o QR da instalación."), 13, 250), 13
        )
        y = top - 168
    # Normas resumidas
    y = page.text("H2", MARGIN, y, [_("Normas de uso")], 16, True)
    rules = facility.current_rules() if facility and not template else None
    items = (rules.lines()[:6] if rules else []) or (
        ["______________________________________________"] * 4
        if template
        else [_("Consulta as normas na web do concello.")]
    )
    li_start = len(page.elements)
    for item in items:
        lines = wrap(f"• {item}", 12, width)
        y = page.text("LI", MARGIN, y, lines, 12, leading=1.35)
    page.group("L", list(range(li_start, len(page.elements))))
    # Protocolo de accidentes e DEA
    y -= 8
    y = page.text("H2", MARGIN, y, [_("En caso de accidente")], 16, True)
    protocol = (facility.accident_protocol if facility and not template else "") or _(
        "1. Mantén a calma e protexe a persoa ferida sen movela se non hai perigo.\n"
        "2. Chama ao 112 e explica onde estás e que pasou.\n"
        "3. Se non respira, empeza a reanimación e pide o DEA.\n"
        "4. Avisa ao concello."
    )
    y = page.text("P", MARGIN, y, wrap(protocol, 12, width), 12, leading=1.35)
    aed = facility.aed_location if facility and not template else ""
    y = page.text(
        "P",
        MARGIN,
        y - 2,
        wrap(
            _("DEA (desfibrilador) máis próximo: %(d)s")
            % {
                "d": aed
                or ("____________________________" if template else _("pregunta no concello"))
            },
            12,
            width,
            True,
        ),
        12,
        True,
    )
    # Caixa do 112 e teléfono do concello
    box_h = 74
    by = max(MARGIN + 40, y - 18 - box_h)
    page.artifact(["0.62 0.05 0.05 rg", f"{MARGIN} {by} {width / 2 - 8:.1f} {box_h} re f"])
    page.text("P", MARGIN + 14, by + box_h - 6, [_("Emerxencias")], 13, True, color=(1, 1, 1))
    page.text("P", MARGIN + 14, by + box_h - 24, ["112"], 34, True, color=(1, 1, 1))
    cx = MARGIN + width / 2 + 8
    page.artifact(["0 0 0 RG 1.5 w", f"{cx:.1f} {by} {width / 2 - 8:.1f} {box_h} re S"])
    page.text("P", cx + 14, by + box_h - 6, [_("Concello · deportes")], 13, True)
    page.text("P", cx + 14, by + box_h - 26, [m.contact_phone or "—"], 22, True)
    if m.contact_email:
        page.text("P", cx + 14, by + 10 + 12, [m.contact_email], 11)
    # Pé (decorativo + texto)
    page.text(
        "P",
        MARGIN,
        MARGIN - 6,
        [
            _(
                "Avarías: botón «Incidencia ou seguridade» da app. Cartel xerado o %(d)s con Eira (software libre)."
            )
            % {"d": timezone.localdate().strftime("%d/%m/%Y")}
        ],
        9,
    )
    title = (
        _("Cartel · %(f)s") % {"f": facility.name}
        if not template
        else _("Plantilla de cartel · Concello de %(c)s") % {"c": m.name}
    )
    lang = "es-ES" if (get_language() or "gl").startswith("es") else "gl-ES"
    return _assemble(page, title, lang=lang, logo=logo)


def _assemble(page, title, lang, logo=None):
    content = zlib.compress("\n".join(page.ops).encode("latin-1"))
    objects = {}
    # 1 Catalog · 2 Pages · 3 Page · 4 F1 · 5 F2 · 6 Contents · 7 Info · 8 StructTreeRoot
    # 9 Document · 10 ParentTree · 11 Metadata · 12 Image · 13+ elementos
    first_elem = 13
    elem_ids = {}
    next_id = first_elem
    for i in range(len(page.elements)):
        elem_ids[i] = next_id
        next_id += 1
    grouped = {child for tag, children, _a in page.elements if tag == "L" for child in children}
    mcid_owner = {}
    for i, (tag, kids, attrs) in enumerate(page.elements):
        if tag == "L":
            parent = 9
            kids_ref = " ".join(f"{elem_ids[c]} 0 R" for c in kids)
            objects[elem_ids[i]] = f"<< /Type /StructElem /S /L /P {parent} 0 R /K [{kids_ref}] >>"
            continue
        parent = next(
            (elem_ids[j] for j, (t, ks, _a) in enumerate(page.elements) if t == "L" and i in ks), 9
        )
        alt = f" /Alt ({_esc(attrs['alt'])})" if attrs.get("alt") else ""
        tag_name = "LBody" if tag == "LI" else tag
        k = " ".join(f"<< /Type /MCR /Pg 3 0 R /MCID {mc} >>" for mc in kids)
        body = f"<< /Type /StructElem /S /{tag_name} /P {parent} 0 R /K [{k}]{alt} >>"
        if tag == "LI":
            # LI > LBody (estrutura de lista correcta)
            objects[elem_ids[i]] = (
                f"<< /Type /StructElem /S /LI /P {parent} 0 R /K [{next_id} 0 R] >>"
            )
            objects[next_id] = body.replace(f"/P {parent} 0 R", f"/P {elem_ids[i]} 0 R")
            for mc in kids:
                mcid_owner[mc] = next_id
            next_id += 1
        else:
            objects[elem_ids[i]] = body
            for mc in kids:
                mcid_owner[mc] = elem_ids[i]
    top_level = [elem_ids[i] for i in range(len(page.elements)) if i not in grouped]
    parent_tree = " ".join(f"{mcid_owner[mc]} 0 R" for mc in range(page.mcid))
    now = dt.datetime.now(dt.UTC).strftime("%Y%m%d%H%M%SZ")
    xmp = (
        '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:pdfuaid="http://www.aiim.org/pdfua/ns/id/">'
        f'<dc:title><rdf:Alt><rdf:li xml:lang="x-default">{_xml(title)}</rdf:li></rdf:Alt></dc:title>'
        f"<dc:language><rdf:Bag><rdf:li>{lang}</rdf:li></rdf:Bag></dc:language>"
        "</rdf:Description></rdf:RDF></x:xmpmeta>"
        '<?xpacket end="w"?>'
    ).encode()
    resources = "/Font << /F1 4 0 R /F2 5 0 R >>"
    if logo:
        resources += " /XObject << /Im1 12 0 R >>"
    objects.update(
        {
            1: f"<< /Type /Catalog /Pages 2 0 R /Lang ({lang}) /MarkInfo << /Marked true >> "
            "/StructTreeRoot 8 0 R /Metadata 11 0 R /ViewerPreferences << /DisplayDocTitle true >> >>",
            2: "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            3: f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Resources << {resources} >> /Contents 6 0 R /StructParents 0 /Tabs /S >>",
            4: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            5: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
            7: f"<< /Title ({_esc(title)}) /Producer (Eira) /CreationDate (D:{now}) >>",
            8: "<< /Type /StructTreeRoot /K [9 0 R] /ParentTree 10 0 R /ParentTreeNextKey 1 >>",
            9: "<< /Type /StructElem /S /Document /P 8 0 R /K ["
            + " ".join(f"{i} 0 R" for i in top_level)
            + "] >>",
            10: f"<< /Nums [0 [{parent_tree}]] >>",
        }
    )
    streams = {
        6: (f"<< /Length {len(content)} /Filter /FlateDecode >>", content),
        11: (f"<< /Type /Metadata /Subtype /XML /Length {len(xmp)} >>", xmp),
    }
    if logo:
        w, h, data = logo
        streams[12] = (
            f"<< /Type /XObject /Subtype /Image /Width {w} /Height {h} /ColorSpace /DeviceRGB "
            f"/BitsPerComponent 8 /Filter /DCTDecode /Length {len(data)} >>",
            data,
        )
    else:
        objects[12] = "<< >>"
    total = max([*objects, *streams])
    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for i in range(1, total + 1):
        offsets[i] = len(out)
        out += f"{i} 0 obj\n".encode()
        if i in streams:
            head, data = streams[i]
            out += head.encode("latin-1") + b"\nstream\n" + data + b"\nendstream"
        else:
            out += objects.get(i, "null").encode("latin-1")
        out += b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {total + 1}\n0000000000 65535 f \n".encode()
    for i in range(1, total + 1):
        out += f"{offsets[i]:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {total + 1} /Root 1 0 R /Info 7 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode()
    return bytes(out)


def _xml(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
