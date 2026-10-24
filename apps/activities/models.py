# SPDX-License-Identifier: EUPL-1.2
"""Escolas e actividades municipais: grupos, inscricións, sesións, asistencia, RPE e probas."""

import datetime as dt

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.facilities.models import Facility
from apps.tenants.models import TenantModel


class Activity(TenantModel):
    name = models.CharField(_("nome"), max_length=120)
    description = models.TextField(_("descrición"), blank=True)
    season = models.CharField(_("tempada"), max_length=20, default="2026-2027")
    is_published = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("actividade")
        verbose_name_plural = _("actividades")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Group(TenantModel):
    class RpeScale(models.TextChoices):
        OMNI = "omni", _("OMNI 0–10 (infancia)")
        BORG = "borg", _("Borg CR-10 (persoas adultas)")

    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="groups")
    name = models.CharField(_("grupo"), max_length=120)
    facility = models.ForeignKey(Facility, null=True, blank=True, on_delete=models.SET_NULL)
    monitor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="groups_led",
    )
    min_age = models.PositiveIntegerField(_("idade mínima"), default=0)
    max_age = models.PositiveIntegerField(_("idade máxima"), default=120)
    places = models.PositiveIntegerField(_("prazas"), default=15)
    fee_cents = models.PositiveIntegerField(_("cota (céntimos)"), default=0)
    weekdays = models.CharField(_("días (0=luns)"), max_length=20, default="0,2")
    start_time = models.TimeField(_("hora de inicio"))
    duration_minutes = models.PositiveIntegerField(_("duración (min)"), default=60)
    rpe_scale = models.CharField(max_length=8, choices=RpeScale.choices, default=RpeScale.BORG)

    class Meta:
        verbose_name = _("grupo")
        verbose_name_plural = _("grupos")
        ordering = ["activity__name", "name"]

    def __str__(self):
        return f"{self.activity} · {self.name}"

    def weekday_list(self):
        return [int(x) for x in self.weekdays.split(",") if x.strip().isdigit()]

    def enrolled(self):
        return self.enrollments.filter(status=Enrollment.Status.ACTIVE)

    @property
    def free_places(self):
        return max(0, self.places - self.enrolled().count())


class Enrollment(TenantModel):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", _("Pendente de pagamento")
        ACTIVE = "active", _("Inscrita")
        WAITLIST = "waitlist", _("Lista de espera")
        CANCELLED = "cancelled", _("Baixa")

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="enrollments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    dependent = models.ForeignKey(
        "accounts.Dependent",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT)
    # Dato da inscrición, que achega o concello (padrón ou folla de inscrición), non a monitora.
    # A tableta só amosa nome + primeiro apelido; o nome completo, só na administración.
    surnames = models.CharField(_("apelidos (inscrición)"), max_length=80, blank=True)
    paid_cents = models.PositiveIntegerField(default=0)
    payment_reference = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Seudónimo estable para o observatorio: nunca se expón o nome nin o id
    pseudonym = models.CharField(max_length=16, blank=True, db_index=True)

    class Meta:
        verbose_name = _("inscrición")
        verbose_name_plural = _("inscricións")
        ordering = ["created_at"]

    @property
    def participant_surnames(self):
        return self.surnames

    @property
    def participant_name(self):
        if self.dependent:
            return self.dependent.first_name
        return self.user.display_name or self.user.email.split("@")[0] if self.user else "—"

    @property
    def can_appear_in_photos(self):
        if self.dependent:
            return self.dependent.can_appear_in_photos()
        return bool(self.user and self.user.photo_consent)

    @property
    def participant_age(self):
        if self.dependent:
            return self.dependent.age
        return self.user.age if self.user else None


class PendingParticipant(TenantModel):
    """Persoa que o monitor apunta na pista e que aínda non está inscrita: o concello valídaa."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pendente de validar")
        VALIDATED = "validated", _("Validada")
        REJECTED = "rejected", _("Descartada")

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="pending_participants")
    first_name = models.CharField(_("nome"), max_length=60)
    birth_year = models.PositiveIntegerField(_("ano de nacemento"), null=True, blank=True)
    guardian_email = models.EmailField(_("correo da familia ou da persoa"), blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    resolved_at = models.DateTimeField(null=True, blank=True)
    enrollment = models.ForeignKey(
        Enrollment, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = _("persoa pendente de validar")
        verbose_name_plural = _("persoas pendentes de validar")
        ordering = ["created_at"]

    def __str__(self):
        return self.first_name


class Session(TenantModel):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="sessions")
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["date", "start_time"]
        constraints = [models.UniqueConstraint(fields=["group", "date"], name="uniq_session_day")]

    # v4: o estado depende da hora, non só de se se gardou o esforzo. Antes, gardar o esforzo
    # (ou o seed da demo) marcaba «Pechada» unha sesión que aínda non empezara.
    UPCOMING, OPEN, FINISHED, CLOSED = "upcoming", "open", "finished", "closed"
    STATUS_LABELS = {
        UPCOMING: _("Por empezar"),
        OPEN: _("Aberta"),
        FINISHED: _("Rematada"),
        CLOSED: _("Pechada"),
    }
    # A tableta segue aberta un pouco antes e despois para quen chega cedo ou sae tarde.
    MARGIN = dt.timedelta(minutes=15)

    @property
    def start_dt(self):
        return timezone.make_aware(dt.datetime.combine(self.date, self.start_time))

    @property
    def end_dt(self):
        return self.start_dt + dt.timedelta(minutes=self.duration_minutes)

    def status_at(self, now=None):
        now = now or timezone.now()
        if now < self.start_dt - self.MARGIN:
            return self.UPCOMING
        if now <= self.end_dt + self.MARGIN:
            return self.OPEN
        return self.CLOSED if self.closed_at else self.FINISHED

    @property
    def status(self):
        return self.status_at()

    @property
    def status_label(self):
        return self.STATUS_LABELS[self.status]


class Attendance(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="attendances")
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="attendances")
    present = models.BooleanField(default=False)
    rpe = models.PositiveSmallIntegerField(null=True, blank=True)  # 0–10
    minutes = models.PositiveIntegerField(null=True, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    rpe_at = models.DateTimeField(null=True, blank=True)
    # v4: a asistencia marcouse soa ao rexistrar a saída (non tocara «Entrada»)
    auto_in = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "enrollment"], name="uniq_attendance")
        ]

    @property
    def session_load(self):
        """Carga da sesión (Foster): sRPE × minutos."""
        if self.rpe is None or not self.present:
            return None
        return self.rpe * (self.minutes or self.session.duration_minutes)


class FitnessBattery(TenantModel):
    """Batería de probas xenérica (campos configurables). Sen baremos inventados."""

    name = models.CharField(max_length=120)
    reference = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = _("batería de probas")
        verbose_name_plural = _("baterías de probas")

    def __str__(self):
        return self.name


class FitnessTest(models.Model):
    battery = models.ForeignKey(FitnessBattery, on_delete=models.CASCADE, related_name="tests")
    name = models.CharField(max_length=120)
    unit = models.CharField(max_length=20)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.name} ({self.unit})"


class FitnessResult(models.Model):
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="fitness_results"
    )
    test = models.ForeignKey(FitnessTest, on_delete=models.CASCADE)
    date = models.DateField()
    value = models.DecimalField(max_digits=8, decimal_places=2)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-date"]
