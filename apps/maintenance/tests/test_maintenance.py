# SPDX-License-Identifier: EUPL-1.2
import datetime as dt

import pytest

from apps.maintenance.models import Frequency, MaintenanceTask, WorkOrder
from apps.maintenance.services import generate_orders

pytestmark = pytest.mark.django_db


def test_template_creates_plan(padel_a):
    assert padel_a.maintenance_plans.get().tasks.count() == 2


def test_generation_is_idempotent(padel_a):
    today = dt.date(2026, 11, 2)  # luns
    n = generate_orders(days=14, today=today)
    assert n > 0
    assert generate_orders(days=14, today=today) == 0
    assert WorkOrder.objects.filter(task__isnull=False).count() == n


@pytest.mark.parametrize(
    "freq, start, day, expected",
    [
        (Frequency.DAILY, dt.date(2026, 1, 1), dt.date(2026, 3, 3), True),
        (Frequency.WEEKLY, dt.date(2026, 11, 2), dt.date(2026, 11, 9), True),
        (Frequency.WEEKLY, dt.date(2026, 11, 2), dt.date(2026, 11, 10), False),
        (Frequency.MONTHLY, dt.date(2026, 1, 31), dt.date(2026, 2, 28), True),
        (Frequency.YEARLY, dt.date(2026, 3, 5), dt.date(2027, 3, 5), True),
        (Frequency.DAILY, dt.date(2026, 5, 1), dt.date(2026, 4, 30), False),
    ],
)
def test_occurrences(freq, start, day, expected):
    assert MaintenanceTask(title="x", frequency=freq, start_date=start).occurs_on(day) is expected


def test_operator_closes_order_with_checklist(client, operator_a, padel_a):
    generate_orders(days=3)
    order = WorkOrder.objects.first()
    client.force_login(operator_a)
    assert client.get(f"/c/concello-a/operario/orde/{order.pk}/").status_code == 200
    r = client.post(
        f"/c/concello-a/operario/orde/{order.pk}/",
        {"action": "close", "done": ["0"], "closing_notes": "Feito"},
    )
    assert r.status_code == 302
    order.refresh_from_db()
    assert order.status == "done" and order.checklist_state[0]["done"]


def test_offline_sync_replay_is_idempotent(client, operator_a, padel_a):
    """A cola sen conexión reenvía co header X-Eira-Sync; un segundo envío non rompe nada."""
    generate_orders(days=3)
    order = WorkOrder.objects.first()
    client.force_login(operator_a)
    url = f"/c/concello-a/operario/orde/{order.pk}/"
    assert client.post(url, {"action": "close"}, HTTP_X_EIRA_SYNC="1").status_code == 204
    assert client.post(url, {"action": "close"}, HTTP_X_EIRA_SYNC="1").status_code == 409


def test_shared_calendar(client, admin_a, padel_a):
    generate_orders(days=7)
    client.force_login(admin_a)
    assert client.get("/c/concello-a/xestion/mantemento/calendario/").status_code == 200
    assert (
        client.get("/c/concello-a/operario/calendario/").status_code == 403
    )  # a app do operario é só súa


def test_operator_day_filter_tomorrow(client, operator_a, padel_a):
    """v4.1: filtro «Hoxe» / «Mañá»; sen ordes mañá vese o estado baleiro de mantemento."""
    from django.utils import timezone

    tomorrow = timezone.localdate() + dt.timedelta(days=1)
    WorkOrder.objects.create(
        municipality=padel_a.municipality,
        facility=padel_a,
        title="Revisar redes",
        due_date=tomorrow,
    )
    client.force_login(operator_a)
    html = client.get("/c/concello-a/operario/?dia=manha").content.decode()
    assert (
        "Revisar redes" in html
        and "Mañá está todo ao día" not in html
        and 'aria-current="page">Mañá' in html
    )
    WorkOrder.objects.filter(due_date=tomorrow).update(status=WorkOrder.Status.DONE)
    html = client.get("/c/concello-a/operario/?dia=manha").content.decode()
    assert "Mañá está todo ao día" in html and "baleiro-mantemento" in html
    html = client.get("/c/concello-a/operario/").content.decode()
    assert 'aria-current="page">Hoxe' in html and "Revisar redes" not in html
