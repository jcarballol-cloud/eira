# SPDX-License-Identifier: EUPL-1.2
"""Fase 1 da v2: cada perfil só accede á súa ferramenta (permisos reais no backend)."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import Membership, RegionMembership, Role, User
from apps.activities.models import Activity, Group
from apps.maintenance.models import WorkOrder

pytestmark = pytest.mark.django_db


@pytest.fixture
def people(muni_a, region, citizen, admin_a, operator_a):
    monitor = User.objects.create_user("monitora-a@example.org")
    Membership.objects.create(user=monitor, municipality=muni_a, role=Role.MONITOR)
    dep = User.objects.create_user("deputacion@example.org")
    RegionMembership.objects.create(user=dep, region=region)
    return {
        "neighbour": citizen,
        "admin": admin_a,
        "operator": operator_a,
        "monitor": monitor,
        "region": dep,
    }


@pytest.fixture
def objects(muni_a, padel_a, people):
    other_op = User.objects.create_user("outro-operario@example.org")
    Membership.objects.create(user=other_op, municipality=muni_a, role=Role.MAINTENANCE)
    mine = WorkOrder.objects.create(
        municipality=muni_a,
        facility=padel_a,
        title="Miña",
        due_date=timezone.localdate(),
        assigned_to=people["operator"],
    )
    theirs = WorkOrder.objects.create(
        municipality=muni_a,
        facility=padel_a,
        title="Doutro",
        due_date=timezone.localdate(),
        assigned_to=other_op,
    )
    act = Activity.objects.create(municipality=muni_a, name="Fútbol")
    group = Group.objects.create(
        municipality=muni_a,
        activity=act,
        name="G",
        monitor=people["monitor"],
        start_time=dt.time(17),
        weekdays="0,1,2,3,4,5,6",
    )
    return {"mine": mine, "theirs": theirs, "group": group}


C = "/c/concello-a"
# (url, quen pode entrar con 200) — o resto recibe 403
MATRIX = [
    (f"{C}/app/", {"neighbour"}),
    (f"{C}/reservas/", {"neighbour"}),
    (f"{C}/incidencias/nova/", {"neighbour"}),
    ("/conta/familia/", {"neighbour"}),
    # A deputación só ve agregados sen acceso de soporte (v3): panel, ordes e altas teñen datos persoais
    (f"{C}/xestion/", {"admin"}),
    (f"{C}/xestion/indicadores/", {"admin", "region"}),
    (f"{C}/xestion/ordes/", {"admin"}),
    (f"{C}/xestion/altas/", {"admin"}),
    (f"{C}/app/benvida/", {"neighbour"}),
    (f"{C}/operario/", {"operator"}),
    (f"{C}/operario/calendario/", {"operator"}),
    (f"{C}/monitor/", {"monitor"}),
    ("/rexion/proba/", {"region"}),
]


@pytest.mark.parametrize("url, allowed", MATRIX)
@pytest.mark.parametrize("who", ["neighbour", "admin", "operator", "monitor", "region"])
def test_role_matrix(client, people, url, allowed, who):
    client.force_login(people[who])
    status = client.get(url).status_code
    assert status == (200 if who in allowed else 403), (who, url, status)


def test_staff_cannot_book_or_enroll_as_neighbour(client, people, padel_a, objects):
    from conftest import next_slot

    start = next_slot(padel_a)
    for who in ("admin", "operator", "monitor", "region"):
        client.force_login(people[who])
        r = client.post(
            f"{C}/instalacions/{padel_a.pk}/reservar/",
            {"inicio": start.isoformat(), "accept_rules": "on", "participants": "2"},
        )
        assert r.status_code == 403, who
        r = client.post(
            f"{C}/actividades/grupo/{objects['group'].pk}/inscribirse/", {"participant": "self"}
        )
        assert r.status_code == 403, who


def test_staff_grid_has_no_booking_links(client, people, padel_a):
    client.force_login(people["admin"])
    html = client.get(f"{C}/instalacions/{padel_a.pk}/").content.decode()
    assert "/reservar/?inicio=" not in html


def test_operator_only_sees_own_and_unassigned_orders(client, people, objects, padel_a, muni_a):
    unassigned = WorkOrder.objects.create(
        municipality=muni_a, facility=padel_a, title="Libre", due_date=timezone.localdate()
    )
    client.force_login(people["operator"])
    html = client.get(f"{C}/operario/").content.decode()
    assert "Miña" in html and "Libre" in html and "Doutro" not in html
    assert client.get(f"{C}/operario/orde/{objects['mine'].pk}/").status_code == 200
    assert client.get(f"{C}/operario/orde/{unassigned.pk}/").status_code == 200
    assert client.get(f"{C}/operario/orde/{objects['theirs'].pk}/").status_code == 404
    r = client.post(f"{C}/operario/orde/{objects['theirs'].pk}/", {"action": "close"})
    assert r.status_code == 404


def test_region_is_read_only_except_support_actions(client, people, padel_a, muni_a):
    from django.utils import timezone

    from apps.tenants.models import SupportAccess

    SupportAccess.objects.create(
        municipality=muni_a,
        region=muni_a.region,
        reason="proba",
        granted_by=people["admin"],
        expires_at=timezone.now() + SupportAccess.DURATION,
    )
    client.force_login(people["region"])
    html = client.get(f"{C}/xestion/").content.decode()
    assert "como Deputación" in html and "Volver á rede" in html
    assert (
        client.post(f"{C}/xestion/instalacions/{padel_a.pk}/normas/", {"text": "x"}).status_code
        == 403
    )
    assert client.post(f"{C}/xestion/peches/alerta/").status_code == 403
    assert (
        client.get(f"{C}/xestion/portabilidade/exportar.zip").status_code == 200
    )  # soporte: exportar


@pytest.mark.parametrize(
    "who, expected",
    [
        ("neighbour", "/c/concello-a/app/"),
        ("admin", "/c/concello-a/xestion/"),
        ("operator", "/c/concello-a/operario/"),
        ("monitor", "/c/concello-a/monitor/"),
        ("region", "/rexion/proba/"),
    ],
)
def test_logo_goes_to_profile_home(client, people, who, expected, padel_a):
    from apps.accounts.profiles import home_url

    assert home_url(people[who]) == expected
    client.force_login(people[who])
    html = client.get(expected).content.decode()
    assert f'class="brand" href="{expected}"' in html
    assert 'action="/acceso/sair/"' in html  # saír sempre a un toque


def test_device_frame_toggle(client, people):
    client.force_login(people["neighbour"])
    assert "framed-app" in client.get(f"{C}/app/").content.decode()
    r = client.get(f"{C}/app/?marco=0")
    assert "framed-app" not in r.content.decode() and r.cookies["eira_marco"].value == "0"
    assert "framed-app" not in client.get(f"{C}/app/").content.decode()
    client.force_login(people["admin"])
    assert (
        "framed" not in client.get(f"{C}/xestion/?marco=1").content.decode().split("<body")[1][:120]
    )


def test_demo_home_two_steps_and_demo_bar(client, settings, people, muni_a):
    from apps.integrations import demo

    settings.EIRA_DEMO_TOOLS = True
    demo.DEMO_TENANTS.append(
        {"slug": "concello-a", "kind": "Proba", "summary": "Concello de proba"}
    )
    try:
        html = client.get("/").content.decode()
        assert "Paso 1 de 2" in html and "?concello=concello-a" in html
        assert 'name="email" value="uxia@demo.eira.example"' not in html  # perfís só no paso 2
        html = client.get("/?concello=vilardeiras").content.decode()
        assert "Escolle primeiro un concello" not in html or "Quen es" in html
    finally:
        demo.DEMO_TENANTS.pop()


def test_lema_antigo_retirado(client, muni_a):
    html = client.get("/").content.decode()
    assert "O difícil é abrir a porta" not in html
    assert "Software libre para a xestión deportiva municipal" in html


def test_every_sidebar_entry_marks_itself_active(client, people, muni_a, objects):
    """v3: cada entrada do menú lateral do concello márcase con aria-current na súa páxina."""
    import re

    client.force_login(people["admin"])
    html = client.get(f"{C}/xestion/").content.decode()
    nav = html[html.index('class="sidenav"') : html.index("</nav>", html.index('class="sidenav"'))]
    links = re.findall(r'<a href="([^"]+)"', nav)
    assert len(links) >= 15
    failures = []
    for href in links:
        page = client.get(href)
        assert page.status_code == 200, href
        body = page.content.decode()
        side = body[
            body.index('class="sidenav"') : body.index("</nav>", body.index('class="sidenav"'))
        ]
        if not re.search(rf'<a href="{re.escape(href)}"[^>]*aria-current="page"', side):
            failures.append(href)
    assert not failures, failures
