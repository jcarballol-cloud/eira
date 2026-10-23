# SPDX-License-Identifier: EUPL-1.2
"""Xerador mínimo de PDF (texto en Helvetica, codificación WinAnsi) para os recibos.

Sen dependencias: suficiente para un recibo dunha páxina. Admite os caracteres do galego e do
castelán (á, é, í, ó, ú, ñ, ç, ü, ª, º, €, ·).
"""


def _esc(text):
    raw = text.encode("cp1252", errors="replace")
    out = []
    for byte in raw:
        ch = chr(byte)
        if ch in "()\\":
            out.append("\\" + ch)
        elif byte < 32 or byte > 126:
            out.append(f"\\{byte:03o}")
        else:
            out.append(ch)
    return "".join(out)


def simple_pdf(lines, title="Recibo"):
    """lines: lista de (texto, tamaño_de_letra, negra). Devolve bytes dun PDF A4 dunha páxina."""
    y = 800
    ops = ["BT"]
    for text, size, bold in lines:
        font = "/F2" if bold else "/F1"
        y -= int(size * 1.6)
        ops.append(f"{font} {size} Tf 1 0 0 1 56 {y} Tm ({_esc(text)}) Tj")
    ops.append("ET")
    stream = "\n".join(ops).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> "
        b"/Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Title (" + _esc(title).encode("latin-1") + b") /Producer (Eira) >>",
    ]
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info {len(objects)} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
