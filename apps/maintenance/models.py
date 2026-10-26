# SPDX-License-Identifier: EUPL-1.2
"""Mantemento preventivo (plans e tarefas periódicas) e ordes de traballo.

v1.1: o mesmo motor serve para a limpeza (tarefas de tipo «limpeza» por zona, QR por zona e
rexistro de limpeza)."""

import datetime as dt
import secrets

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.facilities.models import Facility
from apps.tenants.models import TenantModel


class Frequency(models.TextChoices):
    SEVERAL = "several", _("Varias veces ao día")  # v1.1 (limpeza)
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


class TaskKind(models.TextChoices):
    MAINTENANCE = "maintenance", _("Mantemento")
    CLEANING = "cleaning", _("Limpeza")


class CleaningZone(TenantModel):
    """v1.1 · Zona de limpeza dunha instalación (vestiarios, aseos, pista…) co seu QR."""

    class Kind(models.TextChoices):
        CHANGING = "changing", _("Vestiarios")
        TOILETS = "toilets", _("Aseos")
        COURT = "court", _("Pista")
        STANDS = "stands", _("Bancadas")
        STORAGE = "storage", _("Almacén")
        POOL = "pool", _("Vaso e praia da piscina")
        OTHER = "other", _("Outra")

    facility = models.ForeignKey(
        Facility,
        verbose_name=_("instalación"),
        on_delete=models.CASCADE,
        related_name="cleaning_zones",
    )
    name = models.CharField(_("nome"), max_length=120)
    kind = models.CharField(_("tipo"), max_length=12, choices=Kind.choices, default=Kind.OTHER)
    max_hours = models.PositiveSmallIntegerField(
        _("tempo máximo sen limpar (horas)"),
        default=24,
        help_text=_("Se pasa máis tempo sen rexistrar unha limpeza, avísase ao concello."),
    )
    token = models.CharField(max_length=24, unique=True, editable=False)
    active = models.BooleanField(_("activa"), default=True)
    alerted_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("zona de limpeza")
        verbose_name_plural = _("zonas de limpeza")
        ordering = ["facility__name", "name"]

    def __str__(self):
        return f"{self.facility.name} · {self.name}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(12)
        super().save(*args, **kwargs)

    def last_log(self):
        return self.logs.order_by("-done_at").first()

    def checklist_items(self):
        """Puntos das tarefas de limpeza desta zona (sen repetir); se non hai, os do tipo."""
        items = []
        for task in self.tasks.filter(plan__active=True):
            for item in task.checklist_items():
                if item not in items:
                    items.append(item)
        if not items:
            from .cleaning import DEFAULT_CHECKLIST

            items = [str(i) for i in DEFAULT_CHECKLIST.get(self.kind, DEFAULT_CHECKLIST["other"])]
        return items


class MaintenanceTask(models.Model):
    plan = models.ForeignKey(MaintenancePlan, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(_("tarefa"), max_length=160)
    frequency = models.CharField(_("frecuencia"), max_length=10, choices=Frequency.choices)
    checklist = models.TextField(_("checklist (unha liña por punto)"), blank=True)
    start_date = models.DateField(_("data de inicio"), default=dt.date.today)
    estimated_minutes = models.PositiveIntegerField(default=30)
    # v1.1 · limpeza
    kind = models.CharField(
        _("tipo de tarefa"), max_length=12, choices=TaskKind.choices, default=TaskKind.MAINTENANCE
    )
    zone = models.ForeignKey(
        CleaningZone,
        verbose_name=_("zona"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    times_per_day = models.PositiveSmallIntegerField(
        _("veces ao día"), default=1, help_text=_("Só para «Varias veces ao día».")
    )

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
        if self.frequency in (Frequency.DAILY, Frequency.SEVERAL):
            return True
        if self.frequency == Frequency.WEEKLY:
            return day.weekday() == self.start_date.weekday()
        if self.frequency == Frequency.MONTHLY:
            return day.day == min(self.start_date.day, 28)
        return (day.month, day.day) == (self.start_date.month, min(self.start_date.day, 28))

    @property
    def occurrences_per_day(self):
        return max(1, self.times_per_day) if self.frequency == Frequency.SEVERAL else 1

    @property
    def frequency_label(self):
        if self.frequency == Frequency.SEVERAL:
            return _("%(n)s veces ao día") % {"n": self.occurrences_per_day}
        return self.get_frequency_display()


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
            ("cleaning", _("Limpeza")),  # v1.1
        ],
        default="regular",
    )
    # v1.1 · limpeza: zona e quenda (0, 1, 2… nas tarefas de varias veces ao día)
    zone = models.ForeignKey(
        CleaningZone,
        verbose_name=_("zona"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    slot = models.PositiveSmallIntegerField(default=0)
    closing_notes = models.TextField(_("notas de peche"), blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("orde de traballo")
        verbose_name_plural = _("ordes de traballo")
        ordering = ["due_date", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["task", "due_date", "slot"],
                name="uniq_task_occurrence_slot",
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


class CleaningLog(TenantModel):
    """v1.1 · Rexistro de limpeza: quen, cando, que tarefas e foto opcional.

    Substitúe a folla de papel da parede. Créase ao escanear o QR da zona ou ao pechar unha
    orde de limpeza. Garda o nome e a empresa no momento do rexistro, para que o histórico non
    cambie se a persoa deixa o servizo."""

    class Source(models.TextChoices):
        QR = "qr", _("QR da zona")
        ORDER = "order", _("Orde de limpeza")

    facility = models.ForeignKey(
        Facility,
        verbose_name=_("instalación"),
        on_delete=models.CASCADE,
        related_name="cleaning_logs",
    )
    zone = models.ForeignKey(
        CleaningZone,
        verbose_name=_("zona"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    by_name = models.CharField(_("persoa"), max_length=120, blank=True)
    company = models.CharField(_("empresa"), max_length=120, blank=True)
    done_at = models.DateTimeField(_("data e hora"), db_index=True)
    items = models.JSONField(default=list, blank=True)  # [{"label": str, "done": bool}]
    notes = models.CharField(_("observacións"), max_length=500, blank=True)
    photo = models.ImageField(_("foto"), upload_to="cleaning/%Y/%m/", blank=True)
    order = models.ForeignKey(
        WorkOrder, null=True, blank=True, on_delete=models.SET_NULL, related_name="cleaning_logs"
    )
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.QR)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("rexistro de limpeza")
        verbose_name_plural = _("rexistros de limpeza")
        ordering = ["-done_at"]

    def __str__(self):
        return f"{self.facility} · {self.zone or '-'} · {self.done_at:%d/%m %H:%M}"

    def done_items(self):
        return [i["label"] for i in self.items if i.get("done")]
