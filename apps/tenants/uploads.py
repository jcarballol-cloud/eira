# SPDX-License-Identifier: EUPL-1.2
"""Validación e limpeza de imaxes subidas: tamaño máximo, formato real e eliminación de EXIF/GPS."""

import io
import secrets

from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "MPO"}
MAX_SIDE = 1600


def clean_image(upload):
    """Valida a imaxe e devolve un ContentFile JPEG novo, reescalado e sen metadatos."""
    if upload.size > settings.EIRA_MAX_UPLOAD_BYTES:
        raise forms.ValidationError(
            _("A foto é demasiado grande (máximo %(mb)s MB).")
            % {"mb": settings.EIRA_MAX_UPLOAD_BYTES // (1024 * 1024)}
        )
    try:
        upload.seek(0)
        probe = Image.open(upload)
        probe.verify()
        upload.seek(0)
        image = Image.open(upload)
        if image.format not in ALLOWED_FORMATS:
            raise forms.ValidationError(_("Formato non admitido. Usa JPEG, PNG ou WebP."))
        image = ImageOps.exif_transpose(image)  # respecta a orientación antes de descartar o EXIF
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise forms.ValidationError(_("O ficheiro non é unha imaxe válida.")) from exc
    image = image.convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    # Gárdase unha imaxe nova: sen EXIF, sen GPS, sen perfil nin miniatura incrustada.
    image.save(out, format="JPEG", quality=85, optimize=True)
    return ContentFile(out.getvalue(), name=f"{secrets.token_hex(8)}.jpg")
