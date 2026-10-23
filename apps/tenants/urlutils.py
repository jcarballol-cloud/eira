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


def role_required(*roles):
    """Restrinxe unha vista do concello aos roles indicados (no concello activo)."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not (request.roles & set(roles)):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


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
