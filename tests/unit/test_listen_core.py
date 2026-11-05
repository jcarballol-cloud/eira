# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · A: lóxica do botón «Escoitar» (voz, velocidade, código, partición), executada en Node."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE, reason="Precisa Node para executar a lóxica en JS")

GL = {"lang": "gl-ES", "name": "Galego"}
ES = {"lang": "es-ES", "name": "Castelán"}
ES_MX = {"lang": "es-MX", "name": "México"}
EN = {"lang": "en-GB", "name": "Inglés"}


def call(fn, *args):
    code = (
        f"const c=require({json.dumps(str(ROOT / 'static/js/listen-core.js'))});"
        f"console.log(JSON.stringify(c.{fn}(...{json.dumps(args)})))"
    )
    out = subprocess.run(
        [NODE, "-e", code], capture_output=True, text=True, check=True, encoding="utf-8"
    )
    return json.loads(out.stdout)


def test_galician_voice_when_available():
    assert call("pickVoice", [EN, ES, GL], "gl") == {
        "voice": GL,
        "lang": "gl-ES",
        "fallback": False,
    }


def test_falls_back_to_spanish_with_notice():
    assert call("pickVoice", [EN, ES], "gl") == {"voice": ES, "lang": "es-ES", "fallback": True}


def test_spanish_interface_needs_no_notice():
    assert call("pickVoice", [GL, ES], "es") == {"voice": ES, "lang": "es-ES", "fallback": False}


def test_other_spanish_variant_is_accepted():
    assert call("pickVoice", [EN, ES_MX], "gl")["voice"] == ES_MX


def test_underscore_language_tags_android():
    assert call("pickVoice", [{"lang": "gl_ES", "name": "A"}], "gl")["lang"] == "gl-ES"


def test_no_voices_still_tries_spanish_tag():
    assert call("pickVoice", [], "gl") == {"voice": None, "lang": "es-ES", "fallback": True}


@pytest.mark.parametrize("setting,rate", [("normal", 1), ("slow", 0.75), (None, 1), ("x", 1)])
def test_rates(setting, rate):
    assert call("rateFor", setting) == rate


def test_code_is_spelled_with_pauses():
    assert call("spellCode", "123456") == "1 2 3, 4 5 6"
    assert call("spellCode", "12 34#") == "1 2 3, 4"


def test_chunks_respect_limit_and_keep_all_words():
    text = "Primeira frase curta. " + "palabra " * 80 + "Fin."
    parts = call("chunks", text, 100)
    assert all(len(p) <= 100 for p in parts)
    assert " ".join(parts).split() == text.split()


def test_chunks_empty():
    assert call("chunks", "   ") == []
