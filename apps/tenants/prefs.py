# SPDX-License-Identifier: EUPL-1.2
"""Preferencias de accesibilidade (texto grande, alto contraste, movemento reducido).

Gárdanse nunha cookie sen datos persoais e aplícanse no servidor como clases no <html>,
polo que funcionan sen JavaScript.
"""

COOKIE = "eira_prefs"
KEYS = ("large_text", "high_contrast", "reduced_motion")
# v4.1: tema escollido co botón «Día / Noite» da demo («light» | «dark»), gardado na sesión.
# Sen valor, segue a preferencia do sistema.
THEME_KEY = "eira_theme"


def read_prefs(request):
    raw = request.COOKIES.get(COOKIE, "")
    active = {k for k in raw.split(".") if k in KEYS}
    session = getattr(request, "session", None)
    theme = session.get(THEME_KEY, "") if session is not None else ""
    return {k: (k in active) for k in KEYS} | {
        "classes": " ".join(f"pref-{k.replace('_', '-')}" for k in sorted(active)),
        "theme": theme if theme in ("light", "dark") else "",
    }


def write_prefs(response, values):
    active = [k for k in KEYS if values.get(k)]
    response.set_cookie(
        COOKIE, ".".join(active), max_age=60 * 60 * 24 * 365, samesite="Lax", httponly=True
    )
    return response
