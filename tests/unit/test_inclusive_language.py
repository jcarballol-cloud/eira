# SPDX-License-Identifier: EUPL-1.2
"""v5 · E: linguaxe inclusiva nas cadeas da interface (galego e castelán).

Ver docs/accesibilidade/linguaxe-inclusiva.md. Busca as formas que hai que evitar nos `msgid`
(galego) e nos `msgstr` (castelán) do catálogo, e tamén nas plantillas."""

import re
from pathlib import Path

import polib
import pytest

ROOT = Path(__file__).resolve().parents[2]

AVOID = {
    "gl": [
        r"\b\w+o/a\b",
        r"\b\w+a/o\b",
        r"\bveciños?\b",
        r"\bo monitor\b",
        r"\bpolo monitor\b",
        r"\bmonitor/a\b",
        r"\busuarios?\b",
        r"\bo operario\b",
        r"\boperarios\b",
    ],
    "es": [
        r"\b\w+o/a\b",
        r"\b\w+a/o\b",
        r"\bvecinos?\b",
        r"\bel monitor\b",
        r"\bmonitor/a\b",
        r"\busuarios?\b",
        r"\bel operario\b",
        r"\boperarios\b",
    ],
}
# Excepcións con motivo (nomes propios, citas legais, categorías de datos do RXPD…)
ALLOWED = {
    "Operario/a",  # cabeceira dunha columna da matriz (documento, non interface); non debería chegar
}


def _hits(text, lang):
    return [p for p in AVOID[lang] if re.search(p, text, flags=re.IGNORECASE)]


def test_galician_msgids_are_inclusive():
    po = polib.pofile(str(ROOT / "locale" / "gl" / "LC_MESSAGES" / "django.po"))
    bad = [e.msgid for e in po if e.msgid not in ALLOWED and _hits(e.msgid, "gl")]
    assert not bad, bad[:10]


def test_spanish_msgstrs_are_inclusive():
    po = polib.pofile(str(ROOT / "locale" / "es" / "LC_MESSAGES" / "django.po"))
    bad = [e.msgstr for e in po if e.msgstr and _hits(e.msgstr, "es")]
    assert not bad, bad[:10]


@pytest.mark.parametrize("path", sorted((ROOT / "templates").rglob("*.html")), ids=lambda p: p.name)
def test_templates_have_no_slash_forms(path):
    text = path.read_text(encoding="utf-8")
    # Só o texto visible das etiquetas de tradución
    strings = re.findall(
        r"{% (?:translate|blocktranslate)[^%]*%}(.*?)(?:{% endblocktranslate %}|$)", text
    )
    strings += re.findall(r'{% translate "([^"]+)"', text)
    bad = [s for s in strings if _hits(s, "gl")]
    assert not bad, bad[:5]
