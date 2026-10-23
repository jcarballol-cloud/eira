#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
"""Comproba que todo ficheiro de código propio leva a cabeceira SPDX EUPL-1.2."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG = "SPDX-License-Identifier: EUPL-1.2"
PATTERNS = [
    "**/*.py",
    "static/js/*.js",
    "static/css/*.css",
    "templates/**/*.js",
    "**/*.yml",
    "**/*.sh",
    "Dockerfile",
    "Makefile",
    "static/img/*.svg",
]
SKIP = {".venv", "migrations", "node_modules", "staticfiles", "vendor"}

missing = []
for pattern in PATTERNS:
    for path in ROOT.glob(pattern):
        if any(part in SKIP for part in path.relative_to(ROOT).parts) or not path.is_file():
            continue
        if TAG not in path.read_text(encoding="utf-8", errors="ignore")[:600]:
            missing.append(path.relative_to(ROOT))
for m in missing:
    print("Falta cabeceira SPDX:", m)
print(f"{len(missing)} ficheiros sen cabeceira")
sys.exit(1 if missing else 0)
