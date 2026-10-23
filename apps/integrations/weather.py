# SPDX-License-Identifier: EUPL-1.2
"""Meteoroloxía detrás dun adaptador.

- FakeWeatherAdapter: previsión plausible e determinista para Galicia (sen rede).
- MeteoSixAdapter: esqueleto para a API MeteoSIX de MeteoGalicia (require clave gratuíta).
"""

import hashlib
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

from django.conf import settings
from django.utils.timezone import localtime
from django.utils.translation import gettext as _


@dataclass
class Forecast:
    temperature_c: float
    precipitation_prob: int  # %
    wind_kmh: int
    uv_index: int
    sky: str  # "clear" | "cloudy" | "rain"
    source: str = "simulado"
    humidity_pct: int = 70

    @property
    def feels_like_c(self):
        """Sensación térmica: índice de calor (NOAA, Rothfusz) con calor e humidade; sensación
        por vento (Environment Canada / NWS 2001) con frío e vento; se non, a temperatura."""
        t, rh, v = self.temperature_c, self.humidity_pct, self.wind_kmh
        if t >= 27 and rh >= 40:
            f = t * 9 / 5 + 32
            hi = (
                -42.379
                + 2.04901523 * f
                + 10.14333127 * rh
                - 0.22475541 * f * rh
                - 6.83783e-3 * f * f
                - 5.481717e-2 * rh * rh
                + 1.22874e-3 * f * f * rh
                + 8.5282e-4 * f * rh * rh
                - 1.99e-6 * f * f * rh * rh
            )
            return round((hi - 32) * 5 / 9)
        if t <= 10 and v > 4.8:
            wc = 13.12 + 0.6215 * t - 11.37 * v**0.16 + 0.3965 * t * v**0.16
            return round(wc)
        return round(t)

    @property
    def sky_label(self):
        return {"clear": _("Despexado"), "cloudy": _("Nubrado"), "rain": _("Chuvia")}.get(
            self.sky, self.sky
        )


MONTHLY_MEAN_C = [9, 10, 12, 13, 15, 18, 20, 20, 19, 16, 12, 10]
MONTHLY_RAIN = [70, 65, 55, 55, 45, 30, 20, 20, 35, 60, 70, 75]
MONTHLY_UV_MAX = [1, 2, 3, 5, 6, 8, 8, 7, 5, 3, 1, 1]


class WeatherAdapter:
    def forecast(self, latitude, longitude, at):
        raise NotImplementedError


class FakeWeatherAdapter(WeatherAdapter):
    def forecast(self, latitude, longitude, at):
        at = localtime(at)
        seed = hashlib.sha256(f"{round(float(latitude or 0), 1)}:{at:%Y-%m-%d}".encode()).digest()
        noise = (seed[0] / 255 - 0.5) * 6
        month = at.month - 1
        hour = at.hour + at.minute / 60
        diurnal = 4 * max(-1.0, 1 - abs(hour - 15) / 9) if 6 <= hour <= 24 else -3
        temp = round(MONTHLY_MEAN_C[month] + diurnal + noise, 1)
        rain = max(0, min(100, MONTHLY_RAIN[month] + int((seed[1] / 255 - 0.5) * 60)))
        sky = "rain" if rain >= 65 else ("cloudy" if rain >= 35 else "clear")
        uv_peak = MONTHLY_UV_MAX[month] * (0.5 if sky != "clear" else 1)
        uv = int(round(max(0.0, uv_peak * (1 - abs(hour - 14) / 6)))) if 8 <= hour <= 20 else 0
        wind = 8 + seed[2] % 30
        # Humidade relativa: alta en Galicia, máis de noite e con chuvia; máis baixa á tarde no verán
        humidity = int(
            max(35, min(98, 78 + (rain - 50) * 0.25 - diurnal * 3 + (seed[3] / 255 - 0.5) * 12))
        )
        return Forecast(temp, rain, wind, uv, sky, humidity_pct=humidity)


