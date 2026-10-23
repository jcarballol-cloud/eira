# SPDX-License-Identifier: EUPL-1.2
"""Bordes da xanela dos códigos sen conexión (nivel 2)."""

import datetime as dt
import random

import pyotp
import pytest

from apps.access import offline_codes as oc

UTC = dt.UTC
SECRET = pyotp.random_base32()
P = oc.CodeParams(secret=SECRET, step_minutes=30, tolerance_minutes=10, digits=6, max_blocks=8)
START = dt.datetime(2026, 11, 18, 18, 0, tzinfo=UTC)
END = dt.datetime(2026, 11, 18, 19, 30, tzinfo=UTC)
CODE = oc.code_for(START, END, P)
S = dt.timedelta(seconds=1)
TOL = dt.timedelta(minutes=10)


@pytest.mark.parametrize("at, ok", [
    (START - TOL - S, False),          # 1 segundo antes da tolerancia
    (START - TOL, True),               # bordo exacto da tolerancia inicial
    (START - dt.timedelta(minutes=5), True),
    (START, True),
    (START + dt.timedelta(minutes=45), True),
    (END, True),
    (END + TOL, True),                 # bordo exacto da tolerancia final
    (END + TOL + S, False),            # 1 segundo despois
    (START - dt.timedelta(hours=1), False),
    (END + dt.timedelta(hours=1), False),
    (START + dt.timedelta(days=1), False),  # mesma hora ao día seguinte
    (START - dt.timedelta(days=7), False),  # mesma hora a semana anterior
])
def test_window_edges(at, ok):
    assert (oc.validate(CODE, at, P) is not None) is ok


def test_match_reports_slot():
    m = oc.validate(CODE, START + dt.timedelta(minutes=1), P)
    assert m.duration_blocks == 3
    assert m.window_start == START - TOL and m.window_end == END + TOL


def test_code_of_other_slot_is_rejected():
    other = oc.code_for(START + dt.timedelta(hours=2), END + dt.timedelta(hours=2), P)
    assert other != CODE
    assert oc.validate(other, START + dt.timedelta(minutes=10), P) is None


def test_duration_is_part_of_the_code():
    """Un código de 30 min non serve para os 90 min seguintes."""
    short = oc.code_for(START, START + dt.timedelta(minutes=30), P)
    assert oc.validate(short, START + dt.timedelta(minutes=20), P)
    assert oc.validate(short, START + dt.timedelta(minutes=41), P) is None  # 30 + 10 de tolerancia + 1


def test_other_secret_is_rejected():
    other = oc.CodeParams(secret=pyotp.random_base32())
    assert oc.validate(CODE, START, other) is None


@pytest.mark.parametrize("bad", ["", "12345", "1234567", "abcdef", None, "12 345"])
def test_malformed_codes(bad):
    assert oc.validate(bad, START, P) is None


def test_spaces_are_tolerated():
    assert oc.validate(f"{CODE[:3]} {CODE[3:]}", START, P)


def test_misaligned_booking_raises():
    with pytest.raises(ValueError):
        oc.code_for(START + dt.timedelta(minutes=15), END, P)


def test_too_long_booking_raises():
    with pytest.raises(ValueError):
        oc.code_for(START, START + dt.timedelta(hours=5), P)


def test_naive_datetime_raises():
    with pytest.raises(ValueError):
        oc.code_for(START.replace(tzinfo=None), END.replace(tzinfo=None), P)


def test_zero_tolerance():
    p = oc.CodeParams(secret=SECRET, tolerance_minutes=0)
    code = oc.code_for(START, END, p)
    assert oc.validate(code, START, p)
    assert oc.validate(code, START - S, p) is None
    assert oc.validate(code, END, p)
    assert oc.validate(code, END + S, p) is None


def test_invalid_params():
    with pytest.raises(ValueError):
        oc.CodeParams(secret=SECRET, max_blocks=16)
    with pytest.raises(ValueError):
        oc.CodeParams(secret=SECRET, step_minutes=0)


def test_candidate_count_is_bounded():
    # Con S=30, T=10 e ata 8 bloques, a pechadura acepta poucas decenas de códigos á vez.
    n = oc.candidate_count(P)
    assert 36 <= n <= 60


def test_random_bookings_property():
    """Propiedade: para reservas aleatorias, o código abre dentro da xanela e non fóra."""
    rng = random.Random(7)
    for _ in range(300):
        block = rng.randint(990_000, 1_100_000)  # anos 2026–2032
        dur = rng.randint(1, 8)
        start = dt.datetime.fromtimestamp(block * 1800, tz=UTC)
        end = start + dt.timedelta(minutes=30 * dur)
        code = oc.code_for(start, end, P)
        inside = start - TOL + dt.timedelta(seconds=rng.randint(0, int((end - start + 2 * TOL).total_seconds())))
        assert oc.validate(code, inside, P), (start, end, inside)
        outside = end + TOL + dt.timedelta(seconds=rng.randint(1, 86_400))
        match = oc.validate(code, outside, P)
        # Unha colisión casual con outro contador é posible pero improbable (≈5·10⁻⁵ por intento)
        assert match is None or (match.block, match.duration_blocks) != (block, dur)
