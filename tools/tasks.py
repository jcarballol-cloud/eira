#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
"""Tarefas do proxecto, equivalentes ao Makefile, para sistemas sen `make` (p. ex. Windows).

python tools/tasks.py dev | seed | test | e2e | lint | licenses | i18n | openapi | screenshots
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
ENV = {**os.environ, "EIRA_DEBUG": os.environ.get("EIRA_DEBUG", "1"), "PYTHONPATH": str(ROOT)}


def run(*args, env=None):
    print("$", " ".join(str(a) for a in args), flush=True)
    result = subprocess.run([str(a) for a in args], cwd=ROOT, env=env or ENV)
    if result.returncode:
        sys.exit(result.returncode)


def manage(*args):
    run(PY, "manage.py", *args)


def i18n():
    run(PY, "tools/compile_messages.py")


def seed():
    i18n()
    manage("migrate", "--noinput")
    manage("seed_demo")


def dev():
    seed()
    manage("runserver", "127.0.0.1:8000")


def test():
    i18n()
    run(PY, "-m", "pytest", "apps", "tests/unit")


def e2e():
    i18n()
    run(PY, "-m", "pytest", "tests/e2e", "-m", "e2e", "-p", "no:cacheprovider")


def lint():
    run(PY, "-m", "ruff", "check", ".")
    run(PY, "-m", "ruff", "format", "--check", ".")


def licenses():
    run(PY, "tools/check_licenses.py")


def openapi():
    # O esquema depende do motor (límites de enteiros): xérase sempre igual, sen tocar a BD real.
    ENV["DATABASE_URL"] = "sqlite:///:memory:"
    manage("spectacular", "--validate", "--fail-on-warn", "--file", "docs/api/openapi.yaml")


def publiccode():
    """Valida publiccode.yml co validador oficial (Docker). Sen rede: o repositorio aínda non é público."""
    run(
        "docker",
        "run",
        "--rm",
        "-v",
        f"{ROOT}:/data:ro",
        "italia/publiccode-parser-go",
        "-no-network",
        "-path",
        "/data",
        "/data/publiccode.yml",
    )


def screenshots():
    i18n()
    run(PY, "-m", "pytest", "tests/e2e/test_screenshots.py", "-m", "e2e", "-p", "no:cacheprovider")


TASKS = {
    f.__name__: f
    for f in (dev, seed, test, e2e, lint, licenses, i18n, openapi, publiccode, screenshots)
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in TASKS:
        print(__doc__)
        sys.exit(2)
    TASKS[sys.argv[1]]()
