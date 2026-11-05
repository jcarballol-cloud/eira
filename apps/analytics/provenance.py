# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · C: mapa de procedencia (mobilidade), sempre agregado.

A persoa indica a súa parroquia de residencia de forma voluntaria (ou sae do cruce co padrón no
alta, gardando só a parroquia). Para persoas doutros concellos úsase o seu concello. **Nunca GPS
nin ubicación do dispositivo.**

Salvagardas (ver docs/rxpd/matriz.md e a EIPD):
- `n` conta **persoas distintas**, non reservas: dez reservas dunha soa persoa non pasan o limiar.
- O limiar (`EIRA_MIN_AGGREGATION`, n ≥ 10) aplícase **despois de cada filtro**, nunca antes.
- O resto agrúpase en «outras procedencias» por destino e, se ese grupo tampouco chega ao limiar,
  móstrase sen cifra («menos de 10»). Nunca se publican totais por destino nin por orixe: permitirían
  deducir o suprimido por resta. Os «puntos quentes» só suman fluxos visibles.
- Só períodos pechados (non datas libres), para dificultar comparar dúas ventás case iguais.
"""

import csv
import datetime as dt
import io
import json
import math
from collections import defaultdict

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import Residency, User
from apps.bookings.models import Booking
from apps.facilities.models import Facility, FacilityKind, Parish
from apps.tenants.models import Municipality

PERIODS = (30, 90, 365)
DEFAULT_PERIOD = 90
COUNTED = (Booking.Status.USED, Booking.Status.CONFIRMED)
CSV_HEADER = ["orixe_tipo", "orixe", "destino", "persoas", "reservas"]


def threshold():
    return settings.EIRA_MIN_AGGREGATION


def clean_filters(data):
    """Só valores coñecidos: calquera outro volve ao predeterminado."""
    raw = str(data.get("periodo", ""))
    days = int(raw) if raw.isdigit() and int(raw) in PERIODS else DEFAULT_PERIOD
    kind = data.get("deporte", "")
    return {"days": days, "kind": kind if kind in FacilityKind.values else ""}


def _window(days, now=None):
    now = now or timezone.now()
    return now - dt.timedelta(days=days), now


def _home_municipalities(user_ids):
    """Concello polo empadroamento validado, para quen non indicou parroquia nin concello."""
    homes = {}
    rows = Residency.objects.filter(user_id__in=user_ids, revoked_at__isnull=True).values_list(
        "user_id", "municipality_id"
    )
    for user_id, municipality_id in rows:
        homes.setdefault(user_id, municipality_id)
    return homes


def _people(user_ids):
    """{persoa: (parroquia, concello)}. Sen datos de residencia, sen orixe (non conta)."""
    people = {}
    residency = _home_municipalities(user_ids)
    rows = User.objects.filter(pk__in=user_ids).values_list(
        "pk",
        "residence_parish_id",
        "residence_parish__municipality_id",
        "residence_municipality_id",
    )
    for pk, parish, parish_town, town in rows:
        people[pk] = (parish, parish_town or town or residency.get(pk))
    return people


def _bookings(municipalities, days, kind, now=None):
    start, end = _window(days, now)
    qs = Booking.objects.filter(
        municipality__in=municipalities,
        status__in=COUNTED,
        start__gte=start,
        start__lt=end,
        user__isnull=False,
    )
    if kind:
        qs = qs.filter(facility__kind=kind)
    return qs


def _apply_threshold(cells, k):
    """cells: {(orixe, destino): {"people": set, "bookings": int}}. Aquí, despois dos filtros."""
    visible, hidden = [], defaultdict(set)
    for (origin, destination), cell in cells.items():
        if len(cell["people"]) >= k:
            visible.append(
                {
                    "origin": origin,
                    "destination": destination,
                    "people": len(cell["people"]),
                    "bookings": cell["bookings"],
                }
            )
        else:
            hidden[destination] |= cell["people"]
    others = [
        {"destination": destination, "people": len(people) if len(people) >= k else None}
        for destination, people in hidden.items()
    ]
    visible.sort(key=lambda row: (-row["people"], str(row["origin"]), str(row["destination"])))
    return visible, others


# ------------------------------------------------------------------ concello
def _collect_town(municipality, days, kind, now=None):
    rows = list(_bookings([municipality], days, kind, now).values_list("user_id", "facility_id"))
    people = _people({user_id for user_id, _f in rows})
    cells = defaultdict(lambda: {"people": set(), "bookings": 0})
    for user_id, facility_id in rows:
        parish, town = people.get(user_id, (None, None))
        if town is None:
            continue
        if town == municipality.pk:
            if parish is None:
                continue  # veciña sen parroquia indicada: non consta a orixe
            origin = ("parish", parish)
        else:
            origin = ("municipality", town)
        cell = cells[(origin, facility_id)]
        cell["people"].add(user_id)
        cell["bookings"] += 1
    return cells


def town_flows(municipality, days=DEFAULT_PERIOD, kind="", now=None, k=None):
    """Fluxos parroquia → instalación e concello → instalación, co limiar xa aplicado."""
    visible, others = _apply_threshold(
        _collect_town(municipality, days, kind, now), k or threshold()
    )
    parishes = {p.pk: p for p in Parish.objects.filter(municipality=municipality)}
    towns = {m.pk: m for m in Municipality.objects.all()}
    facilities = {f.pk: f for f in Facility.objects.for_tenant(municipality)}
    rows = []
    for row in visible:
        kind_key, pk = row["origin"]
        origin = parishes.get(pk) if kind_key == "parish" else towns.get(pk)
        destination = facilities.get(row["destination"])
        if origin is None or destination is None:
            continue
        rows.append(
            {
                "origin_kind": kind_key,
                "origin": origin,
                "origin_name": origin.name,
                "destination": destination,
                "destination_name": destination.name,
                "people": row["people"],
                "bookings": row["bookings"],
            }
        )
    other_rows = [
        {
            "destination_name": facilities[o["destination"]].name,
            "destination": facilities[o["destination"]],
            "people": o["people"],
        }
        for o in others
        if o["destination"] in facilities
    ]
    other_rows.sort(key=lambda o: (o["people"] is None, -(o["people"] or 0), o["destination_name"]))
    return {"rows": rows, "others": other_rows}


# ------------------------------------------------------------------ deputación
def _collect_region(region, days, kind, now=None):
    towns = {m.pk: m for m in region.municipalities.filter(is_active=True)}
    rows = list(_bookings(list(towns), days, kind, now).values_list("user_id", "municipality_id"))
    people = _people({user_id for user_id, _m in rows})
    cells = defaultdict(lambda: {"people": set(), "bookings": 0})
    for user_id, destination in rows:
        _parish, town = people.get(user_id, (None, None))
        if town is None or town == destination:
            continue
        # Fóra da rede non se identifica o concello: vai a «outras procedencias»
        origin = town if town in towns else "outside"
        cell = cells[(origin, destination)]
        cell["people"].add(user_id)
        cell["bookings"] += 1
    return cells, towns


def region_flows(region, days=DEFAULT_PERIOD, kind="", now=None, k=None):
    """Fluxos entre concellos da rede, sempre agregados, e puntos quentes."""
    k = k or threshold()
    cells, towns = _collect_region(region, days, kind, now)
    # «Fóra da rede» nunca se publica como fluxo, aínda que chegue ao limiar
    outside = {key: cell for key, cell in cells.items() if key[0] == "outside"}
    visible, others = _apply_threshold(
        {key: cell for key, cell in cells.items() if key[0] != "outside"}, k
    )
    merged = {o["destination"]: o["people"] for o in others}
    for (_origin, destination), cell in outside.items():
        known = merged.get(destination)
        merged[destination] = (known or 0) + len(cell["people"])
        if merged[destination] < k:
            merged[destination] = None
    rows = [
        {
            "origin": towns[row["origin"]],
            "origin_name": towns[row["origin"]].name,
            "destination": towns[row["destination"]],
            "destination_name": towns[row["destination"]].name,
            "people": row["people"],
            "bookings": row["bookings"],
        }
        for row in visible
    ]
    other_rows = [
        {"destination_name": towns[pk].name, "destination": towns[pk], "people": people}
        for pk, people in merged.items()
    ]
    other_rows.sort(key=lambda o: o["destination_name"])
    inbound = defaultdict(int)
    for row in rows:
        inbound[row["destination_name"]] += row["people"]  # só fluxos visibles: sen restas posibles
    hot = sorted(inbound.items(), key=lambda item: (-item[1], item[0]))
    return {
        "rows": rows,
        "others": other_rows,
        "hotspots": [{"name": name, "people": people} for name, people in hot],
    }


# ------------------------------------------------------------------ exportación agregada
def _others_label():
    return _("outras procedencias")


def csv_text(flows):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(CSV_HEADER)
    for row in flows["rows"]:
        writer.writerow(
            [
                row.get("origin_kind", "municipality"),
                row["origin_name"],
                row["destination_name"],
                row["people"],
                row["bookings"],
            ]
        )
    for other in flows["others"]:
        writer.writerow(
            [
                "others",
                _others_label(),
                other["destination_name"],
                other["people"] if other["people"] is not None else f"<{threshold()}",
                "",
            ]
        )
    return out.getvalue()


def position(obj):
    """(lat, lon) dunha parroquia, instalación ou concello. Para concellos sen posición, a media
    das súas instalacións."""
    lat, lon = getattr(obj, "latitude", None), getattr(obj, "longitude", None)
    if lat is not None and lon is not None:
        return float(lat), float(lon)
    if isinstance(obj, Municipality):
        points = [
            (float(a), float(b))
            for a, b in Facility.objects.for_tenant(obj)
            .exclude(latitude=None)
            .exclude(longitude=None)
            .values_list("latitude", "longitude")
        ]
        if points:
            return sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)
    return None


def geojson_text(flows):
    features = []
    for row in flows["rows"]:
        a, b = position(row["origin"]), position(row["destination"])
        if not (a and b):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[a[1], a[0]], [b[1], b[0]]]},
                "properties": {
                    "origin": row["origin_name"],
                    "destination": row["destination_name"],
                    "people": row["people"],
                    "bookings": row["bookings"],
                },
            }
        )
    return json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False)


# ------------------------------------------------------------------ mapa (SVG do servidor)
W, H, PAD = 640, 460, 54


def _projector(points, w=W, h=H, pad=PAD):
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    mid = math.cos(math.radians(sum(lats) / len(lats)))
    span_x = max((max(lons) - min(lons)) * mid, 1e-6)
    span_y = max(max(lats) - min(lats), 1e-6)
    scale = min((w - 2 * pad) / span_x, (h - 2 * pad) / span_y)
    off_x = (w - span_x * scale) / 2
    off_y = (h - span_y * scale) / 2

    def project(lat, lon):
        return (
            round(off_x + (lon - min(lons)) * mid * scale, 1),
            round(h - off_y - (lat - min(lats)) * scale, 1),
        )

    return project


def _curve(a, b, bend=0.12):
    """Curva para que A→B e B→A non se pisen. O extremo queda antes do símbolo de destino."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1
    cx = (a[0] + b[0]) / 2 - dy * bend
    cy = (a[1] + b[1]) / 2 + dx * bend
    gap = min(16, length / 3)
    ex = b[0] - (b[0] - cx) / (math.hypot(b[0] - cx, b[1] - cy) or 1) * gap
    ey = b[1] - (b[1] - cy) / (math.hypot(b[0] - cx, b[1] - cy) or 1) * gap
    return f"M{a[0]} {a[1]} Q{round(cx, 1)} {round(cy, 1)} {round(ex, 1)} {round(ey, 1)}"


