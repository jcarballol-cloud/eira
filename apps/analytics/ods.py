# SPDX-License-Identifier: EUPL-1.2
"""Escritor mínimo de follas OpenDocument (.ods, ISO/IEC 26300) sen dependencias."""

import io
import zipfile
from numbers import Number
from xml.sax.saxutils import escape

MIMETYPE = "application/vnd.oasis.opendocument.spreadsheet"
MANIFEST = f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
 <manifest:file-entry manifest:full-path="/" manifest:media-type="{MIMETYPE}"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
</manifest:manifest>"""


def _cell(value):
    if isinstance(value, Number) and not isinstance(value, bool):
        return f'<table:table-cell office:value-type="float" office:value="{value}"><text:p>{value}</text:p></table:table-cell>'
    text = escape("" if value is None else str(value))
    return (
        f'<table:table-cell office:value-type="string"><text:p>{text}</text:p></table:table-cell>'
    )


def write_ods(sheet_name, header, rows):
    body = "".join(
        "<table:table-row>" + "".join(_cell(v) for v in row) + "</table:table-row>"
        for row in [header, *rows]
    )
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.2">'
        f'<office:body><office:spreadsheet><table:table table:name="{escape(sheet_name)}">{body}'
        "</table:table></office:spreadsheet></office:body></office:document-content>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(zipfile.ZipInfo("mimetype"), MIMETYPE, compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/manifest.xml", MANIFEST, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("content.xml", content, compress_type=zipfile.ZIP_DEFLATED)
    return buf.getvalue()
