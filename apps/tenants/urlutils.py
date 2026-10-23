# SPDX-License-Identifier: EUPL-1.2
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse


def treverse(tenant, name, *args):
    """reverse() para URLs dun concello: engade o slug automaticamente."""
    slug = tenant.slug if hasattr(tenant, "slug") else tenant
    return reverse(name, args=[slug, *args])


def tredirect(request, name, *args):
    return redirect(treverse(request.tenant, name, *args))


SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def role_required(*roles):
    """Restrinxe unha vista do concello aos roles indicados (no concello activo).

    A deputación (`region_admin` sen `admin`) entra nos concellos da súa rede en **modo consulta**:
    - só lectura: calquera escritura dá 403 agás nas accións marcadas con `@support_action`;
    - por defecto só ve as vistas sen datos persoais (`@aggregate_view`: indicadores, instalacións…);
    - o resto precisa un **acceso de soporte** autorizado polo concello e vixente (24 h). Cada vista
      queda en AuditLog e o concello recibe un aviso no primeiro uso.
    """

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not (request.roles & set(roles)):
                raise PermissionDenied
            read_only = "region_admin" in request.roles and "admin" not in request.roles
            if read_only:
                if request.method not in SAFE_METHODS and not getattr(
                    view, "support_action", False
                ):
                    raise PermissionDenied
                if not getattr(view, "aggregate_view", False):
                    use_support_access(request)
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def use_support_access(request):
    """403 se a deputación non ten acceso de soporte vixente; se o ten, rexístrao."""
    from django.utils import timezone

    from apps.accounts.models import audit
    from apps.tenants.models import SupportAccess

    region_ids = list(request.user.region_memberships.values_list("region_id", flat=True))
    access = SupportAccess.active_for(request.tenant, region_ids)
    if access is None:
        request.support_denied = True
        raise PermissionDenied("Sen acceso de soporte")
    request.support_access = access
    audit(
        "support.view",
        request.user,
        request.tenant,
        access,
        path=request.path,
        expires_at=access.expires_at.isoformat(),
    )
    if access.first_used_at is None:
        access.first_used_at = timezone.now()
        access.save(update_fields=["first_used_at"])
        notify_support_use(request, access)


def notify_support_use(request, access):
    """Aviso ao persoal administrador do concello: a deputación empezou a ver datos persoais."""
    from django.utils.translation import gettext as _

    from apps.accounts.models import Membership, Role
    from apps.notifications.services import notify

    for m in Membership.objects.filter(municipality=request.tenant, role=Role.ADMIN).select_related(
        "user"
    ):
        notify(
            m.user,
            _("A deputación está a usar o acceso de soporte"),
            _("%(r)s consulta datos persoais do concello (motivo: %(m)s). Caduca o %(d)s.")
            % {
                "r": access.region.name,
                "m": access.reason,
                "d": timezone_local(access.expires_at),
            },
            url=treverse(request.tenant, "manage:staff") + "#soporte",
            municipality=request.tenant,
        )


def timezone_local(value):
    from django.utils import timezone

    return timezone.localtime(value).strftime("%d/%m %H:%M")


def aggregate_view(view):
    """Vista sen datos persoais (só agregados ou anónimos): a deputación pode vela sempre."""
    view.aggregate_view = True
    return view


def support_action(view):
    """Acción que a deputación pode facer en modo consulta (soporte). Documentado en DECISIONS.md."""
    view.support_action = True
    return view


def neighbour_required(view):
    """Vistas da app da veciñanza. O persoal do concello (incluída a deputación) recibe 403:
    a administración non reserva nin se inscribe como veciña (só en nome doutra persoa)."""
    from apps.accounts.profiles import STAFF_ROLES

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if request.roles & STAFF_ROLES:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def module_required(key):
    """Feature flag por concello: se o módulo está desactivado, a vista non existe."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.tenant or not request.tenant.module_enabled(key):
                raise Http404
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