def _pull_far_nodes(nodes):
    """Un concello afastado aplastaría o mapa: colócase na súa dirección real, fóra de escala.
    Devolve True se moveu algún. O nome leva a distancia para que non engane."""
    near = [n["pos"] for n in nodes if n.get("pos") and n["kind"] != "municipality"]
    far = [n for n in nodes if n.get("pos") and n["kind"] == "municipality"]
    if not near or not far:
        return False
    lat0 = sum(p[0] for p in near) / len(near)
    lon0 = sum(p[1] for p in near) / len(near)
    radius = max(max(distance_km((lat0, lon0), p) for p in near), 1.0)
    moved = False
    for node in far:
        km = distance_km((lat0, lon0), node["pos"])
        if km <= radius * 1.5:
            continue
        ratio = radius * 1.35 / km
        node["pos"] = (
            lat0 + (node["pos"][0] - lat0) * ratio,
            lon0 + (node["pos"][1] - lon0) * ratio,
        )
        node["name"] = _("%(n)s (%(d)s km)") % {"n": node["name"], "d": round(km)}
        moved = True
    return moved


def build_map(flows, nodes, w=W, h=H, pad=PAD):
    """Datos do SVG. nodes: [{"key", "name", "kind", "pos", "number"?}] con posición coñecida.
    A táboa é a alternativa accesible: o mapa é un complemento."""
    placed = [n for n in nodes if n.get("pos")]
    if not placed:
        return None
    project = _projector([n["pos"] for n in placed], w, h, pad)
    out_nodes = []
    by_key = {}
    for node in placed:
        x, y = project(*node["pos"])
        item = {
            **node,
            "x": x,
            "y": y,
            "label_x": x,
            "label_y": round(y - 15, 1) if y > 40 else round(y + 28, 1),
        }
        by_key[node["key"]] = item
        out_nodes.append(item)
    top = max((row["people"] for row in flows["rows"]), default=1)
    lines = []
    for row in flows["rows"]:
        a = by_key.get(row["origin_key"])
        b = by_key.get(row["destination_key"])
        if not (a and b):
            continue
        lines.append(
            {
                "d": _curve((a["x"], a["y"]), (b["x"], b["y"])),
                "width": round(1.5 + 6.5 * row["people"] / top, 1),
                "title": _("%(a)s → %(b)s: %(n)s persoas")
                % {"a": row["origin_name"], "b": row["destination_name"], "n": row["people"]},
            }
        )
    return {"w": w, "h": h, "nodes": out_nodes, "lines": lines}


