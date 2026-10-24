# SPDX-License-Identifier: EUPL-1.2
"""v4: o ancho das barras respecta a escala (porcentaxes 0–100, satisfacción 0–100, absolutos ao máximo)."""

import pytest
from django.template import Context, Template

from apps.analytics.indicators import hbar
from apps.tenants.templatetags.eira import bucket5, signed


def widths(chart):
    return [round(b["pct"]) for b in chart["bars"]]


def test_percentages_are_scaled_0_to_100_not_to_the_max():
    # antes: 23 % enchía a barra enteira e 12 % quedaba na metade
    chart = hbar([{"l": "A", "v": 12}, {"l": "B", "v": 23}], "v", "l", suffix=" %", scale="percent")
    assert widths(chart) == [12, 23]
    assert [bucket5(b["pct"]) for b in chart["bars"]] == [10, 25]
    assert chart["scale"] == "percent" and chart["top_display"] == "100 %"


def test_percentages_over_100_are_capped():
    assert widths(hbar([{"l": "A", "v": 130}], "v", "l", scale="percent")) == [100]


def test_satisfaction_uses_fixed_0_100_scale():
    chart = hbar([{"l": "A", "v": 85}, {"l": "B", "v": 84}], "v", "l", suffix="/100", maximum=100)
    assert widths(chart) == [85, 84]
    assert chart["scale"] == "fixed" and chart["top_display"] == "100"


def test_absolute_values_are_relative_to_series_max_and_say_so():
    chart = hbar([{"l": "A", "v": 112.3}, {"l": "B", "v": 606.5}], "v", "l")
    assert widths(chart) == [19, 100]
    assert chart["scale"] == "max"
    html = Template('{% include "includes/hbar.html" with chart=chart cid="x" title="t" %}').render(
        Context({"chart": chart})
    )
    assert "Barras relativas ao valor máis alto" in html and "606" in html


def test_empty_and_negative_values():
    assert hbar([], "v", "l")["bars"] == []
    assert widths(hbar([{"l": "A", "v": -5}, {"l": "B", "v": 10}], "v", "l")) == [0, 100]


@pytest.mark.parametrize("value, expected", [(37, "+37"), (-42, "−42"), (0, "0"), (None, "")])
def test_signed_delta_format(value, expected):
    assert signed(value) == expected


def test_signed_uses_locale_decimals(settings):
    from django.utils import translation

    with translation.override("gl"):
        assert signed(-2.9) == "−2,9"
