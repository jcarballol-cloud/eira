# SPDX-License-Identifier: EUPL-1.2
"""v1.3 · C: dobre factor TOTP (RFC 6238), códigos de recuperación e obrigatoriedade por concello."""

import base64
import re
import time

import pyotp
import pytest
from django.core.cache import cache

from apps.accounts import twofactor
from apps.accounts.models import (
    AuditLog,
    Membership,
    RecoveryCode,
    RegionMembership,
    Role,
    TwoFactorDevice,
    User,
)

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


def _enable(user, now=None):
    device = twofactor.start_setup(user)
    code = pyotp.TOTP(device.secret).at(now or time.time())
    codes = twofactor.confirm(device, code)
    return device, codes


def _code(device, offset_steps=0):
    return pyotp.HOTP(device.secret).at(twofactor._current_step() + offset_steps)


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


def test_rfc6238_reference_vector():
    """Vector de proba do anexo B da RFC 6238 (SHA-1, T = 59 s → 94287082 con 8 díxitos)."""

    key = base64.b32encode(b"12345678901234567890").decode()
    assert pyotp.TOTP(key, digits=8).at(59) == "94287082"
    # A nosa verificación usa o mesmo cálculo (HOTP do paso de 30 s)
    assert pyotp.HOTP(key, digits=8).at(59 // twofactor.STEP) == "94287082"


def test_setup_confirm_and_recovery_codes(admin_a):
    device, codes = _enable(admin_a)
    device.refresh_from_db()
    assert device.confirmed and twofactor.enabled(admin_a)
    assert len(codes) == 10 and len(set(codes)) == 10
    assert all(re.fullmatch(r"[A-Z2-9]{4}-[A-Z2-9]{4}", c) for c in codes)
    # Só se garda o HMAC
    stored = list(RecoveryCode.objects.filter(user=admin_a).values_list("code_hash", flat=True))
    assert len(stored) == 10 and not any(c.replace("-", "") in h for c in codes for h in stored)
    assert AuditLog.objects.filter(action="2fa.enable", actor=admin_a).exists()


def test_wrong_code_does_not_confirm(admin_a):
    device = twofactor.start_setup(admin_a)
    with pytest.raises(twofactor.TwoFactorError):
        twofactor.confirm(device, "000000" if _code(device) != "000000" else "111111")
    assert not twofactor.enabled(admin_a)


def test_code_cannot_be_replayed_and_window(admin_a):
    device, _codes = _enable(admin_a)
    device.last_step = 0
    device.save()
    code = _code(device)
    assert twofactor.check_code(device, code)
    assert not twofactor.check_code(device, code)  # o mesmo código non vale dúas veces
    assert twofactor.check_code(device, _code(device, +1))  # reloxo adiantado un paso
    assert not twofactor.check_code(device, _code(device, +3))  # fóra da xanela


def test_recovery_code_single_use(admin_a):
    _device, codes = _enable(admin_a)
    assert twofactor.use_recovery_code(admin_a, codes[0].lower().replace("-", " "))
    assert not twofactor.use_recovery_code(admin_a, codes[0])
    assert twofactor.recovery_left(admin_a) == 9


def test_login_requires_second_factor(client, admin_a):
    device, codes = _enable(admin_a)
    client.force_login(admin_a)
    r = client.get(f"{C}/xestion/")
    assert r.status_code == 302 and r["Location"] == "/acceso/dobre-factor/"
    assert client.get("/conta/").status_code == 302  # todo bloqueado ata o segundo paso
    r = client.post("/acceso/dobre-factor/", {"code": "123"})
    assert r.status_code == 200 and "non é correcto" in r.content.decode()
    r = client.post("/acceso/dobre-factor/", {"code": _code(device, +1)})
    assert r.status_code == 302 and r["Location"] == f"{C}/xestion/"  # volve onde ía
    assert client.get(f"{C}/xestion/").status_code == 200
    assert AuditLog.objects.filter(action="auth.2fa", actor=admin_a).exists()


def test_login_with_recovery_code_notifies(client, admin_a):
    from apps.notifications.models import Notification

    _device, codes = _enable(admin_a)
    client.force_login(admin_a)
    r = client.post("/acceso/dobre-factor/", {"code": codes[3]})
    assert r.status_code == 302
    assert Notification.objects.filter(user=admin_a, title__icontains="recuperación").exists()
    assert AuditLog.objects.get(action="auth.2fa", actor=admin_a).detail["method"] == "recovery"


def test_too_many_attempts_logs_out(client, admin_a):
    _enable(admin_a)
    client.force_login(admin_a)
    for _i in range(twofactor.MAX_ATTEMPTS):
        client.post("/acceso/dobre-factor/", {"code": "999999"})
    r = client.post("/acceso/dobre-factor/", {"code": "999999"})
    assert r.status_code == 302 and r["Location"] == "/acceso/"
    assert AuditLog.objects.filter(action="2fa.locked").exists()
    assert "_auth_user_id" not in client.session


def test_people_without_2fa_are_not_affected(client, admin_a, citizen):
    client.force_login(admin_a)
    assert client.get(f"{C}/xestion/").status_code == 200
    client.force_login(citizen)
    assert client.get(f"{C}/").status_code == 200


def test_council_can_require_it_for_admin_and_dpo(client, muni_a, admin_a, operator_a):
    muni_a.require_2fa_admin = True
    muni_a.save()
    client.force_login(admin_a)
    r = client.get(f"{C}/xestion/")
    assert r.status_code == 302 and r["Location"] == "/conta/seguridade/?obrigatorio=1"
    assert client.get("/conta/seguridade/?obrigatorio=1").status_code == 200
    dpo = User.objects.create_user("dpd@example.org")
    Membership.objects.create(user=dpo, municipality=muni_a, role=Role.DPO)
    client.force_login(dpo)
    assert client.get(f"{C}/xestion/privacidade/brechas/").status_code == 302
    # Mantemento non é un rol de administración: non se lle esixe (403 normal, non redirección)
    client.force_login(operator_a)
    assert client.get(f"{C}/xestion/").status_code == 403
    # Coa app activada, entra
    _enable(admin_a)
    client.force_login(admin_a)
    client.post("/acceso/dobre-factor/", {"code": _code(admin_a.two_factor, +1)})
    assert client.get(f"{C}/xestion/").status_code == 200


def test_required_cannot_be_disabled(admin_a, muni_a):
    device, _codes = _enable(admin_a)
    muni_a.require_2fa_admin = True
    muni_a.save()
    with pytest.raises(twofactor.TwoFactorError):
        twofactor.disable(admin_a, _code(device, +1))
    muni_a.require_2fa_admin = False
    muni_a.save()
    twofactor.disable(admin_a, _code(device, +1))
    assert not TwoFactorDevice.objects.filter(user=admin_a).exists()
    assert not RecoveryCode.objects.filter(user=admin_a).exists()


def test_region_can_require_it(client, region, muni_a):
    u = User.objects.create_user("dep@example.org")
    RegionMembership.objects.create(user=u, region=region)
    region.require_2fa = True
    region.save()
    client.force_login(u)
    r = client.get(f"/rexion/{region.slug}/")
    assert r.status_code == 302 and "/conta/seguridade/" in r["Location"]
    assert twofactor.required_by(u) == [region.name]


def test_security_page_flow(client, admin_a):
    client.force_login(admin_a)
    r = client.post("/conta/seguridade/", {"accion": "activar"})
    html = r.content.decode()
    assert r.status_code == 200 and "<svg" in html and "data-secret" in html
    device = TwoFactorDevice.objects.get(user=admin_a)
    r = client.post("/conta/seguridade/", {"accion": "confirmar", "code": _code(device)})
    assert r.status_code == 302 and r["Location"] == "/conta/seguridade/codigos/"
    r = client.get("/conta/seguridade/codigos/")
    assert r.status_code == 200 and r["Cache-Control"] == "no-store"
    assert len(re.findall(r"<code>[A-Z2-9]{4}-[A-Z2-9]{4}</code>", r.content.decode())) == 10
    # Só se mostran unha vez
    assert client.get("/conta/seguridade/codigos/").status_code == 302
    # A sesión que o activou xa vale (non pide o segundo paso)
    assert client.get("/conta/").status_code == 200


def test_admin_resets_lost_device_of_colleague(client, muni_a, admin_a):
    colleague = User.objects.create_user("colega@example.org")
    Membership.objects.create(user=colleague, municipality=muni_a, role=Role.ADMIN)
    _enable(colleague)
    client.force_login(admin_a)
    r = client.get(f"{C}/xestion/persoal/")
    assert "Restablecer o dobre factor" in r.content.decode()
    client.post(f"{C}/xestion/persoal/", {"reset_2fa": colleague.pk})
    assert not twofactor.enabled(colleague)
    assert AuditLog.objects.filter(action="2fa.reset", actor=admin_a, municipality=muni_a).exists()


def test_reset_not_allowed_for_people_managing_other_councils(muni_a, muni_b, admin_a):
    other = User.objects.create_user("dobre@example.org")
    Membership.objects.create(user=other, municipality=muni_a, role=Role.ADMIN)
    Membership.objects.create(user=other, municipality=muni_b, role=Role.ADMIN)
    _enable(other)
    with pytest.raises(twofactor.TwoFactorError):
        twofactor.reset_for(other, admin_a, muni_a)
    with pytest.raises(twofactor.TwoFactorError):
        twofactor.reset_for(admin_a, admin_a, muni_a)
