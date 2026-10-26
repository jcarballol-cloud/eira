# SPDX-License-Identifier: EUPL-1.2
"""Mantemento preventivo (plans e tarefas periódicas) e ordes de traballo."""

import datetime as dt

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.facilities.models import Facility
from apps.tenants.models import TenantModel


class Frequency(models.TextChoices):
    DAILY = "daily", _("Diaria")
    WEEKLY = "weekly", _("Semanal")
    MONTHLY = "monthly", _("Mensual")
    YEARLY = "yearly", _("Anual")


class MaintenancePlan(TenantModel):
    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, related_name="maintenance_plans"
    )
    name = models.CharField(_("nome"), max_length=120)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("plan de mantemento")
        verbose_name_plural = _("plans de mantemento")

    def __str__(self):
        return f"{self.facility}: {self.name}"


class MaintenanceTask(models.Model):
    plan = models.ForeignKey(MaintenancePlan, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(_("tarefa"), max_length=160)
    frequency = models.CharField(_("frecuencia"), max_length=10, choices=Frequency.choices)
    checklist = models.TextField(_("checklist (unha liña por punto)"), blank=True)
    start_date = models.DateField(_("data de inicio"), default=dt.date.today)
    estimated_minutes = models.PositiveIntegerField(default=30)

    class Meta:
        verbose_name = _("tarefa periódica")
        verbose_name_plural = _("tarefas periódicas")

    def __str__(self):
        return self.title

    def checklist_items(self):
        return [line.strip() for line in self.checklist.splitlines() if line.strip()]

    def occurs_on(self, day):
        if day < self.start_date:
            return False
        if self.frequency == Frequency.DAILY:
            return True
        if self.frequency == Frequency.WEEKLY:
            return day.weekday() == self.start_date.weekday()
        if self.frequency == Frequency.MONTHLY:
            return day.day == min(self.start_date.day, 28)
        return (day.month, day.day) == (self.start_date.month, min(self.start_date.day, 28))


class WorkOrder(TenantModel):
    class Status(models.TextChoices):
        OPEN = "open", _("Pendente")
        IN_PROGRESS = "in_progress", _("En curso")
        DONE = "done", _("Pechada")

    facility = models.ForeignKey(
        Facility,
        verbose_name=_("instalación"),
        on_delete=models.CASCADE,
        related_name="work_orders",
    )
    task = models.ForeignKey(
        MaintenanceTask, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders"
    )
    incident = models.ForeignKey(
        "incidents.Incident",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="work_orders",
    )
    title = models.CharField(_("título"), max_length=160)
    description = models.TextField(_("descrición"), blank=True)
    due_date = models.DateField(_("data prevista"), db_index=True)
    status = models.CharField(
        _("estado"), max_length=12, choices=Status.choices, default=Status.OPEN
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("asignada a"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="work_orders",
    )
    checklist_state = models.JSONField(default=list, blank=True)  # [{"label": str, "done": bool}]
    # v5 · H: «Revisión de seguridade inicial Eira» (alta da instalación)
    kind = models.CharField(
        max_length=20,
        choices=[
            ("regular", _("Ordinaria")),
            ("safety_review", _("Revisión de seguridade inicial")),
        ],
        default="regular",
    )
    closing_notes = models.TextField(_("notas de peche"), blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("orde de traballo")
        verbose_name_plural = _("ordes de traballo")
        ordering = ["due_date", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["task", "due_date"],
                name="uniq_task_occurrence",
                condition=models.Q(task__isnull=False),
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return self.status != self.Status.DONE and self.due_date < dt.date.today()


class WorkOrderPhoto(models.Model):
    order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="workorders/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
