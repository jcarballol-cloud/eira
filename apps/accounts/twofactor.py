# SPDX-License-Identifier: EUPL-1.2
"""v1.3 · C: dobre factor TOTP (RFC 6238) e códigos de recuperación.

- Opcional para calquera persoa; obrigatorio para a administración e o DPD dun concello que o
  configure (`require_2fa_admin`) e para a deputación se a agrupación o configura (`require_2fa`).
- O segundo factor pídese **despois** do código ao correo ou de Cl@ve: a sesión queda identificada
  pero bloqueada (`TwoFactorMiddleware`) ata introducir o código da app ou un de recuperación.
- Un código TOTP non vale dúas veces (gárdase o último paso aceptado). Intentos limitados.
- Códigos de recuperación: 10, dun só uso, gardados como HMAC e mostrados unha única vez.
"""

import secrets
import time

import pyotp
from django import forms
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from .models import Membership, RecoveryCode, TwoFactorDevice, audit, hash_recovery_code

STEP = 30  # segundos (RFC 6238)
DIGITS = 6
WINDOW = 1  # admítese o paso anterior e o seguinte (desfase do reloxo do móbil)
RECOVERY_COUNT = 10
RECOVERY_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sen 0/O nin 1/I/L
MAX_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60
SESSION_KEY = "2fa_ok"  # pk do dispositivo verificado nesta sesión
NEXT_KEY = "2fa_next"
ISSUER = "Eira"
MANAGEMENT_ROLES = ("admin", "dpo")


class TwoFactorError(Exception):
    pass


# ---------------------------------------------------------------- servizos


def device_for(user):
    if not getattr(user, "is_authenticated", False):
        return None
    return TwoFactorDevice.objects.filter(user=user).first()


def enabled(user):
    device = device_for(user)
    return bool(device and device.confirmed)


def start_setup(user):
    """Crea (ou reinicia) un dispositivo sen confirmar cun segredo novo."""
    device, _created = TwoFactorDevice.objects.get_or_create(
        user=user, defaults={"secret": pyotp.random_base32()}
    )
    if device.confirmed:
        raise TwoFactorError(_("O dobre factor xa está activado."))
    device.secret = pyotp.random_base32()
    device.last_step = 0
    device.save(update_fields=["secret", "last_step"])
    return device


def provisioning_uri(device):
    return pyotp.TOTP(device.secret, digits=DIGITS, interval=STEP).provisioning_uri(
        name=device.user.email, issuer_name=ISSUER
    )


def _current_step(now=None):
    return int((now if now is not None else time.time()) // STEP)


def check_code(device, code, now=None):
    """True se o código TOTP é válido e non se usou xa. Garda o paso para evitar reprodución."""
    code = "".join(ch for ch in (code or "") if ch.isdigit())
    if len(code) != DIGITS or not device.secret:  # v1.4: segredo ilexible (chave cambiada)
        return False
    hotp = pyotp.HOTP(device.secret, digits=DIGITS)
    current = _current_step(now)
    for step in range(current - WINDOW, current + WINDOW + 1):
        if step <= device.last_step:
            continue
        if secrets.compare_digest(hotp.at(step), code):
            device.last_step = step
            device.save(update_fields=["last_step"])
            return True
    return False


def new_recovery_codes(user):
    """Substitúe os códigos de recuperación. Devolve os novos en claro (só se mostran unha vez)."""
    codes = []
    for _i in range(RECOVERY_COUNT):
        raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _j in range(8))
        codes.append(f"{raw[:4]}-{raw[4:]}")
    with transaction.atomic():
        RecoveryCode.objects.filter(user=user).delete()
        RecoveryCode.objects.bulk_create(
            RecoveryCode(user=user, code_hash=hash_recovery_code(user.pk, c)) for c in codes
        )
    return codes


def use_recovery_code(user, code):
    found = RecoveryCode.objects.filter(
        user=user, used_at__isnull=True, code_hash=hash_recovery_code(user.pk, code)
    ).first()
    if found is None:
        return False
    found.used_at = timezone.now()
    found.save(update_fields=["used_at"])
    return True


def recovery_left(user):
    return RecoveryCode.objects.filter(user=user, used_at__isnull=True).count()


def confirm(device, code, request=None):
    if not check_code(device, code):
        raise TwoFactorError(
            _("O código non é correcto. Comproba a hora do móbil e téntao de novo.")
        )
    device.confirmed_at = timezone.now()
    device.save(update_fields=["confirmed_at"])
    codes = new_recovery_codes(device.user)
    audit("2fa.enable", device.user, _tenant_of(request))
    return codes


