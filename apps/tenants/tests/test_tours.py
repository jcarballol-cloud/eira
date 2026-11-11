# SPDX-License-Identifier: EUPL-1.2
"""v1.5.1: guía paso a paso de cada perfil (definición, cando aparece e CSP)."""

import json
import re
from pathlib import Path

import pytest
from django.conf import settings as dj_settings
from django.urls import NoReverseMatch, reverse
from django.utils import translation

from apps.tenants.tours import TOURS, tour_payload

C = "/c/concello-a"
TEMPLATES = Path(dj_settings.BASE_DIR) / "templates"


def tour_json(html):
    m = re.search(r'<script id="tour-data" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1)) if m else None


def test_every_profile_has_a_tour_of_4_to_7_steps():
    assert set(TOURS) == {"neighbour", "operator", "cleaning", "monitor", "admin", "region"}
    for kind, tour in TOURS.items():
        assert 4 <= len(tour["steps"]) <= 7, kind
        for _target, title, body in tour["steps"]:
            assert str(title).strip() and str(body).strip(), kind
            assert len(str(body)) <= 200, f"{kind}: texto longo de máis ({title})"


def test_start_screens_exist():
    for kind, tour in TOURS.items():
        args = ["proba"] if tour["start"].startswith("region:") else ["concello-a"]
        try:
            reverse(tour["start"], args=args)
        except NoReverseMatch:  # pragma: no cover - a mensaxe di que pantalla falta
            pytest.fail(f"{kind}: non existe a pantalla {tour['start']}")


def test_every_target_is_marked_in_some_template():
    """Se alguén quita un `data-tour` dunha plantilla, este test avisa (o E2E mira a pantalla)."""
    marks = set()
    for f in TEMPLATES.rglob("*.html"):
        marks |= set(re.findall(r'data-tour="([a-z-]+)"', f.read_text(encoding="utf-8")))
    for kind, tour in TOURS.items():
        for target, title, _body in tour["steps"]:
            if target:
                assert target in marks, f'{kind} · {title}: falta data-tour="{target}"'


def test_payload_uses_selectors_and_translates():
    with translation.override("es"):
        data = tour_payload("neighbour", auto=True)
    assert data["id"].startswith("neighbour-v")
    assert data["steps"][0]["target"] == '[data-tour="search"]'
    assert data["steps"][1]["target"] is None  # centrado
    assert data["steps"][0]["title"] == "Busca una instalación"
    assert data["labels"]["step"] == "Paso %(n)s de %(total)s"


def test_demo_shows_tour_on_profile_home_only(client, settings, citizen, muni_a):
    settings.EIRA_DEMO_TOOLS = True
    client.force_login(citizen)
    html = client.get(f"{C}/app/").content.decode()
    data = tour_json(html)
    assert data and data["auto"] is True and len(data["steps"]) == 7
    assert 'role="dialog"' not in html  # <dialog> xa ten o rol; sen duplicalo
    assert '<dialog class="tour" id="tour" aria-modal="true" aria-labelledby="tour-title"' in html
    assert "js/tour" in html and "tour.js" in html
    other = client.get(f"{C}/reservas/").content.decode()
    assert tour_json(other) is None and "tour.js" not in other
    assert f'href="{C}/app/?guia=1" data-tour-open' in other  # «?» → «Ver a guía»


def test_real_install_needs_the_municipality_to_enable_it(client, settings, admin_a, muni_a):
    settings.EIRA_DEMO_TOOLS = False
    client.force_login(admin_a)
    html = client.get(f"{C}/xestion/").content.decode()
    assert tour_json(html) is None and "Ver a guía" not in html
    muni_a.guided_tour = True
    muni_a.save()
    html = client.get(f"{C}/xestion/").content.decode()
    data = tour_json(html)
    assert data and data["id"].startswith("admin-v") and len(data["steps"]) == 6
    assert "Ver a guía" in html


@pytest.mark.parametrize(
    "who,path,kind",
    [
        ("operator_a", f"{C}/operario/", "operator"),
        ("cleaner_a", f"{C}/operario/", "cleaning"),
    ],
)
def test_staff_profiles_get_their_own_tour(client, settings, request, who, path, kind):
    settings.EIRA_DEMO_TOOLS = True
    client.force_login(request.getfixturevalue(who))
    data = tour_json(client.get(path).content.decode())
    assert data and data["id"].startswith(f"{kind}-v")


def test_tour_markup_has_no_inline_script_or_style(client, settings, citizen, muni_a):
    settings.EIRA_DEMO_TOOLS = True
    client.force_login(citizen)
    html = client.get(f"{C}/app/").content.decode()
    dialog = re.search(r"<dialog.*?</dialog>", html, re.S).group(0)
    assert "style=" not in dialog and "<script" not in dialog
    for tag in re.findall(r"<script\b[^>]*>", html):
        assert "src=" in tag or 'type="application/json"' in tag, tag


def test_settings_can_enable_the_tour(client, admin_a, muni_a):
    from apps.accounts.tests.test_v14 import _settings_form_data

    client.force_login(admin_a)
    form = _settings_form_data(client)
    form["guided_tour"] = "on"
    assert client.post(f"{C}/xestion/configuracion/", form).status_code == 302
    muni_a.refresh_from_db()
    assert muni_a.guided_tour is True
