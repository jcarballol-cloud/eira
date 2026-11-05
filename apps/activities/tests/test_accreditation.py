# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · E: bloqueo da asignación con menores, permisos, revisión e minimización."""

import datetime as dt

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import (
    AuditLog,
    Dependent,
    Household,
    Membership,
    RegionMembership,
    Role,
    User,
)
from apps.activities import accreditation
from apps.activities.models import Activity, Enrollment, Group, MinorsAccreditation
from apps.notifications.models import Notification
from apps.tenants.models import Municipality, Region, SupportAccess

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    m = Municipality.objects.create(name="Acreditas", slug="acreditas")
    admin = User.objects.create_user("admin-acc@example.org")
    Membership.objects.create(user=admin, municipality=m, role=Role.ADMIN)
    monitor = User.objects.create_user("mon-acc@example.org", display_name="Mon")
    Membership.objects.create(user=monitor, municipality=m, role=Role.MONITOR)
    activity = Activity.objects.create(municipality=m, name="Natación")
    minors = Group.objects.create(
        municipality=m, activity=activity, name="Infantil", start_time=dt.time(17, 0), max_age=12
    )
    adults = Group.objects.create(
        municipality=m, activity=activity, name="Adultas", start_time=dt.time(20, 0), min_age=18
    )
    return m, admin, monitor, minors, adults


def group_url(m, group):
    return f"/c/{m.slug}/xestion/actividades/grupo/{group.pk}/"


def acc_url(m):
    return f"/c/{m.slug}/xestion/actividades/acreditacions/"


def test_blocked_without_accreditation(client, setup):
    m, admin, monitor, minors, _adults = setup
    client.force_login(admin)
    resp = client.post(
        group_url(m, minors), {"action": "assign", "monitor": monitor.pk}, follow=True
    )
    minors.refresh_from_db()
    assert minors.monitor_id is None
    assert "falta marcar a acreditación" in resp.content.decode()
    assert AuditLog.objects.filter(action="accreditation.blocked").exists()


def test_allowed_after_confirm_and_only_who_and_when_stored(client, setup):
    m, admin, monitor, minors, _adults = setup
    client.force_login(admin)
    member = Membership.objects.get(user=monitor, municipality=m)
    client.post(acc_url(m), {"member": member.pk, "verified": "1"})
    record = MinorsAccreditation.objects.get(user=monitor)
    assert record.confirmed_by == admin and record.confirmed_at
    fields = {f.name for f in MinorsAccreditation._meta.get_fields()}
    assert fields == {
        "id",
        "municipality",
        "user",
        "confirmed_by",
        "confirmed_at",
        "review_notified_at",
    }
    client.post(group_url(m, minors), {"action": "assign", "monitor": monitor.pk})
    minors.refresh_from_db()
    assert minors.monitor == monitor


def test_checkbox_required(client, setup):
    m, admin, monitor, _minors, _adults = setup
    client.force_login(admin)
    member = Membership.objects.get(user=monitor, municipality=m)
    client.post(acc_url(m), {"member": member.pk})
    assert not MinorsAccreditation.objects.exists()


def test_adult_group_not_blocked(client, setup):
    m, admin, monitor, _minors, adults = setup
    client.force_login(admin)
    client.post(group_url(m, adults), {"action": "assign", "monitor": monitor.pk})
    adults.refresh_from_db()
    assert adults.monitor == monitor


def test_adult_group_with_enrolled_minor_counts(setup):
    m, admin, monitor, _minors, adults = setup
    home = Household.objects.create(responsible=admin)
    kid = Dependent.objects.create(household=home, first_name="K", birth_year=2015)
    Enrollment.objects.create(municipality=m, group=adults, user=admin, dependent=kid)
    assert adults.has_minors
    with pytest.raises(accreditation.AssignmentBlocked):
        accreditation.assign_monitor(adults, monitor, by=admin)


@pytest.mark.parametrize("role", [Role.DPO, Role.MAINTENANCE, Role.MONITOR, Role.CLEANING])
def test_other_roles_cannot_mark(client, setup, role):
    m, _admin, monitor, _minors, _adults = setup
    other = User.objects.create_user(f"{role}@example.org")
    Membership.objects.create(user=other, municipality=m, role=role)
    client.force_login(other)
    member = Membership.objects.get(user=monitor, municipality=m)
    assert client.post(acc_url(m), {"member": member.pk, "verified": "1"}).status_code == 403
    assert client.get(acc_url(m)).status_code == 403
    assert not MinorsAccreditation.objects.exists()


def test_region_cannot_mark_even_with_support(client, setup):
    m, _admin, monitor, minors, _adults = setup
    region = Region.objects.create(name="Rexión", slug="rexion-acc")
    m.region = region
    m.save()
    dep = User.objects.create_user("dep-acc@example.org")
    RegionMembership.objects.create(user=dep, region=region)
    SupportAccess.objects.create(
        municipality=m,
        region=region,
        reason="x",
        expires_at=timezone.now() + dt.timedelta(hours=1),
    )
    client.force_login(dep)
    member = Membership.objects.get(user=monitor, municipality=m)
    assert client.post(acc_url(m), {"member": member.pk, "verified": "1"}).status_code == 403
    assert not MinorsAccreditation.objects.exists()
    resp = client.post(group_url(m, minors), {"action": "assign", "monitor": monitor.pk})
    assert resp.status_code == 403


def test_review_expires_notifies_once_and_blocks(setup):
    m, admin, monitor, minors, _adults = setup
    record = accreditation.confirm(m, monitor, by=admin)
    assert accreditation.status_of(m, monitor) == accreditation.CURRENT
    record.confirmed_at = timezone.now() - dt.timedelta(days=365)
    record.save()
    assert accreditation.status_of(m, monitor) == accreditation.EXPIRED
    with pytest.raises(accreditation.AssignmentBlocked):
        accreditation.assign_monitor(minors, monitor, by=admin)
    call_command("booking_maintenance", verbosity=0)
    assert Notification.objects.filter(user=admin, title__icontains="acreditación").count() == 1
    call_command("booking_maintenance", verbosity=0)
    assert Notification.objects.filter(user=admin, title__icontains="acreditación").count() == 1
    accreditation.confirm(m, monitor, by=admin)
    assert accreditation.status_of(m, monitor) == accreditation.CURRENT


def test_review_period_configurable(setup):
    m, admin, monitor, _minors, _adults = setup
    record = accreditation.confirm(m, monitor, by=admin)
    record.confirmed_at = timezone.now() - dt.timedelta(days=100)
    record.save()
    assert accreditation.status_of(m, monitor) == accreditation.CURRENT
    m.accreditation_review_months = 3
    m.save()
    assert accreditation.status_of(m, monitor) == accreditation.EXPIRED


def test_group_clean_blocks_admin_site_path(setup):
    _m, _admin, monitor, minors, _adults = setup
    minors.monitor = monitor
    with pytest.raises(ValidationError):
        minors.full_clean()


def test_withdraw_shows_warning_and_tenant_isolation(client, setup):
    m, admin, monitor, minors, _adults = setup
    other = Municipality.objects.create(name="Outro", slug="outro-acc")
    accreditation.confirm(m, monitor, by=admin)
    accreditation.assign_monitor(minors, monitor, by=admin)
    assert accreditation.status_of(other, monitor) == accreditation.MISSING
    accreditation.withdraw(m, monitor, by=admin)
    client.force_login(admin)
    assert "falta marcar a acreditación" in client.get(group_url(m, minors)).content.decode()
