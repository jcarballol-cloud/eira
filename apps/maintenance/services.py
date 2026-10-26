# SPDX-License-Identifier: EUPL-1.2
import datetime as dt

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import audit

from .models import MaintenanceTask, WorkOrder


def generate_orders(days=14, today=None, municipality=None):
    """Xera (de forma idempotente) as ordes das tarefas periódicas nos próximos `days` días."""
    today = today or timezone.localdate()
    tasks = MaintenanceTask.objects.filter(plan__active=True).select_related(
        "plan", "plan__facility", "zone"
    )
    if municipality is not None:
        tasks = tasks.filter(plan__municipality=municipality)
    created = 0
    for task in tasks:
        cleaning = task.kind == "cleaning"
        if cleaning and task.zone_id and not task.zone.active:
            continue
        times = task.occurrences_per_day
        for i in range(days):
            day = today + dt.timedelta(days=i)
            if not task.occurs_on(day):
                continue
            for slot in range(times):
                if WorkOrder.objects.filter(task=task, due_date=day, slot=slot).exists():
                    continue
                title = task.title + (f" ({slot + 1}/{times})" if times > 1 else "")
                try:
                    with transaction.atomic():
                        WorkOrder.objects.create(
                            municipality=task.plan.municipality,
                            facility=task.plan.facility,
                            task=task,
                            title=title,
                            due_date=day,
                            slot=slot,
                            kind="cleaning" if cleaning else "regular",
                            zone=task.zone if cleaning else None,
                            checklist_state=[
                                {"label": item, "done": False} for item in task.checklist_items()
                            ],
                        )
                        created += 1
                except IntegrityError:
                    pass
    return created


def update_checklist(order, done_indexes):
    state = order.checklist_state or []
    for i, item in enumerate(state):
        item["done"] = i in done_indexes
    order.checklist_state = state
    if order.status == WorkOrder.Status.OPEN and done_indexes:
        order.status = WorkOrder.Status.IN_PROGRESS
    order.save(update_fields=["checklist_state", "status"])


def close_order(order, by=None, notes="", log=True, photo=None):
    from apps.incidents.models import Incident
    from apps.incidents.services import resolve

    order.status = WorkOrder.Status.DONE
    order.closed_at = timezone.now()
    order.closing_notes = notes
    order.save(update_fields=["status", "closed_at", "closing_notes"])
    audit("workorder.close", by, order.municipality, order)
    if order.kind == "cleaning" and log:
        # v1.1: pechar unha orde de limpeza tamén queda no rexistro de limpeza
        from .cleaning import record
        from .models import CleaningLog

        state = order.checklist_state or []
        record(
            facility=order.facility,
            user=by,
            zone=order.zone,
            done_labels=[i["label"] for i in state if i.get("done")],
            all_labels=[i["label"] for i in state],
            notes=notes,
            photo=photo,
            order=order,
            source=CleaningLog.Source.ORDER,
        )
    if order.incident_id and order.incident.status != Incident.Status.RESOLVED:
        resolve(order.incident, by=by, note=notes)
    return order
