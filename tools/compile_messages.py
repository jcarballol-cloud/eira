#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
"""Compila locale/*/LC_MESSAGES/*.po en .mo con polib (non require GNU gettext).

Os msgid xa están en galego (idioma por defecto): no catálogo `gl` copiase msgid → msgstr
para que quede formalmente completo.
"""

from pathlib import Path

import polib

ROOT = Path(__file__).resolve().parent.parent

for po_path in sorted((ROOT / "locale").glob("*/LC_MESSAGES/*.po")):
    po = polib.pofile(str(po_path))
    if po_path.parts[-3] == "gl":
        for entry in po:
            if entry.msgid_plural and not any(entry.msgstr_plural.values()):
                entry.msgstr_plural = {0: entry.msgid, 1: entry.msgid_plural}
            elif not entry.msgid_plural and not entry.msgstr:
                entry.msgstr = entry.msgid
            if "fuzzy" in entry.flags:
                entry.flags.remove("fuzzy")
        po.metadata["Language"] = "gl"
        po.metadata["Plural-Forms"] = "nplurals=2; plural=(n != 1);"
        po.save()
    po.save_as_mofile(str(po_path.with_suffix(".mo")))
    print(f"{po_path.relative_to(ROOT)}: {po.percent_translated()} % traducido")
