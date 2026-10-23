#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
"""Compila locale/*/LC_MESSAGES/*.po en .mo con polib (non require GNU gettext)."""

from pathlib import Path

import polib

ROOT = Path(__file__).resolve().parent.parent

for po_path in sorted((ROOT / "locale").glob("*/LC_MESSAGES/*.po")):
    po = polib.pofile(str(po_path))
    po.save_as_mofile(str(po_path.with_suffix(".mo")))
    print(f"{po_path.relative_to(ROOT)}: {po.percent_translated()} % traducido")