def town_map(municipality, flows):
    """A rede do concello: as súas instalacións e parroquias e os concellos da rede."""
    from apps.tenants.network import network_of

    for row in flows["rows"]:
        row["origin_key"] = f"{row['origin_kind']}-{row['origin'].pk}"
        row["destination_key"] = f"facility-{row['destination'].pk}"
    nodes = []
    for parish in Parish.objects.filter(municipality=municipality):
        nodes.append(
            {
                "key": f"parish-{parish.pk}",
                "name": parish.name,
                "kind": "parish",
                "pos": position(parish),
            }
        )
    for town in network_of(municipality):
        nodes.append(
            {
                "key": f"municipality-{town.pk}",
                "name": town.name,
                "kind": "municipality",
                "pos": position(town),
            }
        )
    facilities = list(Facility.objects.for_tenant(municipality).filter(is_published=True))
    for number, facility in enumerate(facilities, start=1):
        facility.map_number = number
        nodes.append(
            {
                "key": f"facility-{facility.pk}",
                "name": facility.name,
                "kind": "facility",
                "number": number,
                "pos": position(facility),
            }
        )
    out_of_scale = _pull_far_nodes(nodes)
    map_data = build_map(flows, nodes)
    if map_data:
        map_data["out_of_scale"] = out_of_scale
    return map_data, facilities


