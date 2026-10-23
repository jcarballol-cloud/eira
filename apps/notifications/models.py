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

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    municipality = models.ForeignKey(Municipality, null=True, blank=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=300, blank=True)
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.INFO)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    channels = models.CharField(max_length=60, blank=True)  # canles polas que se enviou

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("aviso")
        verbose_name_plural = _("avisos")


class PushSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.URLField(max_length=500, unique=True)
    keys = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
