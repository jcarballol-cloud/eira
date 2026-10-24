# SPDX-License-Identifier: EUPL-1.2
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import Municipality


class Notification(models.Model):
    class Level(models.TextChoices):
        INFO = "info", _("Información")
        SUCCESS = "success", _("Confirmación")
        WARNING = "warning", _("Aviso")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    municipality = models.ForeignKey(Municipality, null=True, blank=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=300, blank=True)
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.INFO)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    channels = models.CharField(max_length=60, blank=True)  # canles polas que se enviou
    # v4: avisos do concello (categoría para filtrar na app)
    notice = models.ForeignKey(
        "Notice", null=True, blank=True, on_delete=models.CASCADE, related_name="deliveries"
    )
    category = models.CharField(max_length=12, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("aviso")
        verbose_name_plural = _("avisos")


class PushSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    endpoint = models.URLField(max_length=500, unique=True)
    keys = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


# ---------- v4: avisos do concello ----------
class Category(models.TextChoices):
    CLOSURE = "closure", _("Peches")
    ALERT = "alert", _("Alertas")
    SCHEDULE = "schedule", _("Horarios")
    ACTIVITY = "activity", _("Actividades e inscricións")
    EVENT = "event", _("Festas e eventos")
    NEWS = "news", _("Novidades")


# Base xurídica por categoría (docs/rxpd/avisos.md). «service»: información necesaria para o
# servizo que a persoa usa (art. 6.1.e, e 6.1.b se afecta a unha reserva súa); «info»: comunicacións
# informativas, só con consentimento (art. 6.1.a).
SERVICE, INFO = "service", "info"
CATEGORY_BASIS = {
    Category.CLOSURE: SERVICE,
    Category.ALERT: SERVICE,
    Category.SCHEDULE: INFO,
    Category.ACTIVITY: INFO,
    Category.EVENT: INFO,
    Category.NEWS: INFO,
}
CATEGORY_ICON = {
    Category.CLOSURE: "lock",
    Category.ALERT: "alert",
    Category.SCHEDULE: "clock",
    Category.ACTIVITY: "users",
    Category.EVENT: "star",
    Category.NEWS: "bell",
}
CHANNELS = ("app", "email", "telegram", "push")


class Notice(models.Model):
    """Aviso que redacta o concello e que se envía a un público e por unhas canles."""

    class Audience(models.TextChoices):
        ALL = "all", _("Toda a veciñanza")
        FACILITY = "facility", _("Quen ten reserva nunha instalación")
        OUTDOOR = "outdoor", _("Quen ten reserva nas instalacións descubertas")
        ACTIVITY = "activity", _("Persoas inscritas nunha actividade")
        PARISH = "parish", _("Quen reserva nunha parroquia")

    municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, related_name="notices")
    category = models.CharField(_("categoría"), max_length=12, choices=Category.choices)
    title = models.CharField(_("título"), max_length=120)
    body = models.TextField(_("texto"), max_length=1500)
    url = models.CharField(_("ligazón (opcional)"), max_length=300, blank=True)
    audience = models.CharField(
        _("destinatarios"), max_length=10, choices=Audience.choices, default=Audience.ALL
    )
    facility = models.ForeignKey(
        "facilities.Facility",
        verbose_name=_("instalación"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    activity = models.ForeignKey(
        "activities.Activity",
        verbose_name=_("actividade"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    parish = models.ForeignKey(
        "facilities.Parish",
        verbose_name=_("parroquia"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    window_start = models.DateTimeField(_("desde"), null=True, blank=True)
    window_end = models.DateTimeField(_("ata"), null=True, blank=True)
    cancel_bookings = models.BooleanField(_("cancelar as reservas afectadas"), default=False)
    channels = models.JSONField(_("canles"), default=list)  # app, email, telegram, push, channel
    publish_at = models.DateTimeField(_("enviar o"), null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    recipients = models.PositiveIntegerField(default=0)
    cancelled = models.PositiveIntegerField(default=0)
    sent_counts = models.JSONField(default=dict)  # {"app": n, "email": n, ...}

    class Meta:
        ordering = ["-publish_at", "-created_at"]
        verbose_name = _("aviso do concello")
        verbose_name_plural = _("avisos do concello")

    def __str__(self):
        return self.title

    @property
    def basis(self):
        return CATEGORY_BASIS[self.category]

    @property
    def is_scheduled(self):
        return self.sent_at is None


class NoticePreference(models.Model):
    """Preferencias dunha persoa cos avisos dun concello: consentimento para as comunicacións
    informativas e matriz categoría × canle."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notice_prefs"
    )
    municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, related_name="+")
    comms_consent_at = models.DateTimeField(null=True, blank=True)
    matrix = models.JSONField(default=dict)  # {categoría: [canles]}; sen clave = todas

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "municipality"], name="uniq_notice_pref")
        ]

    def channels_for(self, category):
        return set(self.matrix.get(category, CHANNELS))


class TelegramLink(models.Model):
    """Código dun só uso para vincular o bot persoal de Telegram coa conta (caduca en 30 min)."""

    TTL_MINUTES = 30
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="telegram_links"
    )
    code = models.CharField(max_length=16, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
