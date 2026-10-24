# SPDX-License-Identifier: EUPL-1.2
"""v4: estatísticas da monitora (só os seus grupos; ausencias seguidas; carga semanal)."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import Membership, Role, User
from apps.activities import stats
from apps.activities.models import Activity, Attendance, Enrollment, Group, Session

pytestmark = pytest.mark.django_db


def make_group(muni, monitor, name):
    a = Activity.objects.create(municipality=muni, name="Pilates")
    return Group.objects.create(
        municipality=muni,
        activity=a,
        name=name,
        monitor=monitor,
        min_age=0,
        max_age=110,
        places=10,
        fee_cents=0,
        weekdays="0,1,2,3,4,5,6",
        start_time=dt.time(10),
    )


@pytest.fixture
def setup(muni_a, citizen):
    mon = User.objects.create_user("mon@example.org")
    Membership.objects.create(user=mon, municipality=muni_a, role=Role.MONITOR)
    g = make_group(muni_a, mon, "Mañá")
    ana = Enrollment.objects.create(
        municipality=muni_a, group=g, user=citizen, status="active", surnames="Souto Pazos"
    )
    other = User.objects.create_user("veciño2@example.org", display_name="Xan")
    xan = Enrollment.objects.create(
        municipality=muni_a, group=g, user=other, status="active", surnames="Rial"
    )
    today = timezone.localdate()
    # 4 sesións: Ana vén ás catro (RPE 5, 60 min); Xan só á primeira
    for i, back in enumerate((10, 8, 3, 1)):
        s = Session.objects.create(
            municipality=muni_a,
            group=g,
            date=today - dt.timedelta(days=back),
            start_time=dt.time(10),
            duration_minutes=60,
        )
        Attendance.objects.create(session=s, enrollment=ana, present=True, rpe=5, minutes=60)
        Attendance.objects.create(
            session=s, enrollment=xan, present=i == 0, minutes=60 if i == 0 else 0
        )
    return {"monitor": mon, "group": g, "ana": ana, "xan": xan}


def test_group_stats_attendance_rpe_and_absences(setup):
    data = stats.group_stats(setup["group"])
    assert [r["pct"] for r in data["sessions"]] == [100, 50, 50, 50]
    assert data["avg_pct"] == 62 and data["avg_rpe"] == 5
    # Xan faltou ás tres últimas: aparece só con nome + primeiro apelido
    assert len(data["absences"]) == 1
    assert data["absences"][0]["streak"] == 3 and "Pazos" not in data["absences"][0]["label"]


def test_weekly_load_is_mean_per_person(setup):
    data = stats.group_stats(setup["group"])
    total = sum(w["load"] * w["people"] for w in data["weeks"])
    assert total == 4 * 5 * 60  # só Ana ten esforzo: 4 sesións × RPE 5 × 60 min


def test_absence_streak_needs_three_in_a_row(setup):
    last = Session.objects.filter(group=setup["group"]).order_by("-date").first()
    Attendance.objects.filter(session=last, enrollment=setup["xan"]).update(present=True)
    assert stats.group_stats(setup["group"])["absences"] == []


def test_stats_page_shows_only_own_groups(client, setup, muni_a):
    other_mon = User.objects.create_user("outra@example.org")
    Membership.objects.create(user=other_mon, municipality=muni_a, role=Role.MONITOR)
    make_group(muni_a, other_mon, "Grupo alleo")
    client.force_login(setup["monitor"])
    r = client.get("/c/concello-a/monitor/estatisticas/")
    html = r.content.decode()
    assert r.status_code == 200 and "Mañá" in html and "Grupo alleo" not in html
    assert "Barras relativas ao valor máis alto" in html  # a carga semanal indica a súa escala
    assert "<table" in html  # cada gráfica ten a súa táboa


def test_citizen_cannot_see_stats(client, citizen):
    client.force_login(citizen)
    assert client.get("/c/concello-a/monitor/estatisticas/").status_code in (302, 403)
