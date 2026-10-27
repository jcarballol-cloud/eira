# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · C: ficha ampliada (accesibilidade detallada, sostibilidade e DESA), busca, adaptador
de desfibriladores, índice de vida activa e revisión de seguridade inicial."""

import pytest

from apps.analytics.vitality import _accessibility
from apps.facilities.models import Facility
from apps.integrations.defibrillators import CsvDefibrillatorAdapter, distance_m
from apps.integrations.registry import get_adapter
from apps.maintenance.safety import SAFETY_CHECKLIST

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


def _edit_data(client, facility):
    url = f"{C}/xestion/instalacions/{facility.pk}/"
    data = {k: v for k, v in client.get(url).context["form"].initial.items() if v is not None}
    data["parish"] = facility.parish_id or ""
    data.pop("photo", None)
    return url, {k: v for k, v in data.items() if v is not False}


def test_detailed_accessibility_fills_basic_list(client, admin_a, hall_a):
    client.force_login(admin_a)
    url, data = _edit_data(client, hall_a)
    data.update(
        {
            "acc_route": "yes",
            "acc_widths": "yes",
            "acc_toilets": "partial",
            "accnote_toilets": "Só no andar baixo",
            "acc_pmr_parking": "no",
            "bike_parking_spaces": 8,
            "ev_chargers": 2,
            "ev_charger_type": "Tipo 2, 7 kW",
            "transit_stop": "Bus liña 2 (200 m)",
            "aed_on_site": "true",
            "aed_inside_location": "Conserxaría",
            "aed_hours": "Mentres está aberta",
        }
    )
    r = client.post(url, data)
    assert r.status_code == 302, r.context["form"].errors
    hall_a.refresh_from_db()
    assert hall_a.accessibility_detail["toilets"] == {
        "value": "partial",
        "note": "Só no andar baixo",
    }
    # A lista básica enchese soa: só «si» conta como si
    assert hall_a.step_free is True
    assert hall_a.adapted_toilet is False and hall_a.accessible_parking is False
    assert hall_a.is_accessible and hall_a.bike_parking_spaces == 8 and hall_a.aed_on_site is True
    html = client.get(f"{C}/instalacions/{hall_a.pk}/").content.decode()
    for text in (
        "Accesibilidade detallada",
        "Itinerario accesible desde o exterior",
        "Só no andar baixo",
        "Parcial",
        "Mobilidade sostible",
        "8 prazas",
        "Tipo 2, 7 kW",
        "Bus liña 2 (200 m)",
        "DESA (desfibrilador)",
        "Conserxaría",
    ):
        assert text in html, text
    # A lista básica segue visible
    assert "Accesibilidade física" in html


def test_old_forms_without_detail_keep_it(client, admin_a, hall_a):
    hall_a.accessibility_detail = {"route": {"value": "yes", "note": ""}}
    hall_a.save()
    client.force_login(admin_a)
    url, data = _edit_data(client, hall_a)
    data = {k: v for k, v in data.items() if not k.startswith("acc")}
    client.post(url, data)
    hall_a.refresh_from_db()
    assert hall_a.accessibility_detail == {"route": {"value": "yes", "note": ""}}


def test_search_filters_accessible_bikes_aed(client, hall_a, padel_a, gym_a):
    Facility.objects.filter(pk=hall_a.pk).update(
        accessibility_detail={"route": {"value": "yes"}, "widths": {"value": "yes"}},
        bike_parking_spaces=6,
        aed_on_site=True,
    )
    Facility.objects.filter(pk=padel_a.pk).update(
        accessibility_detail={"route": {"value": "yes"}, "widths": {"value": "partial"}},
        bike_parking_spaces=0,
    )
    for param in ("full_access", "bikes", "aed"):
        html = client.get(f"{C}/?{param}=on").content.decode()
        assert hall_a.name in html and padel_a.name not in html and gym_a.name not in html, param
    html = client.get(f"{C}/").content.decode()
    assert "Con aparcabicis" in html and "Con DESA" in html and ">" in html


def test_defibrillator_adapter_is_sorted_by_distance():
    found = get_adapter("defibrillators").nearest(42.7710, -7.8930, limit=3)
    assert len(found) == 3
    assert [f["distance_m"] for f in found] == sorted(f["distance_m"] for f in found)
    assert all("ficticia" in f["name"] or "ficticio" in f["name"] for f in found)
    assert CsvDefibrillatorAdapter().nearest(None, None) == []
    assert 1000 < distance_m(42.0, -8.0, 42.01, -8.0) < 1200


def test_manage_fills_nearest_aed(client, admin_a, hall_a):
    Facility.objects.filter(pk=hall_a.pk).update(latitude=42.7712, longitude=-7.8925)
    client.force_login(admin_a)
    r = client.post(f"{C}/xestion/instalacions/{hall_a.pk}/", {"accion": "desa"})
    assert r.status_code == 302
    hall_a.refresh_from_db()
    assert hall_a.aed_near_name and hall_a.aed_near_distance_m is not None
    html = client.get(f"{C}/instalacions/{hall_a.pk}/").content.decode()
    assert "O máis próximo" in html and hall_a.aed_near_name in html


def test_vitality_uses_detailed_accessibility(hall_a):
    basic = _accessibility(hall_a)
    hall_a.accessibility_detail = {
        "route": {"value": "yes"},
        "widths": {"value": "partial"},
        "toilets": {"value": "no"},
    }
    assert _accessibility(hall_a) == round(100 * 1.5 / 7) != basic
    hall_a.accessibility_detail = {}
    assert _accessibility(hall_a) == basic  # sen detalle: a lista básica


def test_safety_review_includes_new_points():
    labels = " ".join(str(item) for item in SAFETY_CHECKLIST)
    for word in ("Accesibilidade detallada", "DESA", "Aparcabicis"):
        assert word in labels
