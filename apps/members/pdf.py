# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · H: carné imprimible en PDF etiquetado e tamaño tarxeta (85,6 × 54 mm, ID-1).

Reutiliza o xerador accesible do cartel (`apps/facilities/poster.py`): estrutura etiquetada,
idioma, título e QR como figura con texto alternativo. O QR impreso non caduca aos poucos
minutos (é papel): leva a versión do carné e a data de fin, e o concello pode anulalo."""

from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from apps.facilities.poster import (
    TaggedPage,
    _assemble,
    _crest_ops,
    _hex_rgb,
    _jpeg_logo,
    qr_ops,
    wrap,
)

from . import services

CARD_W, CARD_H = 243, 153  # puntos (85,6 × 54 mm)


def build_card(card, sports_pass=None):
    m = card.municipality
    user = card.user
    page = TaggedPage()
    logo = _jpeg_logo(m)
    r, g, b = _hex_rgb(m.accent_color)
    page.artifact([f"{r:.3f} {g:.3f} {b:.3f} rg", f"0 {CARD_H - 30} {CARD_W} 30 re f"])
    page.artifact(["0.6 0.6 0.6 RG 0.5 w", f"0.5 0.5 {CARD_W - 1} {CARD_H - 1} re S"])
    x0 = 10
    if logo:  # sen escudo propio, só o texto (o círculo coas iniciais non se vería na banda)
        page.figure(
            _crest_ops(m, 8, CARD_H - 27, 24, "Im1"),
            _("Escudo do Concello de %(c)s") % {"c": m.name},
        )
        x0 = 38
    page.text("H1", x0, CARD_H - 3, [_("Carné municipal de deportes")], 9, True, color=(1, 1, 1))
    page.text("P", x0, CARD_H - 14, [_("Concello de %(c)s") % {"c": m.name}], 7, color=(1, 1, 1))
    y = CARD_H - 36
    name = user.display_name or user.email.split("@")[0]
    y = page.text("P", 10, y, wrap(name, 11, 140, True)[:2], 11, True)
    if sports_pass:
        y = page.text("P", 10, y - 2, [sports_pass.type.name], 8)
        y = page.text(
            "P",
            10,
            y,
            [_("Válido ata o %(d)s") % {"d": sports_pass.expires_on.strftime("%d/%m/%Y")}],
            8,
        )
        until = sports_pass.expires_on
    else:
        y = page.text("P", 10, y - 2, [_("Sen abono activo")], 8)
        until = timezone.localdate() + timezone.timedelta(days=365)
    page.text("P", 10, 26, [_("N.º %(n)s") % {"n": card.display_number}], 8, True)
    page.text("P", 10, 15, [_("Emerxencias: 112")], 7)
    token = services.print_token(card, until)
    page.figure(
        qr_ops(token, CARD_W - 88, 12, 78),
        _("Código QR do carné número %(n)s") % {"n": card.display_number},
    )
    lang = "es-ES" if (get_language() or "gl").startswith("es") else "gl-ES"
    return _assemble(
        page,
        _("Carné municipal · %(c)s") % {"c": m.name},
        lang=lang,
        logo=logo,
        size=(CARD_W, CARD_H),
    )
