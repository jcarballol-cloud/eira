# SPDX-License-Identifier: EUPL-1.2
"""Fotos das instalacións.

- Se o concello sube unha foto, úsase esa (sen EXIF, en WebP de 480/960/1440 px).
- Se non, unha foto de detalle do tipo de instalación da biblioteca libre de `static/img/fotos/`
  (Wikimedia Commons, CC0 / CC BY / CC BY-SA / dominio público; créditos en CREDITS.md e /creditos/).
"""

import io
import json
from functools import cache
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _
from PIL import Image

SIZES = (480, 960, 1440)
STOCK_DIR = Path(settings.BASE_DIR) / "static" / "img" / "fotos"

ALT = {
    "padel-1": _("Pista de pádel de cristal, baleira, sobre céspede artificial"),
    "padel-2": _("Pista de pádel cuberta de chan azul, baleira"),
    "padel-3": _("Fila de pistas de pádel cubertas baixo unha carpa"),
    "pool-1": _("Bloque de saída e corcheiras dunha piscina"),
    "pool-2": _("Escaleira de acceso e número de rúa dunha piscina"),
    "pool-3": _("Plataformas de saída numeradas dunha piscina cuberta"),
    "gym-1": _("Balóns medicinais no chan dunha sala de musculación"),
    "gym-2": _("Discos e mancuernas nun soporte do ximnasio"),
    "gym-3": _("Sala de musculación con máquinas e bancos, baleira"),
    "sports_hall-1": _("Pavillón con estrutura de madeira e pista de parqué"),
    "sports_hall-2": _("Pavillón baleiro con grandes ventás e chan brillante"),
    "grass_field-1": _("Detalle da rede dunha portería de fútbol"),
    "grass_field-2": _("Portería de fútbol ao solpor nun campo de herba"),
    "outdoor_court-1": _("Pista de baloncesto descuberta nun parque con árbores"),
    "outdoor_court-2": _("Canastra de baloncesto descuberta co balón no aire"),
    "outdoor_court-3": _("Pista polideportiva cuberta con chan verde e vermello"),
}


@cache
def credits():
    path = STOCK_DIR / "credits.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _stock(kind, seed):
    items = [c for c in credits() if c["kind"] == kind] or credits()
    return items[seed % len(items)] if items else None


def _srcset(url_for, max_width):
    sizes = [s for s in SIZES if s <= max_width] or [SIZES[0]]
    return ", ".join(f"{url_for(s)} {s}w" for s in sizes), url_for(sizes[min(1, len(sizes) - 1)])


def photo_for(facility):
    """Datos para pintar a foto: src, srcset, alt e crédito (só nas fotos da biblioteca)."""
    if facility.photo:
        base = facility.photo.name.rsplit(".", 1)[0]
        if default_storage.exists(f"{base}-480.webp"):
            available = max(s for s in SIZES if default_storage.exists(f"{base}-{s}.webp"))
            srcset, src = _srcset(lambda s: default_storage.url(f"{base}-{s}.webp"), available)
        else:
            srcset, src = "", facility.photo.url
        return {"src": src, "srcset": srcset, "alt": facility.photo_alt, "credit": None}
    item = _stock(facility.kind, facility.pk or 0)
    if not item:
        return None
    srcset, src = _srcset(
        lambda s: static(f"img/fotos/{item['file']}-{s}.webp"), item.get("max_width", 1440)
    )
    return {"src": src, "srcset": srcset, "alt": ALT.get(item["file"], ""), "credit": item}


def make_variants(fieldfile):
    """Xera as variantes WebP dunha foto subida (xa limpa de metadatos por clean_image)."""
    if not fieldfile:
        return
    base = fieldfile.name.rsplit(".", 1)[0]
    with fieldfile.open("rb") as fh:
        image = Image.open(io.BytesIO(fh.read())).convert("RGB")
    for size in SIZES:
        if size > image.width and size != SIZES[0]:
            break
        im = image.copy()
        im.thumbnail((size, size * 2))
        out = io.BytesIO()
        im.save(out, "WEBP", quality=80, method=6)
        name = f"{base}-{size}.webp"
        if default_storage.exists(name):
            default_storage.delete(name)
        default_storage.save(name, ContentFile(out.getvalue()))