def region_map(region, flows):
    for row in flows["rows"]:
        row["origin_key"] = f"municipality-{row['origin'].pk}"
        row["destination_key"] = f"municipality-{row['destination'].pk}"
    nodes = [
        {
            "key": f"municipality-{town.pk}",
            "name": town.name,
            "kind": "municipality",
            "pos": position(town),
        }
        for town in region.municipalities.filter(is_active=True)
    ]
    return build_map(flows, nodes)


# ------------------------------------------------------------------ a persoa: onde está e distancias
def distance_km(a, b):
    """Distancia en liña recta (haversine) entre (lat, lon)."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(h))


def nearby_for(user, home):
    """Distancias desde a parroquia (ou o concello) que a persoa indicou. Nunca desde o GPS."""
    from apps.tenants.network import network_of

    place = user.residence_parish or user.residence_municipality
    if place is None:
        return None
    origin = position(place)
    if origin is None:
        return {"place": place, "rows": [], "map": None}
    towns = [home, *network_of(home)]
    rows = []
    for facility in (
        Facility.objects.filter(municipality__in=towns, is_published=True)
        .exclude(latitude=None)
        .exclude(longitude=None)
        .select_related("municipality")
    ):
        rows.append(
            {
                "facility": facility,
                "km": round(distance_km(origin, position(facility)), 1),
            }
        )
    rows.sort(key=lambda row: (row["km"], row["facility"].name))
    rows = rows[:10]
    # No mapa, só as do concello (ou a máis próxima): as lonxanas van na lista, coa súa distancia
    nodes = [{"key": "me", "name": place.name, "kind": "me", "pos": origin}]
    limit = max(rows[0]["km"] * 3, 15) if rows else 0
    for number, row in enumerate(rows, start=1):
        row["number"] = number
        if row["km"] > limit:
            continue
        nodes.append(
            {
                "key": f"facility-{row['facility'].pk}",
                "name": row["facility"].name,
                "kind": "facility",
                "number": number,
                "pos": position(row["facility"]),
            }
        )
    return {
        "place": place,
        "rows": rows,
        "map": build_map({"rows": []}, nodes, w=420, h=320, pad=34),
    }
