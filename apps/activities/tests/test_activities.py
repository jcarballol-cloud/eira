# SPDX-License-Identifier: EUPL-1.2
import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import Consent, Dependent, Household, Membership, Role, User
from apps.activities import services
from apps.activities.models import Activity, Attendance, Enrollment, Group, Session
from apps.analytics import observatory

pytestmark = pytest.mark.django_db


@pytest.fixture
def monitor(muni_a):
    u = User.objects.create_user("monitora@example.org")
    Membership.objects.create(user=u, municipality=muni_a, role=Role.MONITOR)
    return u


@pytest.fixture
def kids_group(muni_a, monitor):
    a = Activity.objects.create(municipality=muni_a, name="Fútbol")
    return Group.objects.create(
        municipality=muni_a,
        activity=a,
        name="Benxamín",
        monitor=monitor,
        min_age=8,
        max_age=10,
        places=2,
        fee_cents=0,
        weekdays="0,1,2,3,4,5,6",
        start_time=dt.time(17),
        rpe_scale="omni",
    )


def child(parent, name="Noa", age=9, consents=("data",)):
    hh, _c = Household.objects.get_or_create(responsible=parent)
    d = Dependent.objects.create(
        household=hh, first_name=name, birth_year=timezone.localdate().year - age
    )
    for k in consents:
        Consent.objects.create(dependent=d, kind=k, granted_by=parent)
    return d


def test_minor_needs_data_consent(kids_group, citizen):
    with pytest.raises(services.EnrollmentError):
        services.enroll(kids_group, citizen, child(citizen, consents=()))
    e = services.enroll(kids_group, citizen, child(citizen, "Lúa"))
    assert e.status == Enrollment.Status.ACTIVE and e.pseudonym


def test_age_range_enforced(kids_group, citizen):
    with pytest.raises(services.EnrollmentError):
        services.enroll(kids_group, citizen, child(citizen, age=14))


def test_only_own_dependents(kids_group, citizen, outsider):
    with pytest.raises(services.EnrollmentError):
        services.enroll(kids_group, citizen, child(outsider))


def test_waitlist_and_promotion(kids_group, citizen, outsider):
    a = services.enroll(kids_group, citizen, child(citizen, "A"))
    services.enroll(kids_group, citizen, child(citizen, "B"))
    c = services.enroll(kids_group, outsider, child(outsider, "C"))
    assert c.status == Enrollment.Status.WAITLIST
    services.cancel_enrollment(a)
    c.refresh_from_db()
    assert c.status == Enrollment.Status.ACTIVE


def test_paid_group_goes_through_payment(client, kids_group, citizen):
    kids_group.fee_cents = 1500
    kids_group.save()
    d = child(citizen)
    client.force_login(citizen)
    r = client.post(
        f"/c/concello-a/actividades/grupo/{kids_group.pk}/inscribirse/",
        {"participant": d.pk, "surnames": "Proba Exemplo"},
    )
    assert "/dev/tpv/" in r["Location"]
    r = client.post(r["Location"], {"result": "ok"})
    client.get(r["Location"])
    assert Enrollment.objects.get().status == Enrollment.Status.ACTIVE


def test_monitor_tablet_flow(client, kids_group, citizen, monitor):
    with_perf = services.enroll(
        kids_group, citizen, child(citizen, "Con", consents=("data", "performance"))
    )
    without = services.enroll(kids_group, citizen, child(citizen, "Sen", consents=("data",)))
    client.force_login(monitor)
    assert client.get("/c/concello-a/monitor/").status_code == 200
    session = Session.objects.get(group=kids_group, date=timezone.localdate())
    client.post(
        f"/c/concello-a/monitor/sesion/{session.pk}/asistencia/",
        {f"p{with_perf.pk}": "1", f"p{without.pk}": "1"},
    )
    assert Attendance.objects.filter(session=session, present=True).count() == 2
    client.post(
        f"/c/concello-a/monitor/sesion/{session.pk}/esforzo/",
        {f"rpe{with_perf.pk}": "7", f"rpe{without.pk}": "5"},
    )
    a1 = Attendance.objects.get(session=session, enrollment=with_perf)
    a2 = Attendance.objects.get(session=session, enrollment=without)
    assert a1.rpe == 7 and a1.session_load == 7 * 60
    assert a2.rpe is None  # sen consentimento de rendemento non se garda o esforzo
    session.refresh_from_db()
    # só se pecha se xa rematou (v4: antes pechábase aínda que non empezara)
    assert bool(session.closed_at) == (timezone.now() >= session.end_dt)


@pytest.mark.parametrize(
    "minutes_from_start, closed, expected",
    [
        (-60, False, "upcoming"),
        (-10, False, "open"),
        (30, False, "open"),
        (30, True, "open"),
        (120, False, "finished"),
        (120, True, "closed"),
    ],
)
def test_session_status_depends_on_time(kids_group, minutes_from_start, closed, expected):
    now = timezone.now()
    start = timezone.localtime(now - dt.timedelta(minutes=minutes_from_start))
    s = Session(
        group=kids_group,
        municipality=kids_group.municipality,
        date=start.date(),
        start_time=start.time().replace(tzinfo=None),
        duration_minutes=60,
        closed_at=now if closed else None,
    )
    assert s.status_at(now) == expected


