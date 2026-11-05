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
            assert sorted(PLACEHOLDER.findall(entry.msgid)) == sorted(
                PLACEHOLDER.findall(entry.msgstr)
            ), entry.msgid


def test_every_code_string_is_in_the_catalog():
    """v1.5: sen GNU gettext, comproba que o castelán ten todas as cadeas de plantillas e Python."""
    import sys

    sys.path.insert(0, str(ROOT / "tools"))
    import i18n_check

    known = {
        e.msgid for e in polib.pofile(str(ROOT / "locale" / "es" / "LC_MESSAGES" / "django.po"))
    }
    missing = sorted(k for k in i18n_check.collect() if k and k not in known)
    assert not missing, missing[:10]
