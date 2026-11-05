#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
"""v1.5: lista as cadeas da interface que faltan no catálogo, sen precisar GNU gettext.

Extrae os msgid das plantillas (co `templatize` de Django) e do Python (con `ast`) e compáraos con
locale/es. `--add FICHEIRO.json` engade as traducións {"msgid galego": "msgstr castelán"} (para
plurais, {"msgid": ["singular es", "plural es"]}) aos catálogos gl e es. Uso:
    python tools/i18n_check.py                 # lista o que falta (saída 1 se falta algo)
    python tools/i18n_check.py --add t.json
"""

import ast
import json
import os
import re
import sys
from pathlib import Path

import polib

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("EIRA_DEBUG", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eira.settings")

SINGULAR = {"_", "gettext", "gettext_lazy", "gettext_noop", "pgettext"}
PLURAL = {"ngettext", "ngettext_lazy"}
TEMPLATE_CALL = re.compile(
    r"\b(n?gettext)\(u('(?:[^'\\]|\\.)*')(?:,\s*u('(?:[^'\\]|\\.)*'))?", re.DOTALL
)
SKIP = {".venv", "__pycache__", "migrations", "tests", "node_modules", "staticfiles"}


def from_python(source):
    found = {}
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and node.args):
            continue
        name = getattr(node.func, "id", getattr(node.func, "attr", ""))
        if name not in SINGULAR | PLURAL:
            continue
        values = [a.value if isinstance(a, ast.Constant) else None for a in node.args[:2]]
        if not isinstance(values[0], str):
            continue
        found[values[0]] = values[1] if name in PLURAL and len(values) > 1 else None
    return found


def from_template(text):
    from django.utils.translation.template import templatize

    found = {}
    for match in TEMPLATE_CALL.finditer(templatize(text)):
        singular = ast.literal_eval(match.group(2))
        plural = ast.literal_eval(match.group(3)) if match.group(3) else None
        found[singular] = plural
    return found


def collect():
    found = {}
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT).parts
        if SKIP & set(rel) or rel[0] in {"tools", "docs"}:
            continue
        found.update(from_python(path.read_text(encoding="utf-8")))
    for path in (ROOT / "templates").rglob("*"):
        if path.suffix in {".html", ".txt"}:
            found.update(from_template(path.read_text(encoding="utf-8")))
    return found


def catalog(lang):
    return ROOT / "locale" / lang / "LC_MESSAGES" / "django.po"


def add(path):
    pairs = json.loads(Path(path).read_text(encoding="utf-8"))
    code = collect()
    for lang in ("gl", "es"):
        po = polib.pofile(str(catalog(lang)))
        known = {e.msgid: e for e in po}
        for msgid, es in pairs.items():
            plural = code.get(msgid)
            if isinstance(es, list) and not plural:
                raise SystemExit(f"Plural sen msgid_plural no código: {msgid}")
            entry = known.get(msgid)
            if entry is None:
                entry = polib.POEntry(msgid=msgid)
                po.append(entry)
            if isinstance(es, list):
                entry.msgid_plural = plural
                entry.msgstr_plural = {0: msgid, 1: plural} if lang == "gl" else dict(enumerate(es))
            else:
                entry.msgstr = msgid if lang == "gl" else es
        po.save()


def main():
    import django

    django.setup()
    if len(sys.argv) == 3 and sys.argv[1] == "--add":
        add(sys.argv[2])
    known = {e.msgid for e in polib.pofile(str(catalog("es")))}
    missing = {k: v for k, v in collect().items() if k and k not in known}
    print(json.dumps(missing, ensure_ascii=False, indent=1))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
