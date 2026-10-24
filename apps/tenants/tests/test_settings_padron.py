# SPDX-License-Identifier: EUPL-1.2
"""v4.1: en produción (DEBUG=0 e sen ferramentas de demo) EIRA_PADRON_SECRET é obrigatorio."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def boot(**env):
    clean = {k: v for k, v in os.environ.items() if not k.startswith("EIRA_")}
    clean.update(
        {
            "DJANGO_SETTINGS_MODULE": "eira.settings",
            "PYTHONPATH": str(ROOT),
            "EIRA_SECRET_KEY": "proba-" + "x" * 50,
            **env,
        }
    )
    return subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=ROOT,
        env=clean,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize(
    "env, ok",
    [
        ({"EIRA_DEBUG": "0", "EIRA_DEMO_TOOLS": "0"}, False),
        ({"EIRA_DEBUG": "0", "EIRA_DEMO_TOOLS": "0", "EIRA_PADRON_SECRET": "s" * 40}, True),
        ({"EIRA_DEBUG": "0", "EIRA_DEMO_TOOLS": "1"}, True),  # demo con datos ficticios
        ({"EIRA_DEBUG": "1"}, True),  # desenvolvemento
    ],
)
def test_padron_secret_required_in_production(env, ok):
    r = boot(**env)
    assert (r.returncode == 0) is ok, r.stderr[-500:]
    if not ok:
        assert "Falta EIRA_PADRON_SECRET" in r.stderr
