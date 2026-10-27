# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · C: desfibriladores (DESA) próximos detrás dun adaptador.

A implementación por defecto le un CSV (pensada para un rexistro oficial con datos abertos, se
existe na comunidade autónoma). Non se integra ningunha app concreta (p. ex. ARIANA RCP) sen
verificar antes os seus datos e a súa licenza: ver docs/DECISIONS.md («non verificado»)."""

import csv
import math
from pathlib import Path

from django.conf import settings

DEMO_CSV = Path(__file__).resolve().parent / "data" / "desa_demo.csv"


def distance_m(lat1, lon1, lat2, lon2):
    """Distancia aproximada (haversine) en metros."""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return int(round(2 * r * math.asin(math.sqrt(a))))


class DefibrillatorAdapter:
    def nearest(self, latitude, longitude, limit=1):
        """Lista de {name, address, hours, latitude, longitude, distance_m}, a máis próxima primeiro."""
        raise NotImplementedError


class CsvDefibrillatorAdapter(DefibrillatorAdapter):
    """Le un CSV (name, address, latitude, longitude, hours). Por defecto, o da demo (ficticio)."""

    def __init__(self, path=None):
        self.path = Path(path or getattr(settings, "EIRA_DESA_CSV", "") or DEMO_CSV)

    def rows(self):
        with self.path.open(encoding="utf-8") as fh:
            lines = [line for line in fh if not line.startswith("#")]
        for row in csv.DictReader(lines):
            try:
                yield {
                    "name": row["name"].strip(),
                    "address": row["address"].strip(),
                    "hours": (row.get("hours") or "").strip(),
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                }
            except (KeyError, TypeError, ValueError):
                continue

    def nearest(self, latitude, longitude, limit=1):
        if latitude is None or longitude is None:
            return []
        lat, lon = float(latitude), float(longitude)
        found = [
            {**r, "distance_m": distance_m(lat, lon, r["latitude"], r["longitude"])}
            for r in self.rows()
        ]
        return sorted(found, key=lambda r: r["distance_m"])[:limit]
