# SPDX-License-Identifier: EUPL-1.2
"""v5 · Suplemento de iluminación.

Unha franxa precisa luz se algunha parte dela cae fóra das horas de luz natural:
- regra «solpor» (por defecto): antes do amencer ou despois do solpor, calculados para as
  coordenadas da instalación (algoritmo da NOAA, sen dependencias nin rede);
- regra «horario fixo»: desde `lighting_from` ata `lighting_until` do día seguinte.

A persoa tamén pode marcar «necesito luz» (pavillón escuro, días de néboa…).
"""

import datetime as dt
import math

from django.utils import timezone

# Coordenadas por defecto (centro de Galicia) se a instalación non as ten
DEFAULT_LAT, DEFAULT_LON = 42.75, -7.9


def _sun_utc(day, lat, lon, rising):
    """Hora UTC do amencer (`rising`) ou do solpor para un día e lugar. None se non hai."""
    n = day.timetuple().tm_yday
    lng_hour = lon / 15
    t = n + ((6 if rising else 18) - lng_hour) / 24
    m = 0.9856 * t - 3.289
    sun_lon = (
        m + 1.916 * math.sin(math.radians(m)) + 0.020 * math.sin(math.radians(2 * m)) + 282.634
    ) % 360
    ra = math.degrees(math.atan(0.91764 * math.tan(math.radians(sun_lon)))) % 360
    ra = (ra + (math.floor(sun_lon / 90) * 90 - math.floor(ra / 90) * 90)) / 15
    sin_dec = 0.39782 * math.sin(math.radians(sun_lon))
    cos_dec = math.cos(math.asin(sin_dec))
    zenith = math.radians(90.833)  # solpor oficial (refracción e disco solar)
    cos_h = (math.cos(zenith) - sin_dec * math.sin(math.radians(lat))) / (
        cos_dec * math.cos(math.radians(lat))
    )
    if not -1 <= cos_h <= 1:
        return None
    h = (360 - math.degrees(math.acos(cos_h))) if rising else math.degrees(math.acos(cos_h))
    local_mean = h / 15 + ra - 0.06571 * t - 6.622
    hours = (local_mean - lng_hour) % 24
    base = dt.datetime.combine(day, dt.time.min, tzinfo=dt.UTC)
    return base + dt.timedelta(hours=hours)


def sun_times(day, lat=DEFAULT_LAT, lon=DEFAULT_LON):
    """(amencer, solpor) en hora local para un día."""
    rise = _sun_utc(day, float(lat), float(lon), True)
    sset = _sun_utc(day, float(lat), float(lon), False)
    return (
        timezone.localtime(rise) if rise else None,
        timezone.localtime(sset) if sset else None,
    )


def dark_intervals(facility, day):
    """Intervalos (aware) dun día en que se precisa luz segundo a regra do concello."""
    m = facility.municipality
    tz = timezone.get_current_timezone()
    start_of_day = timezone.make_aware(dt.datetime.combine(day, dt.time.min), tz)
    end_of_day = start_of_day + dt.timedelta(days=1)
    if m.lighting_rule == "fixed":
        until = timezone.make_aware(dt.datetime.combine(day, m.lighting_until), tz)
        since = timezone.make_aware(dt.datetime.combine(day, m.lighting_from), tz)
        return [(start_of_day, until), (since, end_of_day)]
    lat = facility.latitude if facility.latitude is not None else DEFAULT_LAT
    lon = facility.longitude if facility.longitude is not None else DEFAULT_LON
    rise, sset = sun_times(day, lat, lon)
    if rise is None or sset is None:
        return []
    return [(start_of_day, rise), (sset, end_of_day)]


def slot_needs_light(facility, start, end):
    """A franxa cae (en parte) nas horas sen luz natural?"""
    if not facility.lighting:
        return False
    day = timezone.localdate(start)
    return any(a < end and b > start for a, b in dark_intervals(facility, day))


def lighting_supplement(facility, start, end, requested=False):
    """Suplemento (céntimos) e se se aplica. Só nas instalacións con luz e suplemento definido."""
    cents = facility.lighting_supplement_cents
    if not (facility.lighting and cents):
        return 0, False
    automatic = slot_needs_light(facility, start, end)
    return (cents, automatic) if (automatic or requested) else (0, False)