def test_saving_effort_before_the_end_keeps_session_open(kids_group, citizen):
    e = services.enroll(
        kids_group, citizen, child(citizen, "Con", consents=("data", "performance"))
    )
    start = timezone.localtime(timezone.now() + dt.timedelta(minutes=30))
    s = Session.objects.create(
        group=kids_group,
        municipality=kids_group.municipality,
        date=start.date(),
        start_time=start.time(),
        duration_minutes=60,
    )
    services.record_attendance(s, {e.pk})
    services.record_rpe(s, {e.pk: 6})
    s.refresh_from_db()
    assert s.closed_at is None and s.status != "closed"


def test_monitor_only_sees_own_groups(client, kids_group, muni_a):
    other = User.objects.create_user("outra-monitora@example.org")
    Membership.objects.create(user=other, municipality=muni_a, role=Role.MONITOR)
    client.force_login(other)
    client.get("/c/concello-a/monitor/")
    assert not Session.objects.exists()
    s = Session.objects.create(
        municipality=muni_a, group=kids_group, date=timezone.localdate(), start_time=dt.time(17)
    )
    assert client.get(f"/c/concello-a/monitor/sesion/{s.pk}/asistencia/").status_code == 404


def test_citizen_cannot_use_tablet(client, citizen, muni_a):
    client.force_login(citizen)
    assert client.get("/c/concello-a/monitor/").status_code == 403


def _attendance_for(group, n, k_age):
    parent = User.objects.create_user(f"p{n}{k_age}@example.org")
    session = Session.objects.create(
        municipality=group.municipality,
        group=group,
        date=timezone.localdate() - dt.timedelta(days=2),
        start_time=dt.time(17),
    )
    for i in range(n):
        d = child(parent, f"Proba{i:02d}xyz", age=k_age)
        e = Enrollment.objects.create(
            municipality=group.municipality,
            group=group,
            user=parent,
            dependent=d,
            status="active",
            pseudonym=services.pseudonym(i + 1000 * n),
        )
        Attendance.objects.create(session=session, enrollment=e, present=True, minutes=60, rpe=5)


@pytest.mark.parametrize("n, hidden", [(9, True), (10, False)])
def test_observatory_threshold(kids_group, n, hidden, settings):
    settings.EIRA_MIN_AGGREGATION = 10
    _attendance_for(kids_group, n, 9)
    row = next(
        r for r in observatory.summary(kids_group.municipality)["rows"] if r["band"] == "6–11"
    )
    assert row["suppressed"] is hidden
    if hidden:
        assert (
            row["weekly_minutes"] is None and row["attendance_pct"] is None and row["trend"] == []
        )
        assert observatory.microdata(kids_group.municipality) == []
    else:
        assert row["weekly_minutes"] == 10 and row["attendance_pct"] == 100  # 60 min en 6 semanas


def test_observatory_threshold_is_configurable(kids_group, settings):
    _attendance_for(kids_group, 5, 9)
    settings.EIRA_MIN_AGGREGATION = 5
    row = next(
        r for r in observatory.summary(kids_group.municipality)["rows"] if r["band"] == "6–11"
    )
    assert not row["suppressed"]


def test_observatory_page_never_shows_names(client, kids_group, settings):
    settings.EIRA_MIN_AGGREGATION = 2
    _attendance_for(kids_group, 3, 9)
    html = client.get("/c/concello-a/actividades/observatorio/").content.decode()
    assert "Proba00xyz" not in html and "Proba01xyz" not in html


def test_microdata_is_pseudonymised_and_admin_only(client, kids_group, admin_a, citizen, settings):
    settings.EIRA_MIN_AGGREGATION = 2
    _attendance_for(kids_group, 3, 9)
    client.force_login(citizen)
    assert client.get("/c/concello-a/actividades/observatorio/?csv=micro").status_code == 403
    client.force_login(admin_a)
    body = client.get("/c/concello-a/actividades/observatorio/?csv=micro").content.decode()
    assert "Proba00xyz" not in body and "6–11" in body and len(body.splitlines()) == 4


def test_minor_enrollment_requires_surnames(client, kids_group, citizen):
    """v4: ao inscribir un/unha menor nunha escola, os apelidos son obrigatorios (dato da inscrición)."""
    kid = child(citizen, "Iria")
    client.force_login(citizen)
    url = f"/c/concello-a/actividades/grupo/{kids_group.pk}/inscribirse/"
    r = client.post(url, {"participant": kid.pk})
    assert r.status_code == 400 and not Enrollment.objects.exists()
    assert "como figuran no padrón" in r.content.decode()
    client.post(url, {"participant": kid.pk, "surnames": "Souto Pazos"})
    assert Enrollment.objects.get().surnames == "Souto Pazos"