def required_by(user):
    """Concellos e agrupacións que lle esixen o dobre factor a esta persoa (lista de nomes)."""
    if not getattr(user, "is_authenticated", False):
        return []
    names = [
        m.municipality.name
        for m in Membership.objects.filter(
            user=user, role__in=MANAGEMENT_ROLES, municipality__require_2fa_admin=True
        ).select_related("municipality")
    ]
    names += [
        rm.region.name
        for rm in user.region_memberships.filter(region__require_2fa=True).select_related("region")
    ]
    return sorted(set(names))


def disable(user, code, request=None):
    device = device_for(user)
    if not device or not device.confirmed:
        raise TwoFactorError(_("O dobre factor non está activado."))
    if required_by(user):
        raise TwoFactorError(
            _("Non o podes desactivar: %(n)s esíxeo para o teu rol.")
            % {"n": ", ".join(required_by(user))}
        )
    if not (check_code(device, code) or use_recovery_code(user, code)):
        raise TwoFactorError(_("O código non é correcto."))
    device.delete()
    RecoveryCode.objects.filter(user=user).delete()
    audit("2fa.disable", user, _tenant_of(request))


def reset_for(target, by, municipality):
    """Outra persoa administradora do concello quítalle o dobre factor a quen perdeu o móbil e os
    códigos. Só se a persoa non xestiona outros concellos nin a deputación (aí faino o soporte)."""
    if target == by:
        raise TwoFactorError(_("Non podes restablecer o teu propio dobre factor."))
    elsewhere = (
        Membership.objects.filter(user=target, role__in=MANAGEMENT_ROLES)
        .exclude(municipality=municipality)
        .exists()
        or target.region_memberships.exists()
    )
    if elsewhere:
        raise TwoFactorError(
            _(
                "Esta persoa xestiona outros concellos ou a deputación: o restablecemento faino o "
                "soporte técnico da instalación."
            )
        )
    deleted, _rows = TwoFactorDevice.objects.filter(user=target).delete()
    RecoveryCode.objects.filter(user=target).delete()
    if deleted:
        audit("2fa.reset", by, municipality, target)
    return bool(deleted)


def _tenant_of(request):
    return getattr(request, "tenant", None) if request is not None else None


def _lock_key(user):
    return f"eira:2fa:fail:{user.pk}"


def locked(user):
    return (cache.get(_lock_key(user)) or 0) >= MAX_ATTEMPTS


def register_failure(user):
    key = _lock_key(user)
    cache.add(key, 0, LOCK_SECONDS)
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, LOCK_SECONDS)
        return 1


def clear_failures(user):
    cache.delete(_lock_key(user))


# ---------------------------------------------------------------- middleware

EXEMPT_PREFIXES = (
    "/acceso/",
    "/static/",
    "/i18n/",
    "/sw.js",
    "/manifest.webmanifest",
    "/offline/",
    "/dev/",  # ferramentas da demo (cambio de perfil); só existen con EIRA_DEMO_TOOLS=1
)


