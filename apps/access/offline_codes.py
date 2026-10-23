# SPDX-License-Identifier: EUPL-1.2
"""Códigos de acceso temporais sen conexión (nivel 2).

Esquema (documentado en docs/access/offline-codes.md):

    bloque  b = floor(unix_inicio / (S·60))        S = minutos por bloque (p. ex. 30)
    duración d = número de bloques da reserva       1 ≤ d ≤ D_MAX (≤ 15)
    contador C = b·16 + d
    código   = HOTP(K, C)  (RFC 4226, HMAC-SHA1, 6 díxitos)

A pechadura comparte K coa plataforma e ten reloxo propio. Para validar un código á hora t
con tolerancia T, proba todos os pares (b, d) cuxa xanela [b·S − T, (b+d)·S + T] contén t.
Así o código só abre durante a franxa reservada (± T) sen que a pechadura necesite rede.

Este módulo é puro (sen Django) para que o mesmo código se poida levar ao firmware.
"""

import hmac
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pyotp

DURATION_BITS = 4
MAX_DURATION_BLOCKS = 2**DURATION_BITS - 1  # 15


@dataclass(frozen=True)
class CodeParams:
    secret: str  # base32
    step_minutes: int = 30
    tolerance_minutes: int = 10
    digits: int = 6
    max_blocks: int = 8

    def __post_init__(self):
        if not 1 <= self.max_blocks <= MAX_DURATION_BLOCKS:
            raise ValueError("max_blocks fóra de rango")
        if self.step_minutes <= 0 or self.tolerance_minutes < 0:
            raise ValueError("parámetros de tempo non válidos")


@dataclass(frozen=True)
class Match:
    block: int
    duration_blocks: int
    window_start: datetime
    window_end: datetime


def _ts(dt):
    if dt.tzinfo is None:
        raise ValueError("Requírese unha data con fuso horario")
    return dt.timestamp()


def counter_for(start, end, params):
    """Contador HOTP dunha reserva. A reserva debe estar aliñada aos bloques."""
    step = params.step_minutes * 60
    start_ts, end_ts = _ts(start), _ts(end)
    if start_ts % step or end_ts % step:
        raise ValueError("A reserva non está aliñada aos bloques do código")
    block = int(start_ts // step)
    duration = int((end_ts - start_ts) // step)
    if not 1 <= duration <= params.max_blocks:
        raise ValueError("Duración non soportada polo esquema de códigos")
    return (block << DURATION_BITS) | duration


def code_for(start, end, params):
    return pyotp.HOTP(params.secret, digits=params.digits).at(counter_for(start, end, params))


def window_for(start, end, params):
    tol = timedelta(minutes=params.tolerance_minutes)
    return start - tol, end + tol


def validate(code, at, params):
    """Valida `code` á hora `at` do reloxo da pechadura. Devolve un Match ou None."""
    code = (code or "").strip().replace(" ", "")
    if len(code) != params.digits or not code.isdigit():
        return None
    step = params.step_minutes * 60
    tol = params.tolerance_minutes * 60
    t = _ts(at)
    hotp = pyotp.HOTP(params.secret, digits=params.digits)
    found = None
    for d in range(1, params.max_blocks + 1):
        # b·step − tol ≤ t ≤ (b+d)·step + tol
        b_min = math.ceil((t - tol) / step) - d
        b_max = math.floor((t + tol) / step)
        for b in range(b_min, b_max + 1):
            if not (b * step - tol <= t <= (b + d) * step + tol):
                continue
            # Compárase sempre en tempo constante e sen saír antes (non filtra información de tempo).
            if hmac.compare_digest(hotp.at((b << DURATION_BITS) | d), code) and found is None:
                found = Match(
                    block=b,
                    duration_blocks=d,
                    window_start=datetime.fromtimestamp(b * step - tol, tz=UTC),
                    window_end=datetime.fromtimestamp((b + d) * step + tol, tz=UTC),
                )
    return found


def candidate_count(params):
    """Número de códigos que a pechadura acepta nun instante (para analizar a forza bruta)."""
    step, tol = params.step_minutes, params.tolerance_minutes
    t = 0.5  # instante xenérico non aliñado
    total = 0
    for d in range(1, params.max_blocks + 1):
        b_min = math.ceil((t - tol) / step) - d
        b_max = math.floor((t + tol) / step)
        total += sum(
            1 for b in range(b_min, b_max + 1) if b * step - tol <= t <= (b + d) * step + tol
        )
    return total
