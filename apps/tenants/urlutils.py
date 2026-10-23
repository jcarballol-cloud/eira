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

    A deputación (`region_admin`) entra nos concellos da súa rede só en **modo consulta**: pode ler,
    pero calquera escritura dá 403 agás nas accións marcadas con `@support_action`.
    """

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not (request.roles & set(roles)):
                raise PermissionDenied
            read_only = "region_admin" in request.roles and "admin" not in request.roles
            if (
                read_only
                and request.method not in SAFE_METHODS
                and not getattr(view, "support_action", False)
            ):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


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
