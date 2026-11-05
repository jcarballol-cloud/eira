# SPDX-License-Identifier: EUPL-1.2
"""v5 · A: reservar en concellos próximos da mesma rede (deputación ou mancomunidade) coa
mesma conta, e ver as súas actividades e eventos se a persoa quere."""

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .models import Municipality
from .urlutils import neighbour_required, treverse


def network_of(municipality):
    """Concellos activos da mesma rede, sen o propio."""
    if not municipality or not municipality.region_id:
        return Municipality.objects.none()
    return (
        Municipality.objects.filter(region_id=municipality.region_id, is_active=True)
        .exclude(pk=municipality.pk)
        .order_by("name")
    )


def switcher(user, tenant):
    """Opcións do selector de concello en «Reservar»: o propio e os da rede abertos."""
    from apps.bookings.services import linked_home

    if not getattr(user, "is_authenticated", False) or tenant is None or not tenant.region_id:
        return []
    home = linked_home(user) or tenant
    if home.region_id != tenant.region_id:
        home = tenant
    options = [home] + [m for m in network_of(home) if m.network_open]
    return [
        {"municipality": m, "is_home": m.pk == home.pk, "current": m.pk == tenant.pk}
        for m in options
    ]


@neighbour_required
def nearby(request):
    """«Concellos próximos»: onde podes reservar coa túa conta e en que condicións."""
    from apps.facilities.models import Facility

    home = request.tenant
    rows = []
    for m in network_of(home):
        rows.append(
            {
                "municipality": m,
                "facilities": Facility.objects.for_tenant(m).filter(is_published=True).count(),
                "following": m.slug in (request.user.network_feed or []),
            }
        )
    from apps.analytics.provenance import nearby_for
    from apps.facilities.models import Parish

    return render(
        request,
        "app/nearby.html",
        {
            "rows": rows,
            "region": home.region,
            "nav": "app_home",
            # v1.5 · C: a súa parroquia e as distancias
            "nearby_info": nearby_for(request.user, home),
            "residence_parishes": Parish.objects.filter(municipality=home),
            "residence_towns": network_of(home),
        },
    )


@neighbour_required
@require_POST
def residence(request):
    """v1.5 · C: parroquia ou concello de residencia, voluntario. Nunca GPS."""
    from apps.accounts.models import audit
    from apps.facilities.models import Parish

    value = request.POST.get("residence", "")
    user = request.user
    parish = town = None
    if value[:1] == "p" and value[1:].isdigit():
        parish = Parish.objects.filter(municipality=request.tenant, pk=int(value[1:])).first()
    elif value[:1] == "m" and value[1:].isdigit():
        town = network_of(request.tenant).filter(pk=int(value[1:])).first()
    if value and parish is None and town is None:
        raise Http404
    user.residence_parish, user.residence_municipality = parish, town
    user.save(update_fields=["residence_parish", "residence_municipality"])
    audit("residence.update", user, request.tenant, user, removed=not value)
    messages.success(request, _("Gardado.") if value else _("Borrado: xa non consta onde vives."))
    return redirect(treverse(request.tenant, "app:nearby") + "#onde-estou")


def go(request):
    """Selector de concello (sen JS): redirixe á busca de instalacións do concello escollido."""
    slug = request.GET.get("concello", "")
    target = network_of(request.tenant).filter(slug=slug).first()
    if slug == request.tenant.slug or target is None:
        return redirect(treverse(request.tenant, "tenant_home"))
    return redirect(treverse(target, "tenant_home"))


@neighbour_required
@require_POST
def follow(request):
    """Activa ou desactiva as actividades e eventos dun concello próximo en «Avisos»."""
    slug = request.POST.get("concello", "")
    if not network_of(request.tenant).filter(slug=slug).exists():
        raise Http404
    feed = [s for s in (request.user.network_feed or []) if s != slug]
    if request.POST.get("on") == "1":
        feed.append(slug)
    request.user.network_feed = sorted(set(feed))
    request.user.save(update_fields=["network_feed"])
    messages.success(
        request,
        _("Gardado. Verás as súas actividades e eventos en «Avisos».")
        if request.POST.get("on") == "1"
        else _("Gardado. Xa non verás as súas actividades e eventos."),
    )
    from django.utils.http import url_has_allowed_host_and_scheme

    nxt = request.POST.get("next") or ""
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = treverse(request.tenant, "app:nearby")
    return redirect(nxt)


def network_feed(user, tenant, only=None):
    """Actividades con prazas e avisos públicos (actividades, festas e eventos) dos concellos
    próximos que a persoa escolleu. Non se envía nada: é un taboleiro, coma o do propio concello."""
    from apps.activities.models import Group
    from apps.notifications.models import Category, Notice

    slugs = set(user.network_feed or [])
    towns = [m for m in network_of(tenant) if m.slug in slugs]
    if only:
        towns = [m for m in towns if m.slug == only]
    if not towns:
        return {"towns": [], "notices": [], "groups": []}
    notices = (
        Notice.objects.filter(
            municipality__in=towns,
            audience=Notice.Audience.ALL,
            sent_at__isnull=False,
            category__in=[Category.ACTIVITY, Category.EVENT, Category.NEWS],
        )
        .select_related("municipality")
        .order_by("-sent_at")[:20]
    )
    groups = (
        Group.objects.filter(municipality__in=towns, activity__is_published=True)
        .select_related("municipality", "activity", "facility")
        .order_by("municipality__name", "activity__name", "name")[:20]
    )
    return {"towns": towns, "notices": list(notices), "groups": list(groups), "now": timezone.now()}
