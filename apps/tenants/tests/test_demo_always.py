# SPDX-License-Identifier: EUPL-1.2
"""v1.5.1: os exemplos da demo existen sempre, sexa cal sexa a data e a hora do seed.

A lista está en apps/tenants/demo_checks.py. Inclúe as datas nas que faltaban (venres pola noite) e
casos límite. Cada seed tarda uns 2 min con PostgreSQL, así que aquí só van 4 momentos."""

import datetime as dt
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.tenants.demo_checks import missing

pytestmark = pytest.mark.django_db
MADRID = ZoneInfo("Europe/Madrid")
REAL_NOW = timezone.now


def at(value):
    """Reloxo fixado na hora local indicada, que segue avanzando durante a proba."""
    fixed = dt.datetime.fromisoformat(value).replace(tzinfo=MADRID)
    offset = fixed - REAL_NOW()
    return mock.patch("django.utils.timezone.now", side_effect=lambda: REAL_NOW() + offset)


@pytest.mark.parametrize(
    "moment",
    [
        "2026-11-06T21:00",  # venres: faltaban a lista de espera e a franxa liberada
        "2026-11-07T00:30",  # sábado de madrugada
        "2026-10-25T02:30",  # cambio de hora
        "2026-12-31T23:50",  # fin de ano, cruzando a medianoite
    ],
)
def test_examples_exist_at_any_moment(moment):
    with at(moment):
        call_command("seed_demo", verbosity=0)
        assert timezone.localtime().date() == dt.date.fromisoformat(moment[:10])
        assert missing() == []


def test_clock_helper_also_moves_localdate():
    with at("2026-11-07T00:30"):
        assert timezone.localdate() == dt.date(2026, 11, 7)
