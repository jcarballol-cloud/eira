# SPDX-License-Identifier: EUPL-1.2
"""v1.1 · Rexistro de limpeza: rol, plans, QR, sen conexión, enrutado, atrasos e exportación."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import Membership, Role
from apps.bookings.models import Booking
from apps.incidents.models import Incident
from apps.maintenance import cleaning
from apps.maintenance.models import CleaningLog, CleaningZone, Frequency, WorkOrder
from apps.maintenance.services import generate_orders
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


@pytest.fixture
def hall_zones(hall_a):
    return {z.name: z for z in hall_a.cleaning_zones.all()}


def _orders(muni):
    generate_orders(days=1, municipality=muni)


def test_template_creates_zones_and_plan(hall_a, hall_zones):
    assert set(hall_zones) >= {"Pista central", "Vestiario 1", "Aseos", "Bancadas"}
    aseos = hall_zones["Aseos"]
    task = aseos.tasks.get()
    assert task.kind == "cleaning" and task.frequency == Frequency.SEVERAL
    assert task.times_per_day == 3 and aseos.checklist_items()
    # Idempotente: aplicalo outra vez non duplica nada
    assert cleaning.apply_template(hall_a) == 0
    assert hall_a.cleaning_zones.count() == len(hall_zones)


def test_several_times_a_day_creates_one_order_per_round(hall_a, hall_zones, muni_a):
    today = timezone.localdate()
    generate_orders(days=1, today=today, municipality=muni_a)
    aseos = WorkOrder.objects.filter(zone=hall_zones["Aseos"], due_date=today)
    assert aseos.count() == 3 and {o.slot for o in aseos} == {0, 1, 2}
    assert all(o.kind == "cleaning" for o in aseos)
    assert "(1/3)" in aseos.order_by("slot").first().title
    assert generate_orders(days=1, today=today, municipality=muni_a) == 0


# ---------------------------------------------------------------------------
# Rol: a mesma app do operario, só coas tarefas de limpeza
def test_cleaner_only_sees_cleaning_tasks(client, hall_a, hall_zones, cleaner_a, muni_a):
    _orders(muni_a)
    regular = WorkOrder.objects.filter(facility=hall_a, kind="regular").first()
    assert regular is not None
    client.force_login(cleaner_a)
    html = client.get(f"{C}/operario/").content.decode()
    assert "Aseos" in html and regular.title not in html
    assert "Tarefas de limpeza" in html
    assert client.get(f"{C}/operario/orde/{regular.pk}/").status_code == 404
    mine = WorkOrder.objects.filter(kind="cleaning").first()
    assert client.get(f"{C}/operario/orde/{mine.pk}/").status_code == 200
    assert client.get(f"{C}/operario/calendario/").status_code == 200


@pytest.mark.parametrize(
    "url",
    [
        "/xestion/",
        "/xestion/limpeza/",
        "/xestion/ordes/",
        "/xestion/limpeza/rexistro/",
        "/app/",
        "/reservas/",
        "/incidencias/nova/",
        "/monitor/",
    ],
)
def test_cleaner_gets_403_elsewhere(client, cleaner_a, url):
    client.force_login(cleaner_a)
    assert client.get(C + url).status_code == 403


def test_cleaner_home_is_the_task_list(client, cleaner_a):
    from apps.accounts.profiles import home_url, kind_in_tenant

    assert kind_in_tenant(cleaner_a, {"cleaning"}) == "cleaning"
    assert home_url(cleaner_a).endswith("/operario/")


def test_maintenance_stops_seeing_cleaning_only_when_there_is_cleaning_staff(
    client, hall_a, operator_a, muni_a
):
    _orders(muni_a)
    client.force_login(operator_a)
    # Sen persoal de limpeza: como ata agora, mantemento ve tamén a limpeza
    assert "Limpeza: Aseos" in client.get(f"{C}/operario/").content.decode()
    from apps.accounts.models import User

    u = User.objects.create_user("outra-limpeza@example.org")
    Membership.objects.create(user=u, municipality=muni_a, role=Role.CLEANING)
    html = client.get(f"{C}/operario/").content.decode()
    assert "Limpeza: Aseos" not in html


# ---------------------------------------------------------------------------
# QR da zona
def test_qr_logs_who_when_what_and_closes_the_pending_round(
    client, hall_a, hall_zones, cleaner_a, muni_a
):
    _orders(muni_a)
    aseos = hall_zones["Aseos"]
    client.force_login(cleaner_a)
    url = f"{C}/operario/limpeza/{aseos.token}/"
    page = client.get(url).content.decode()
    assert "Rexistrar limpeza" in page and "data-offline-queue" in page
    r = client.post(url, {"done": ["0", "1"], "notes": "Falta xabón"})
    assert r.status_code == 302
    log = CleaningLog.objects.get()
    assert log.user == cleaner_a and log.zone == aseos and log.source == "qr"
    assert log.company == "Limpezas de Proba, S. L." and log.by_name == "Persoa de limpeza"
    assert len(log.done_items()) == 2 and len(log.items) == len(aseos.checklist_items())
    rounds = WorkOrder.objects.filter(zone=aseos).order_by("slot")
    assert [o.status for o in rounds] == ["done", "open", "open"]
    assert log.order == rounds[0]
    # Non conta como supervisión de mantemento, pero si como última limpeza
    hall_a.refresh_from_db()
    assert hall_a.last_supervision() is None and hall_a.last_cleaning() == log.done_at


def test_offline_sync_keeps_the_time_it_was_saved(client, hall_zones, cleaner_a):
    aseos = hall_zones["Aseos"]
    client.force_login(cleaner_a)
    saved = timezone.now() - dt.timedelta(hours=2)
    r = client.post(
        f"{C}/operario/limpeza/{aseos.token}/",
        {"done": ["0"], "_queued_at": saved.isoformat()},
        headers={"X-Eira-Sync": "1"},
    )
    assert r.status_code == 204
    assert abs((CleaningLog.objects.get().done_at - saved).total_seconds()) < 1
    # Unha hora futura ou moi vella non se acepta: úsase a de agora
    assert cleaning.parse_queued_at((timezone.now() + dt.timedelta(hours=1)).isoformat()) is None
    assert cleaning.parse_queued_at((saved - dt.timedelta(days=9)).isoformat()) is None


def test_closing_a_cleaning_order_also_logs_it(client, hall_zones, cleaner_a, muni_a):
    _orders(muni_a)
    order = WorkOrder.objects.filter(zone=hall_zones["Vestiario 1"]).order_by("slot").first()
    client.force_login(cleaner_a)
    client.post(f"{C}/operario/orde/{order.pk}/", {"action": "close", "done": ["0"]})
    log = CleaningLog.objects.get()
    assert log.order == order and log.source == "order" and log.zone == order.zone


def test_qr_is_public_info_for_everyone_else(client, hall_zones, citizen):
    aseos = hall_zones["Aseos"]
    url = f"{C}/operario/limpeza/{aseos.token}/"
    r = client.get(url)
    assert r.status_code == 200 and "data-offline-queue" not in r.content.decode()
    client.force_login(citizen)
    assert "Este QR é para o persoal de limpeza" in client.get(url).content.decode()
    assert client.post(url, {"done": ["0"]}).status_code == 404
    assert not CleaningLog.objects.exists()


def test_qr_of_another_council_is_404(client, hall_zones, court_b, admin_b):
    client.force_login(admin_b)
    token = hall_zones["Aseos"].token
    assert client.get(f"/c/concello-b/operario/limpeza/{token}/").status_code == 404


def test_facility_page_shows_last_cleaning(client, hall_a, hall_zones, cleaner_a):
    cleaning.record(facility=hall_a, user=cleaner_a, zone=hall_zones["Pista central"])
    html = client.get(f"{C}/instalacions/{hall_a.pk}/").content.decode()
    assert "Última limpeza: hoxe" in html


# ---------------------------------------------------------------------------
# Atrasos
def test_overdue_zone_alerts_the_council_once(hall_a, hall_zones, cleaner_a, admin_a, muni_a):
    aseos = hall_zones["Aseos"]
    for z in hall_zones.values():
        cleaning.record(facility=hall_a, user=cleaner_a, zone=z)
    old = timezone.now() - dt.timedelta(hours=aseos.max_hours + 2)
    CleaningLog.objects.filter(zone=aseos).update(done_at=old)
    late = cleaning.overdue_zones(muni_a)
    assert [r["zone"] for r in late] == [aseos]
    assert cleaning.check_overdue(muni_a) == 1
    assert Notification.objects.filter(user=admin_a, title__contains="Aseos").count() == 1
    assert Notification.objects.filter(user=cleaner_a, title__contains="Aseos").exists()
    assert cleaning.check_overdue(muni_a) == 0  # non se repite
    cleaning.record(facility=hall_a, user=cleaner_a, zone=aseos)
    assert cleaning.overdue_zones(muni_a) == []
    aseos.refresh_from_db()
    assert aseos.alerted_at is None


def test_new_zone_is_not_overdue_until_its_time_passes(hall_a, muni_a):
    zone = CleaningZone.objects.create(
        municipality=muni_a, facility=hall_a, name="Ximnasio pequeno", max_hours=4
    )
    assert zone not in [r["zone"] for r in cleaning.overdue_zones(muni_a)]
    CleaningZone.objects.filter(pk=zone.pk).update(
        created_at=timezone.now() - dt.timedelta(hours=5)
    )
    assert zone in [r["zone"] for r in cleaning.overdue_zones(muni_a)]


def test_overdue_cleaning_lowers_maintenance_in_vitality(hall_a, hall_zones, cleaner_a):
    from apps.analytics.vitality import _maintenance

    today = timezone.localdate()
    for z in hall_zones.values():
        cleaning.record(facility=hall_a, user=cleaner_a, zone=z)
    before = _maintenance(hall_a, today)
    CleaningLog.objects.filter(zone=hall_zones["Aseos"]).update(
        done_at=timezone.now() - dt.timedelta(days=2)
    )
    assert _maintenance(hall_a, today) == max(0, before - 10)


# ---------------------------------------------------------------------------
# Enrutado por tipo
def test_cleaning_incident_goes_to_cleaning_staff(hall_a, citizen, cleaner_a, admin_a, operator_a):
    from apps.incidents.services import notify_staff_new_incident

    inc = Incident.objects.create(
        municipality=hall_a.municipality,
        facility=hall_a,
        reporter=citizen,
        category=Incident.Category.CLEANING,
        description="Vestiarios moi sucios",
    )
    notify_staff_new_incident(inc)
    inc.refresh_from_db()
    order = inc.work_orders.get()
    assert order.kind == "cleaning" and inc.status == Incident.Status.WORK_ORDER
    assert Notification.objects.filter(user=cleaner_a, title__contains="limpeza").exists()
    assert Notification.objects.filter(user=admin_a).exists()  # o concello ve todo
    assert not Notification.objects.filter(user=operator_a).exists()


def test_damage_goes_to_maintenance_not_cleaning(hall_a, citizen, cleaner_a, operator_a):
    from apps.incidents.services import notify_staff_new_incident

    inc = Incident.objects.create(
        municipality=hall_a.municipality,
        facility=hall_a,
        reporter=citizen,
        category=Incident.Category.DAMAGE,
        description="Canastra solta",
    )
    notify_staff_new_incident(inc)
    assert not inc.work_orders.exists()
    assert Notification.objects.filter(user=operator_a, title__contains="avaría").exists()
    assert not Notification.objects.filter(user=cleaner_a).exists()


def test_without_cleaning_staff_cleaning_incident_follows_the_old_path(hall_a, citizen):
    from apps.incidents.services import notify_staff_new_incident

    inc = Incident.objects.create(
        municipality=hall_a.municipality,
        facility=hall_a,
        reporter=citizen,
        category=Incident.Category.CLEANING,
        description="Papeleiras cheas",
    )
    notify_staff_new_incident(inc)
    inc.refresh_from_db()
    assert inc.status == Incident.Status.RECEIVED and not inc.work_orders.exists()


def _used_booking(facility, user, hours_ago=2):
    start = timezone.now() - dt.timedelta(hours=hours_ago)
    return Booking.objects.create(
        municipality=facility.municipality,
        facility=facility,
        user=user,
        start=start,
        end=start + dt.timedelta(hours=1),
        status=Booking.Status.USED,
        price_cents=0,
    )


def test_start_state_and_closing_checklist_have_the_cleaning_tag(hall_a, citizen, cleaner_a):
    from apps.bookings.services import submit_closing_checklist, submit_start_state

    b = _used_booking(hall_a, citizen)
    inc = submit_start_state(b, ok=False, notes="Lixo na pista", cleaning=True)
    assert inc.category == "cleaning" and inc.work_orders.get().kind == "cleaning"
    b2 = _used_booking(hall_a, citizen, hours_ago=5)
    inc2 = submit_closing_checklist(b2, True, None, True, needs_cleaning=True)
    assert inc2.category == "cleaning" and inc2.work_orders.get().kind == "cleaning"


def test_bad_rating_dirty_and_broken_splits_cleaning_and_maintenance(hall_a, citizen, cleaner_a):
    from apps.bookings.ratings import save_rating

    b = _used_booking(hall_a, citizen)
    rating = save_rating(b, "bad", ["lights_broken", "dirty"], create_incident=True)
    assert rating.incident.category == "lighting" and not rating.incident.work_orders.exists()
    order = WorkOrder.objects.get(kind="cleaning", facility=hall_a, incident__isnull=True)
    assert "Sucia" in order.title


def test_admin_can_assign_an_incident_to_cleaning_staff(
    client, hall_a, citizen, cleaner_a, admin_a
):
    inc = Incident.objects.create(
        municipality=hall_a.municipality,
        facility=hall_a,
        reporter=citizen,
        category=Incident.Category.OTHER,
        description="Restos de pintura no chan",
    )
    from apps.incidents.services import create_work_order

    order = create_work_order(inc, admin_a, assigned_to=cleaner_a)
    assert order.kind == "cleaning"


# ---------------------------------------------------------------------------
# Concello: páxina, QR imprimible e exportación
def test_manage_page_qr_and_exports(client, hall_a, hall_zones, cleaner_a, admin_a):
    for z in hall_zones.values():
        cleaning.record(
            facility=hall_a,
            user=cleaner_a,
            zone=z,
            done_labels=["Chan fregado"],
            all_labels=["Chan fregado", "Papeleiras baleiradas"],
        )
    client.force_login(admin_a)
    html = client.get(f"{C}/xestion/limpeza/").content.decode()
    assert "Limpezas de Proba, S. L." in html and "Aseos" in html
    qr = client.get(f"{C}/xestion/limpeza/zona/{hall_zones['Aseos'].pk}/qr/").content.decode()
    assert "<svg" in qr and hall_zones["Aseos"].token in qr
    today = timezone.localdate()
    base = f"{C}/xestion/limpeza/rexistro/?x-start={today - dt.timedelta(days=7)}&x-end={today}"
    csv = client.get(base + "&x-fmt=csv")
    body = csv.content.decode("utf-8-sig")
    assert csv["Content-Type"].startswith("text/csv")
    assert "empresa" in body and "Limpezas de Proba" in body and "Papeleiras baleiradas" in body
    ods = client.get(base + "&x-fmt=ods")
    assert ods["Content-Type"] == "application/vnd.oasis.opendocument.spreadsheet"
    assert ods.content[:2] == b"PK"
    pdf = client.get(base + f"&x-fmt=pdf&x-facility={hall_a.pk}")
    assert pdf["Content-Type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
    assert b"Rexistro de limpeza" in pdf.content


def test_pdf_export_spans_several_pages(hall_a, hall_zones, cleaner_a, muni_a):
    zone = hall_zones["Aseos"]
    for i in range(120):
        cleaning.record(
            facility=hall_a, user=cleaner_a, zone=zone, at=timezone.now() - dt.timedelta(hours=i)
        )
    today = timezone.localdate()
    pdf = cleaning.export_pdf(muni_a, today - dt.timedelta(days=7), today)
    assert b"/Count 1 " not in pdf and b"/Type /Pages" in pdf
    assert pdf.count(b"/Type /Page ") >= 3


def test_export_rejects_backwards_dates(client, admin_a):
    client.force_login(admin_a)
    r = client.get(f"{C}/xestion/limpeza/rexistro/?x-start=2026-10-10&x-end=2026-10-01&x-fmt=csv")
    assert r.status_code == 302


def test_staff_page_saves_the_company(client, admin_a, muni_a):
    client.force_login(admin_a)
    client.post(
        f"{C}/xestion/persoal/",
        {"email": "nova-limpeza@example.org", "role": "cleaning", "company": "Brillo, S. L."},
    )
    m = Membership.objects.get(user__email="nova-limpeza@example.org")
    assert m.role == "cleaning" and m.company == "Brillo, S. L."
