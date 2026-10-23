#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
"""Comproba que as dependencias instaladas teñen licenzas libres compatibles coa EUPL-1.2.

A EUPL-1.2 é compatible coas licenzas permisivas (MIT, BSD, Apache-2.0, ISC, PSF…) e inclúe
no seu anexo GPL-2.0/3.0, LGPL, AGPL, MPL-2.0, EPL, CeCILL, OSL e LiLiQ. Tamén se comproban os
recursos JavaScript vendorizados en static/vendor/.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALLOWED = [
    "MIT",
    "BSD",
    "Apache",
    "ISC",
    "PSF",
    "Python Software Foundation",
    "Unlicense",
    "0BSD",
    "Zero-Clause",
    "MPL-2.0",
    "Mozilla Public License 2.0",
    "LGPL",
    "GPL",
    "GNU General Public",
    "GNU Lesser",
    "EUPL",
    "Artistic",
    "Historical Permission",
    "HPND",
    "CC0",
    "Zope Public",
    "ZPL",
]
# Paquetes cuxa licenza non aparece nos metadatos pero está verificada manualmente.
KNOWN = {
    "pip-licenses": "MIT",
    "prettytable": "BSD-3-Clause",
    "text-unidecode": "Artistic-1.0 / GPL-2.0+ (dual)",
    "polib": "MIT",
    "axe-playwright-python": "MIT (dist-info/licenses/LICENSE); inclúe axe-core MPL-2.0",
}
VENDORED = {
    "static/vendor/htmx/LICENSE": "0BSD",
    "static/vendor/leaflet/LICENSE": "BSD-2-Clause",
}
IGNORE = {"eira", "pip", "setuptools", "wheel"}


def main():
    out = subprocess.run(
        [sys.executable, "-m", "piplicenses", "--format=json", "--with-system", "--from=mixed"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    bad = []
    for pkg in json.loads(out):
        name, lic = pkg["Name"], pkg["License"]
        if name.lower() in IGNORE:
            continue
        if name.lower() in KNOWN:
            lic = KNOWN[name.lower()]
        ok = any(a.lower() in lic.lower() for a in ALLOWED)
        print(f"{'OK ' if ok else 'KO '} {name:32} {lic[:70]}")
        if not ok:
            bad.append((name, lic))
    for path, lic in VENDORED.items():
        exists = (ROOT / path).exists()
        print(f"{'OK ' if exists else 'KO '} {path:32} {lic}")
        if not exists:
            bad.append((path, "falta o ficheiro de licenza"))
    if bad:
        print("\nLicenzas sen verificar:", *[f"  - {n}: {lic}" for n, lic in bad], sep="\n")
        sys.exit(1)
    print("\nTodas as dependencias teñen licenzas compatibles coa EUPL-1.2.")


if __name__ == "__main__":
    main()
