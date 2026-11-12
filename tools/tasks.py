#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
"""Tarefas do proxecto, equivalentes ao Makefile, para sistemas sen `make` (p. ex. Windows).

python tools/tasks.py dev | seed | test | e2e | e2e_pg | lint | licenses | i18n | openapi | screenshots | video | pitch | annex
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
    run(PY, "-m", "pytest", "tests/e2e", "-m", "e2e and not video", "-p", "no:cacheprovider")


def e2e_pg():
    """E2E contra PostgreSQL nun contedor efémero, coma na CI (o servidor de probas con SQLite
    pode dar algún 400 «session was deleted» ocasional por compartir a conexión)."""
    import time

    name, port = "eira-e2e-pg", os.environ.get("EIRA_E2E_PG_PORT", "55432")
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    run(
        "docker", "run", "-d", "--rm", "--name", name,
        "-e", "POSTGRES_DB=eira", "-e", "POSTGRES_USER=eira", "-e", "POSTGRES_PASSWORD=eira",
        "-p", f"127.0.0.1:{port}:5432", "--tmpfs", "/var/lib/postgresql/data",
        "postgres:16-alpine",
    )  # fmt: skip
    try:
        for _ in range(60):
            ready = subprocess.run(
                ["docker", "exec", name, "pg_isready", "-U", "eira", "-h", "127.0.0.1"],
                capture_output=True,
            )
            if ready.returncode == 0:
                break
            time.sleep(1)
        ENV["DATABASE_URL"] = f"postgres://eira:eira@127.0.0.1:{port}/eira"
        e2e()
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


def video():
    i18n()
    run(PY, "-m", "pytest", "tests/e2e/test_video.py", "-m", "video", "-p", "no:cacheprovider")


def pitch():
    # Vídeo final do pitch: 1920×1080, MP4 + WebM + .vtt en docs/demo/ (ignorados polo git)
    i18n()
    ENV["EIRA_AI_ENABLED"] = "0"
    run(
        PY,
        "-m",
        "pytest",
        "tests/e2e/test_pitch_video.py",
        "-m",
        "video",
        "-s",
        "-p",
        "no:cacheprovider",
    )


def annex():
    # v5: vídeo anexo «Eira para o concello e a saúde» (≈ 60 s), en docs/demo/ (ignorado polo git)
    i18n()
    ENV["EIRA_AI_ENABLED"] = "0"
    run(
        PY,
        "-m",
        "pytest",
        "tests/e2e/test_annex_video.py",
        "-m",
        "video",
        "-s",
        "-p",
        "no:cacheprovider",
    )


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
    for f in (
        dev,
        seed,
        test,
        e2e,
        e2e_pg,
        lint,
        licenses,
        i18n,
        openapi,
        publiccode,
        screenshots,
        video,
        pitch,
        annex,
    )
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in TASKS:
        print(__doc__)
        sys.exit(2)
    TASKS[sys.argv[1]]()