class MeteoSixAdapter(WeatherAdapter):
    """Esqueleto do cliente MeteoSIX v5 (MeteoGalicia). Clave en EIRA_METEOSIX_API_KEY.

    Documentación: https://www.meteogalicia.gal/web/proxectos/meteosix
    Non se usa no prototipo; mantense a mesma interface que o adaptador simulado.
    """

    BASE = "https://servizos.meteogalicia.gal/apiv5/getNumericForecastInfo"
    VARIABLES = "temperature,relative_humidity,precipitation_amount,wind,sky_state"

    def forecast(self, latitude, longitude, at):
        if not settings.EIRA_METEOSIX_API_KEY:
            raise RuntimeError("Falta EIRA_METEOSIX_API_KEY")
        query = urllib.parse.urlencode(
            {
                "coords": f"{longitude},{latitude}",
                "variables": self.VARIABLES,
                "API_KEY": settings.EIRA_METEOSIX_API_KEY,
                "format": "application/json",
            }
        )
        with urllib.request.urlopen(f"{self.BASE}?{query}", timeout=5) as resp:  # noqa: S310
            return self.parse(json.load(resp), at)

    @staticmethod
    def parse(data, at):
        """Converte a resposta GeoJSON de MeteoSIX v5 nun Forecast para o instante `at`.

        Estrutura: features[0].properties.days[].variables[] con `name`, `units` e `values`
        (cada un con `timeInstant` e `value`, ou `moduleValue` no vento). O UV non vén en
        getNumericForecastInfo: estímase co mes e o estado do ceo, como no simulado."""
        from django.utils.dateparse import parse_datetime

        target = localtime(at)
        series = {}
        for day in data["features"][0]["properties"]["days"]:
            for var in day["variables"]:
                for item in var.get("values", []):
                    when = parse_datetime(item["timeInstant"])
                    value = item.get("value", item.get("moduleValue"))
                    if when is not None and value is not None:
                        series.setdefault(var["name"], []).append(
                            (abs((when - target).total_seconds()), value, var.get("units", ""))
                        )

        def nearest(name, default=None):
            rows = sorted(series.get(name, []), key=lambda r: r[0])
            return rows[0][1:] if rows else (default, "")

        temp, _u = nearest("temperature", 15)
        rh, _u = nearest("relative_humidity", 70)
        rain_mm, _u = nearest("precipitation_amount", 0)
        wind, wunits = nearest("wind", 0)
        sky, _u = nearest("sky_state", "CLOUDY")
        wind_kmh = float(wind) * 3.6 if wunits in ("ms", "m/s") else float(wind)
        sky_key = (
            "rain" if float(rain_mm or 0) >= 0.5 else ("clear" if sky == "SUNNY" else "cloudy")
        )
        uv_peak = MONTHLY_UV_MAX[target.month - 1] * (1 if sky_key == "clear" else 0.5)
        hour = target.hour + target.minute / 60
        uv = int(round(max(0.0, uv_peak * (1 - abs(hour - 14) / 6)))) if 8 <= hour <= 20 else 0
        return Forecast(
            temperature_c=round(float(temp), 1),
            precipitation_prob=min(100, int(float(rain_mm or 0) * 40)),
            wind_kmh=int(round(wind_kmh)),
            uv_index=uv,
            sky=sky_key,
            source="MeteoSIX",
            humidity_pct=int(float(rh)),
        )


def advice(forecast, indoor=False):
    """Consellos breves e prudentes segundo a previsión (orientativos)."""
    tips = []
    if forecast.temperature_c <= 8:
        tips.append(_("Fai frío: leva roupa de abrigo por capas e quenta ben antes de empezar."))
    if forecast.temperature_c >= 27:
        tips.append(_("Calor: bebe auga antes, durante e despois, e evita as horas centrais."))
    elif forecast.temperature_c >= 20:
        tips.append(_("Leva auga e bebe a miúdo, aínda que non teñas sede."))
    if not indoor and forecast.uv_index >= 6:
        tips.append(_("Índice UV alto: crema solar, gorra e sombra nos descansos."))
    elif not indoor and forecast.uv_index >= 3:
        tips.append(_("Índice UV moderado: usa protección solar."))
    if not indoor and forecast.precipitation_prob >= 60:
        tips.append(
            _("Probable chuvia: o pavimento pode esvarar. Considera unha instalación cuberta.")
        )
    if not indoor and forecast.wind_kmh >= 35:
        tips.append(_("Vento forte: coidado con redes, porterías e obxectos soltos."))
    if not tips:
        tips.append(_("Bo tempo para facer deporte. Hidrátate e disfruta."))
    return tips
