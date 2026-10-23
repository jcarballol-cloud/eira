# SPDX-License-Identifier: EUPL-1.2
"""v3: previsión da instalación para os consellos (sensación térmica, humidade) e MeteoSIX."""

import datetime as dt
from zoneinfo import ZoneInfo

from apps.integrations.weather import FakeWeatherAdapter, Forecast, MeteoSixAdapter

MADRID = ZoneInfo("Europe/Madrid")


def test_feels_like_heat_cold_and_mild():
    hot = Forecast(32, 10, 5, 8, "clear", humidity_pct=60)
    assert hot.feels_like_c >= 35  # índice de calor
    cold = Forecast(2, 30, 30, 0, "cloudy", humidity_pct=80)
    assert cold.feels_like_c <= -2  # sensación por vento
    mild = Forecast(18, 30, 10, 3, "cloudy", humidity_pct=70)
    assert mild.feels_like_c == 18


def test_fake_forecast_is_coherent_with_season_and_hour():
    w = FakeWeatherAdapter()
    lat, lon = 42.77, -7.89

    def at(month, hour):
        return dt.datetime(2026, month, 15, hour, 0, tzinfo=MADRID)

    summer_afternoon = w.forecast(lat, lon, at(7, 16))
    winter_morning = w.forecast(lat, lon, at(1, 8))
    assert summer_afternoon.temperature_c > winter_morning.temperature_c + 5
    assert summer_afternoon.uv_index > winter_morning.uv_index
    assert w.forecast(lat, lon, at(7, 23)).uv_index == 0  # de noite non hai UV
    for f in (summer_afternoon, winter_morning):
        assert 35 <= f.humidity_pct <= 98
    # determinista: mesma franxa, mesma previsión
    assert w.forecast(lat, lon, at(7, 16)) == summer_afternoon


def test_meteosix_parser_picks_nearest_instant():
    data = {
        "features": [
            {
                "properties": {
                    "days": [
                        {
                            "variables": [
                                {
                                    "name": "temperature",
                                    "units": "degc",
                                    "values": [
                                        {"timeInstant": "2026-07-15T16:00:00+02", "value": 24.6},
                                        {"timeInstant": "2026-07-15T17:00:00+02", "value": 26.1},
                                    ],
                                },
                                {
                                    "name": "relative_humidity",
                                    "units": "%",
                                    "values": [
                                        {"timeInstant": "2026-07-15T17:00:00+02", "value": 55},
                                    ],
                                },
                                {
                                    "name": "wind",
                                    "units": "kmh",
                                    "values": [
                                        {
                                            "timeInstant": "2026-07-15T17:00:00+02",
                                            "moduleValue": 12.0,
                                            "directionValue": 300,
                                        },
                                    ],
                                },
                                {
                                    "name": "precipitation_amount",
                                    "units": "lm2",
                                    "values": [
                                        {"timeInstant": "2026-07-15T17:00:00+02", "value": 0},
                                    ],
                                },
                                {
                                    "name": "sky_state",
                                    "units": "",
                                    "values": [
                                        {"timeInstant": "2026-07-15T17:00:00+02", "value": "SUNNY"},
                                    ],
                                },
                            ]
                        }
                    ]
                }
            }
        ]
    }
    f = MeteoSixAdapter.parse(data, dt.datetime(2026, 7, 15, 17, 10, tzinfo=MADRID))
    assert f.temperature_c == 26.1 and f.humidity_pct == 55 and f.wind_kmh == 12
    assert f.sky == "clear" and f.uv_index >= 3 and f.source == "MeteoSIX"
