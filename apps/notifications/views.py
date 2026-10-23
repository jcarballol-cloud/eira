# SPDX-License-Identifier: EUPL-1.2
import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.tenants.urlutils import treverse

from .models import Notification, PushSubscription


@login_required
def list_view(request):
    qs = Notification.objects.filter(user=request.user, municipality=request.tenant)[:100]
    return render(request, "notifications/list.html", {"notifications": qs, "nav": "notifications"})


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(user=request.user, municipality=request.tenant, read_at__isnull=True).update(
        read_at=timezone.now()
    )
    if request.headers.get("HX-Request"):
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    return redirect(treverse(request.tenant, "notifications:list"))


@login_required
@require_POST
def subscribe_push(request):
    """Rexistra unha subscrición Web Push (RFC 8030). O envío real vai detrás do adaptador."""
    try:
        data = json.loads(request.body)
        PushSubscription.objects.update_or_create(
            endpoint=data["endpoint"][:500], defaults={"user": request.user, "keys": data.get("keys", {})}
        )
    except (ValueError, KeyError):
        return JsonResponse({"ok": False}, status=400)
    return JsonResponse({"ok": True})
