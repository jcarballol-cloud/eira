# SPDX-License-Identifier: EUPL-1.2
"""Xera as ilustracións optimizadas desde `assets-originais/` (que non se serve).

    python tools/build_illustrations.py

Saída en `static/img/ilustracions/<nome>-<ancho>.{avif,webp}`, sen metadatos. Pillow (HPND)."""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets-originais"
OUT = ROOT / "static" / "img" / "ilustracions"

# nome → anchos. As cabeceiras en 3 anchos (480, 960, 1600); os estados baleiros, máis pequenos.
SETS = {
    "cabecera-eira": (480, 960, 1600),
    "cabecera-eira-noite": (480, 960, 1600),
    "eira-icono-baleiro": (240, 480),
    "baleiro-reservas": (320, 640),
    "baleiro-avisos": (320, 640),
    "baleiro-mantemento": (320, 640),
}
QUALITY = {"webp": 78, "avif": 55}


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    report = []
    for name, widths in SETS.items():
        original = Image.open(SRC / f"{name}.png").convert("RGB")  # sen alfa nin metadatos
        for w in widths:
            h = round(original.height * w / original.width)
            img = original.resize((w, h), Image.LANCZOS)
            for fmt, q in QUALITY.items():
                path = OUT / f"{name}-{w}.{fmt}"
                img.save(
                    path,
                    fmt.upper(),
                    quality=q,
                    **({"method": 6} if fmt == "webp" else {"speed": 4}),
                )
                report.append((path.name, path.stat().st_size // 1024))
    return report


if __name__ == "__main__":
    for name, kb in build():
        print(f"{name:42} {kb:>5} KB")
