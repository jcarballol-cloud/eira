# SPDX-License-Identifier: EUPL-1.2
"""Preferencias de accesibilidade (texto grande, alto contraste, movemento reducido).

Gárdanse nunha cookie sen datos persoais e aplícanse no servidor como clases no <html>,
polo que funcionan sen JavaScript.
"""

COOKIE = "eira_prefs"
KEYS = ("large_text", "high_contrast", "reduced_motion")


def read_prefs(request):
    raw = request.COOKIES.get(COOKIE, "")
    active = {k for k in raw.split(".") if k in KEYS}
    return {k: (k in active) for k in KEYS} | {
        "classes": " ".join(f"pref-{k.replace('_', '-')}" for k in sorted(active))
    }


def write_prefs(response, values):
    active = [k for k in KEYS if values.get(k)]
    response.set_cookie(
        COOKIE, ".".join(active), max_age=60 * 60 * 24 * 365, samesite="Lax", httponly=True
    )
    return response
