# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · Seguridade: alertas, protocolo de accidente, rexistro de accidentes (A) e escalado do
peche sen confirmar coa lista de persoas responsables (B)."""

import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import TenantModel

# Plantilla por defecto do protocolo (A). Cada concello pode cambiala e cada instalación tamén.
DEFAULT_PROTOCOL = {
    "protect": _(
        "Protexe a persoa e a zona. Se hai dúbida dunha lesión no pescozo ou nas costas, non a "
        "movas. Fálalle con calma e abrígaa."
    ),
    "call": _(
        "Se é grave (non responde, respira mal, sangra moito ou deu un golpe forte na cabeza), "
        "chama ao 112 e segue as súas instrucións."
    ),
    "aed": _(
        "Se non responde e non respira con normalidade, pide que traian o DESA e comeza as "
        "compresións se o 112 cho indica."
    ),
    "notify": _(
        "Ao pulsar «Accidente deportivo» avisamos ao momento á persoa responsable do concello."
    ),
    "register": _(
        "Cando a situación estea controlada, rexistra o accidente. Só uns datos básicos: nunca "
        "diagnósticos nin datos de saúde."
    ),
}
PROTOCOL_STEPS = ("protect", "call", "aed", "notify", "register")


class AccidentProtocol(TenantModel):
    """Protocolo de accidente paso a paso. Sen instalación = plantilla do concello."""

    facility = models.OneToOneField(
        "facilities.Facility",
        verbose_name=_("instalación"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="accident_steps",
    )
    protect = models.TextField(_("1. Protexer"), default=DEFAULT_PROTOCOL["protect"])
    call = models.TextField(_("2. Chamar ao 112 se é grave"), default=DEFAULT_PROTOCOL["call"])
    aed = models.TextField(_("3. DESA"), default=DEFAULT_PROTOCOL["aed"])
    notify = models.TextField(
        _("4. Avisar á persoa responsable"), default=DEFAULT_PROTOCOL["notify"]
    )
    register = models.TextField(_("5. Rexistrar o accidente"), default=DEFAULT_PROTOCOL["register"])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("protocolo de accidente")
        verbose_name_plural = _("protocolos de accidente")

    def steps(self):
        return [(key, getattr(self, key)) for key in PROTOCOL_STEPS]


class ResponsibleContact(TenantModel):
    """Lista de persoas responsables designadas polo concello, por orde e horario
    (p. ex. conserxe de 8 a 22 h; persoa de garda fóra de horario)."""

    order = models.PositiveSmallIntegerField(_("orde"), default=1)
    name = models.CharField(_("nome ou posto"), max_length=120)
    role_label = models.CharField(
        _("función"), max_length=120, blank=True, help_text=_("P. ex. «Conserxe»")
    )
    phone = models.CharField(_("teléfono"), max_length=20, blank=True)
    email = models.EmailField(_("correo"), blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("conta en Eira"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_("Opcional: recibe tamén o aviso na app."),
    )
    from_time = models.TimeField(_("desde"), null=True, blank=True)
    until_time = models.TimeField(
        _("ata"),
        null=True,
        blank=True,
        help_text=_("Baleiro = todo o día. Pode pasar da medianoite."),
    )
    active = models.BooleanField(_("activa"), default=True)
    # v1.5 · B: p. ex. a conserxe dunha instalación: recibe as alertas desa instalación no seu horario
    facility = models.ForeignKey(
        "facilities.Facility",
        verbose_name=_("instalación"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
        help_text=_("Baleiro = todo o concello. P. ex., conserxe só desta instalación."),
    )

    class Meta:
        verbose_name = _("persoa responsable")
        verbose_name_plural = _("persoas responsables")
        ordering = ["order", "pk"]

    def __str__(self):
        return f"{self.name} ({self.hours_label()})"

    def covers(self, moment):
        """Está de servizo á hora local de `moment`?"""
        if not self.active:
            return False
        if self.from_time is None or self.until_time is None:
            return True
        t = timezone.localtime(moment).time()
        if self.from_time <= self.until_time:
            return self.from_time <= t < self.until_time
        return t >= self.from_time or t < self.until_time  # cruza a medianoite

    def hours_label(self):
        if self.from_time is None or self.until_time is None:
            return str(_("todo o día"))
        return f"{self.from_time:%H:%M}–{self.until_time:%H:%M}"


class Alert(TenantModel):
    """Alerta: accidente deportivo ou emerxencia de seguridade. Avisa ao momento e xera unha
    incidencia de prioridade máxima para que mantemento revise a instalación."""

    class Kind(models.TextChoices):
        ACCIDENT = "accident", _("Accidente deportivo")
        SECURITY = "security", _("Emerxencia de seguridade")

    class Origin(models.TextChoices):
        APP = "app", _("App da veciñanza")
        BOOKING = "booking", _("Pantalla da reserva")
        MONITOR = "monitor", _("Tableta da persoa monitora")
        # v1.5 · B: Alerta en todos os perfís
        OPERATOR = "operator", _("App de mantemento")
        CLEANING = "cleaning", _("App de limpeza")
        ADMIN = "admin", _("Administración do concello")

    kind = models.CharField(_("tipo"), max_length=10, choices=Kind.choices)
    origin = models.CharField(max_length=10, choices=Origin.choices, default=Origin.APP)
    facility = models.ForeignKey(
        "facilities.Facility",
        verbose_name=_("instalación"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="alerts",
    )
    booking = models.ForeignKey(
        "bookings.Booking", null=True, blank=True, on_delete=models.SET_NULL, related_name="alerts"
    )
    session = models.ForeignKey(
        "activities.Session", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    incident = models.ForeignKey(
        "incidents.Incident", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    notified = models.JSONField(default=list, blank=True)  # nomes/postos avisados (sen datos)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = _("alerta")
        verbose_name_plural = _("alertas")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} · {self.facility or '—'}"


class AccidentReport(TenantModel):
    """Rexistro de accidentes con datos mínimos: sen diagnósticos nin datos clínicos.

    Só o ven a administración do concello e a persoa delegada de protección de datos (DPD).
    Consérvase o prazo que configure o concello (ver docs/rxpd/matriz.md)."""

    class Kind(models.TextChoices):
        FALL = "fall", _("Caída")
        HIT = "hit", _("Golpe")
        MUSCLE = "muscle", _("Lesión muscular")
        OTHER = "other", _("Outro")

    class Severity(models.TextChoices):
        MILD = "mild", _("Leve")
        CARE = "care", _("Require atención")
        EMERGENCY = "emergency", _("112")

    class ReporterRole(models.TextChoices):
        USER = "user", _("Persoa usuaria ou acompañante")
        MONITOR = "monitor", _("Persoa monitora")
        STAFF = "staff", _("Persoal do concello")
        OTHER = "other", _("Outra persoa")

    facility = models.ForeignKey(
        "facilities.Facility",
        verbose_name=_("instalación"),
        on_delete=models.CASCADE,
        related_name="accidents",
    )
    occurred_at = models.DateTimeField(_("data e hora"), default=timezone.now)
    kind = models.CharField(_("tipo xeral"), max_length=10, choices=Kind.choices)
    severity = models.CharField(_("gravidade percibida"), max_length=10, choices=Severity.choices)
    called_112 = models.BooleanField(_("chamouse ao 112"), default=False)
    reporter_role = models.CharField(
        _("quen o comunica"), max_length=10, choices=ReporterRole.choices
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    alert = models.ForeignKey(
        Alert, null=True, blank=True, on_delete=models.SET_NULL, related_name="accidents"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    facility_related = models.BooleanField(
        _("a instalación tivo que ver"),
        null=True,
        blank=True,
        help_text=_("Resultado da revisión de mantemento (incidencia vinculada)."),
    )

    class Meta:
        verbose_name = _("accidente")
        verbose_name_plural = _("rexistro de accidentes")
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"{self.occurred_at:%d/%m/%Y} · {self.facility} · {self.get_kind_display()}"


def new_token():
    return secrets.token_urlsafe(18)


class ClosingEscalation(TenantModel):
    """B · Peche sen confirmar: recordatorios e aviso á persoa responsable.

    A policía nunca se avisa soa: o aviso á persoa responsable leva un botón «Contactar coa
    Policía Local» para que decida unha persoa, e cada contacto queda rexistrado."""

    class Stage(models.IntegerChoices):
        WAITING = 0, _("Pendente")
        FIRST = 1, _("Primeiro recordatorio")
        SECOND = 2, _("Segundo recordatorio")
        ESCALATED = 3, _("Aviso á persoa responsable")

    class Outcome(models.TextChoices):
        CLOSED_BY_USER = "user", _("A persoa completou a lista de peche")
        DOOR_CLOSED = "door", _("A pechadura informa de que a porta está pechada")
        CHECKED = "checked", _("Revisado pola persoa responsable")

    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.CASCADE, related_name="closing_escalation"
    )
    stage = models.IntegerField(choices=Stage.choices, default=Stage.WAITING)
    first_at = models.DateTimeField(null=True, blank=True)
    second_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    contact = models.ForeignKey(
        ResponsibleContact, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    door_state = models.CharField(max_length=10, blank=True)  # closed | open | ""
    token = models.CharField(max_length=40, default=new_token, unique=True, editable=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=10, choices=Outcome.choices, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    note = models.CharField(_("nota"), max_length=300, blank=True)
    counted_as_breach = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("peche sen confirmar")
        verbose_name_plural = _("peches sen confirmar")
        ordering = ["-pk"]

    @property
    def is_open(self):
        return self.resolved_at is None


class PoliceContact(TenantModel):
    """Cada vez que unha persoa decide contactar coa Policía Local queda rexistrado."""

    escalation = models.ForeignKey(
        ClosingEscalation, null=True, blank=True, on_delete=models.CASCADE, related_name="police"
    )
    phone = models.CharField(max_length=20)
    by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    by_contact = models.ForeignKey(
        ResponsibleContact, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _("contacto coa Policía Local")
        verbose_name_plural = _("contactos coa Policía Local")
        ordering = ["-at"]
