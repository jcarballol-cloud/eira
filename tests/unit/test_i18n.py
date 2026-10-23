# SPDX-License-Identifier: EUPL-1.2
"""Galego e castelán completos: ningunha cadea sen traducir nin con marcas `fuzzy`."""

import re
from pathlib import Path

import polib
import pytest

ROOT = Path(__file__).resolve().parents[2]
PLACEHOLDER = re.compile(r"%\(\w+\)s|%s")


@pytest.mark.parametrize("lang", ["gl", "es"])
def test_catalog_complete(lang):
    po = polib.pofile(str(ROOT / "locale" / lang / "LC_MESSAGES" / "django.po"))
    assert po.percent_translated() == 100, [e.msgid for e in po.untranslated_entries()][:10]
    assert not po.fuzzy_entries()
    for entry in po.translated_entries():
        if not entry.msgid_plural:
            assert sorted(PLACEHOLDER.findall(entry.msgid)) == sorted(PLACEHOLDER.findall(entry.msgstr)), entry.msgid
