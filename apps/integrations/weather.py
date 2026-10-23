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
        return Forecast(temp, rain, wind, uv, sky)


class MeteoSixAdapter(WeatherAdapter):
    """Esqueleto do cliente MeteoSIX v5 (MeteoGalicia). Clave en EIRA_METEOSIX_API_KEY.

    Documentación: https://www.meteogalicia.gal/web/proxectos/meteosix
    Non se usa no prototipo; mantense a mesma interface que o adaptador simulado.
    """

    BASE = "https://servizos.meteogalicia.gal/apiv5/getNumericForecastInfo"

    def forecast(self, latitude, longitude, at):
        if not settings.EIRA_METEOSIX_API_KEY:
            raise RuntimeError("Falta EIRA_METEOSIX_API_KEY")
        query = urllib.parse.urlencode(
            {
                "coords": f"{longitude},{latitude}",
                "variables": "temperature,precipitation_amount,wind,sky_state",
                "API_KEY": settings.EIRA_METEOSIX_API_KEY,
                "format": "application/json",
            }
        )
        with urllib.request.urlopen(f"{self.BASE}?{query}", timeout=5) as resp:  # noqa: S310
            data = json.load(resp)
        raise NotImplementedError(f"Interpretar resposta MeteoSIX ({len(data)} claves)")


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