class TwoFactorMiddleware:
    """1) Sesión co segundo factor pendente → só deixa ver a páxina do código.
    2) Concello/agrupación que o esixe e persoa sen activalo → á páxina para activalo antes de
       entrar na xestión."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and not request.path.startswith(EXEMPT_PREFIXES)
        ):
            device = device_for(user)
            if device and device.confirmed and request.session.get(SESSION_KEY) != device.pk:
                if request.method == "GET" and not request.headers.get("HX-Request"):
                    request.session.setdefault(NEXT_KEY, request.get_full_path())
                return redirect("accounts:two_factor")
            request.two_factor_device = device
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        match = getattr(request, "resolver_match", None)
        namespace = getattr(match, "namespace", "") or ""
        if namespace not in ("manage", "region"):
            return None
        device = getattr(request, "two_factor_device", None)
        if device is not None and device.confirmed:
            return None
        if _must_have_2fa(request, user, namespace):
            messages.warning(
                request,
                _("Para entrar na xestión tes que activar o dobre factor (esíxeo o teu concello)."),
            )
            return redirect(reverse("account:security") + "?obrigatorio=1")
        return None


def _must_have_2fa(request, user, namespace):
    tenant = getattr(request, "tenant", None)
    roles = getattr(request, "roles", set())
    if namespace == "manage" and tenant is not None:
        if tenant.require_2fa_admin and roles & {"admin", "dpo", "region_admin"}:
            return True
        if "region_admin" in roles and tenant.region_id and tenant.region.require_2fa:
            return True
        return False
    if namespace == "region":
        return user.region_memberships.filter(region__require_2fa=True).exists()
    return False


# ---------------------------------------------------------------- vistas


class VerifyForm(forms.Form):
    code = forms.CharField(
        label=gettext_lazy("Código da app ou de recuperación"),
        max_length=12,
        help_text=gettext_lazy(
            "Os 6 díxitos que mostra agora a túa app de códigos, ou un código de recuperación "
            "(p. ex. ABCD-2345)."
        ),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "autocapitalize": "characters",
                "spellcheck": "false",
            }
        ),
    )


class CodeForm(forms.Form):
    code = forms.CharField(
        label=gettext_lazy("Código de 6 díxitos da app"),
        max_length=7,
        widget=forms.TextInput(
            attrs={"autocomplete": "one-time-code", "inputmode": "numeric", "pattern": "[0-9 ]*"}
        ),
    )


def _safe_next(request):
    nxt = request.session.pop(NEXT_KEY, None) or "/"
    return nxt if url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}) else "/"


def verify(request):
    """Segundo paso do acceso: código da app ou de recuperación."""
    request.layout_override = "public"
    user = request.user
    if not user.is_authenticated:
        return redirect("accounts:login")
    device = device_for(user)
    if not device or not device.confirmed or request.session.get(SESSION_KEY) == device.pk:
        return redirect(_safe_next(request))
    form = VerifyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if locked(user):
            audit("2fa.locked", user)
            logout(request)
            messages.error(
                request, _("Demasiados intentos. Agarda 15 minutos antes de volver entrar.")
            )
            return redirect("accounts:login")
        code = form.cleaned_data["code"]
        if check_code(device, code):
            method = "totp"
        elif use_recovery_code(user, code):
            method = "recovery"
        else:
            method = None
        if method:
            clear_failures(user)
            request.session.cycle_key()
            request.session[SESSION_KEY] = device.pk
            audit("auth.2fa", user, method=method)
            if method == "recovery":
                _recovery_used_notice(request, user)
            return redirect(_safe_next(request))
        register_failure(user)
        audit("2fa.failed", user)
        form.add_error("code", _("O código non é correcto ou xa se usou."))
    return render(request, "accounts/two_factor_verify.html", {"form": form})


def _recovery_used_notice(request, user):
    from apps.notifications.services import notify

    left = recovery_left(user)
    body = _(
        "Entraches na túa conta cun código de recuperación. Quédanche %(n)s. Se non fuches ti, "
        "avisa á administración do concello."
    ) % {"n": left}
    notify(
        user,
        _("Usouse un código de recuperación"),
        body,
        url=reverse("account:security"),
        telegram=False,
    )
    messages.warning(request, body)


@login_required
def security(request):
    """Seguridade da conta: activar ou desactivar o dobre factor e os códigos de recuperación."""
    user = request.user
    device = device_for(user)
    action = request.POST.get("accion") if request.method == "POST" else None
    form = CodeForm(request.POST if action in ("confirmar", "desactivar", "codigos") else None)
    try:
        if action == "activar":
            device = start_setup(user)
        elif action == "confirmar" and device and not device.confirmed and form.is_valid():
            codes = confirm(device, form.cleaned_data["code"], request)
            request.session[SESSION_KEY] = device.pk
            request.session["2fa_codes"] = codes
            messages.success(request, _("Dobre factor activado."))
            return redirect("account:security_codes")
        elif action == "codigos" and device and device.confirmed and form.is_valid():
            if not check_code(device, form.cleaned_data["code"]):
                raise TwoFactorError(_("O código non é correcto."))
            request.session["2fa_codes"] = new_recovery_codes(user)
            audit("2fa.recovery_regenerate", user)
            return redirect("account:security_codes")
        elif action == "desactivar" and form.is_valid():
            disable(user, form.cleaned_data["code"], request)
            request.session.pop(SESSION_KEY, None)
            messages.success(request, _("Dobre factor desactivado."))
            return redirect("account:security")
        elif action == "cancelar" and device and not device.confirmed:
            device.delete()
            return redirect("account:security")
    except TwoFactorError as exc:
        if form.is_bound:
            form.add_error("code", str(exc))
        else:
            messages.error(request, str(exc))
    pending = device is not None and not device.confirmed
    return render(
        request,
        "accounts/security.html",
        {
            "device": device,
            "pending": pending,
            "form": form,
            "required_by": required_by(user),
            "forced": request.GET.get("obrigatorio") == "1",
            "recovery_left": recovery_left(user) if device and device.confirmed else 0,
            "qr_svg": _qr(device) if pending else "",
            "secret_groups": _groups(device.secret) if pending else "",
            "issuer": ISSUER,
        },
    )


@login_required
def security_codes(request):
    """Mostra os códigos de recuperación novos unha única vez."""
    codes = request.session.pop("2fa_codes", None)
    if not codes:
        return redirect("account:security")
    response = render(request, "accounts/security_codes.html", {"codes": codes})
    response["Cache-Control"] = "no-store"
    return response


def _qr(device):
    from apps.access.views import qr_svg

    return qr_svg(provisioning_uri(device))


def _groups(secret):
    return " ".join(secret[i : i + 4] for i in range(0, len(secret), 4))
