# SPDX-License-Identifier: EUPL-1.2
"""v1.4 · A: segredo TOTP cifrado en repouso e prazo de conservación do rexistro de auditoría."""

import datetime as dt
import importlib
import io

import pyotp
import pytest
from django.apps import apps as django_apps
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from apps.accounts import secretbox, twofactor
from apps.accounts.auditlog import DEFAULT_RETENTION_MONTHS, purge_expired
from apps.accounts.models import AuditLog, TwoFactorDevice, audit

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


def _raw_secret(device):
    table = connection.ops.quote_name(TwoFactorDevice._meta.db_table)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT secret FROM {table} WHERE id = %s", [device.pk])
        return cursor.fetchone()[0]


def _set_raw_secret(device, value):
    table = connection.ops.quote_name(TwoFactorDevice._meta.db_table)
    with connection.cursor() as cursor:
        cursor.execute(f"UPDATE {table} SET secret = %s WHERE id = %s", [value, device.pk])


# --- A2: segredo TOTP cifrado ---------------------------------------------------------------


def test_secret_is_encrypted_at_rest_and_codes_still_work(admin_a):
    device = twofactor.start_setup(admin_a)
    plain = device.secret
    raw = _raw_secret(device)
    assert raw.startswith(secretbox.PREFIX) and plain not in raw
    device = TwoFactorDevice.objects.get(pk=device.pk)
    assert device.secret == plain
    codes = twofactor.confirm(device, pyotp.TOTP(plain).now())
    assert len(codes) == 10
    device.refresh_from_db()
    assert device.confirmed and _raw_secret(device).startswith(secretbox.PREFIX)


def test_each_save_uses_a_fresh_ciphertext(admin_a):
    device = twofactor.start_setup(admin_a)
    first = _raw_secret(device)
    device.save(update_fields=["secret"])
    assert _raw_secret(device) != first
    assert TwoFactorDevice.objects.get(pk=device.pk).secret == device.secret


def test_migration_encrypts_legacy_plaintext(admin_a):
    device = twofactor.start_setup(admin_a)
    plain = pyotp.random_base32()
    _set_raw_secret(device, plain)  # como estaba gardado antes da v1.4
    # O texto claro antigo lese tal cal (a app non falla antes de migrar)
    assert TwoFactorDevice.objects.get(pk=device.pk).secret == plain
    migration = importlib.import_module("apps.accounts.migrations.0012_v1_4")
    migration.encrypt_existing(django_apps, None)
    raw = _raw_secret(device)
    assert raw.startswith(secretbox.PREFIX) and plain not in raw
    assert TwoFactorDevice.objects.get(pk=device.pk).secret == plain


def test_migration_reverse_leaves_plaintext(admin_a):
    device = twofactor.start_setup(admin_a)
    plain = device.secret
    migration = importlib.import_module("apps.accounts.migrations.0012_v1_4")
    migration.decrypt_existing(django_apps, connection.schema_editor())
    assert _raw_secret(device) == plain


def test_own_key_reads_old_values_and_rotate_moves_them(admin_a, settings):
    from cryptography.fernet import Fernet

    device = twofactor.start_setup(admin_a)
    plain = device.secret
    old_raw = _raw_secret(device)
    settings.EIRA_TOTP_KEY = "chave-propia-de-proba-non-real"
    own = Fernet(secretbox._derive(settings.EIRA_TOTP_KEY))
    # Co valor cifrado coa chave derivada de EIRA_SECRET_KEY séguese podendo ler
    assert TwoFactorDevice.objects.get(pk=device.pk).secret == plain
    out = io.StringIO()
    call_command("rotate_totp_key", stdout=out)
    assert "1 segredos cifrados de novo, 0 ilexibles" in out.getvalue()
    new_raw = _raw_secret(device)
    assert new_raw != old_raw
    # Agora está cifrado coa chave propia
    assert own.decrypt(new_raw[len(secretbox.PREFIX) :].encode()).decode() == plain


def test_changed_key_does_not_crash_and_rejects_codes(admin_a, settings, client):
    device = twofactor.start_setup(admin_a)
    plain = device.secret
    twofactor.confirm(device, pyotp.TOTP(plain).now())
    settings.SECRET_KEY = "outra-chave-distinta-non-real"
    device = TwoFactorDevice.objects.get(pk=device.pk)
    assert device.secret == ""
    assert twofactor.check_code(device, pyotp.TOTP(plain).now()) is False
    out = io.StringIO()
    call_command("rotate_totp_key", stdout=out)
    assert "0 segredos cifrados de novo, 1 ilexibles" in out.getvalue()


def test_decrypt_rejects_tampered_value(admin_a):
    token = secretbox.encrypt("JBSWY3DPEHPK3PXP")
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    with pytest.raises(secretbox.DecryptError):
        secretbox.decrypt(tampered)
    assert secretbox.decrypt(token) == "JBSWY3DPEHPK3PXP"


def test_setup_page_still_shows_the_key_in_clear(client, admin_a):
    client.force_login(admin_a)
    client.post("/conta/seguridade/", {"accion": "activar"})
    device = TwoFactorDevice.objects.get(user=admin_a)
    page = client.get("/conta/seguridade/").content.decode()
    assert device.secret[:4] in page
    assert _raw_secret(device) not in page


# --- A1: conservación do rexistro de auditoría ----------------------------------------------


def _old(entry, days):
    AuditLog.objects.filter(pk=entry.pk).update(at=timezone.now() - dt.timedelta(days=days))


def test_default_retention_is_two_years(muni_a):
    assert muni_a.audit_retention_months == 24 == DEFAULT_RETENTION_MONTHS


def test_purge_respects_each_municipality(muni_a, muni_b, admin_a):
    muni_b.audit_retention_months = 12
    muni_b.save(update_fields=["audit_retention_months"])
    recent_a = audit("tenant.settings", actor=admin_a, municipality=muni_a)
    old_a = audit("tenant.settings", actor=admin_a, municipality=muni_a)
    mid_b = audit("tenant.settings", municipality=muni_b)
    recent_b = audit("tenant.settings", municipality=muni_b)
    _old(recent_a, 30 * 23)
    _old(old_a, 30 * 25)
    _old(mid_b, 30 * 13)
    _old(recent_b, 30 * 11)
    assert purge_expired() == 2
    left = set(AuditLog.objects.exclude(action="audit.purge").values_list("pk", flat=True))
    assert left == {recent_a.pk, recent_b.pk}
    # A purga queda rexistrada en cada concello, sen datos persoais
    purges = AuditLog.objects.filter(action="audit.purge")
    assert {(p.municipality_id, p.detail["deleted"], p.detail["months"]) for p in purges} == {
        (muni_a.pk, 1, 24),
        (muni_b.pk, 1, 12),
    }
    assert purge_expired() == 0
    assert AuditLog.objects.filter(action="audit.purge").count() == 2


def test_purge_entries_without_municipality_use_default(admin_a, muni_a):
    muni_a.audit_retention_months = 120
    muni_a.save(update_fields=["audit_retention_months"])
    login_old = audit("auth.login", actor=admin_a)
    login_new = audit("auth.login", actor=admin_a)
    _old(login_old, 30 * DEFAULT_RETENTION_MONTHS + 1)
    _old(login_new, 30 * DEFAULT_RETENTION_MONTHS - 1)
    assert purge_expired() == 1
    assert AuditLog.objects.filter(pk=login_new.pk).exists()
    assert not AuditLog.objects.filter(pk=login_old.pk).exists()


def test_maintenance_command_purges_audit_log(muni_a):
    entry = audit("tenant.settings", municipality=muni_a)
    _old(entry, 30 * 30)
    out = io.StringIO()
    call_command("booking_maintenance", stdout=out)
    assert "Rexistro de auditoría: 1 entradas borradas por antigüidade" in out.getvalue()
    assert not AuditLog.objects.filter(pk=entry.pk).exists()


@pytest.mark.parametrize(
    "months,ok", [(11, False), (12, True), (24, True), (120, True), (121, False)]
)
def test_retention_limits(muni_a, months, ok):
    muni_a.audit_retention_months = months
    if ok:
        muni_a.full_clean()
    else:
        with pytest.raises(ValidationError):
            muni_a.full_clean()


def test_admin_changes_retention_in_settings(client, admin_a, muni_a):
    client.force_login(admin_a)
    page = client.get(f"{C}/xestion/configuracion/").content.decode()
    assert 'name="audit_retention_months"' in page
    form = _settings_form_data(client)
    form["audit_retention_months"] = "36"
    response = client.post(f"{C}/xestion/configuracion/", form)
    assert response.status_code in (200, 302)
    muni_a.refresh_from_db()
    assert muni_a.audit_retention_months == 36


def _settings_form_data(client):
    """Valores actuais do formulario de configuración, como os enviaría o navegador."""
    import re

    html = client.get(f"{C}/xestion/configuracion/").content.decode()
    data = {}
    for m in re.finditer(r"<input\b[^>]*>", html):
        tag = m.group(0)
        name = re.search(r'name="([^"]+)"', tag)
        if not name or name.group(1) == "csrfmiddlewaretoken":
            continue
        kind = re.search(r'type="([^"]+)"', tag)
        kind = kind.group(1) if kind else "text"
        value = re.search(r'value="([^"]*)"', tag)
        if kind in ("checkbox", "radio"):
            if "checked" in tag:
                data.setdefault(name.group(1), value.group(1) if value else "on")
            continue
        data[name.group(1)] = value.group(1) if value else ""
    for m in re.finditer(r'<select\b[^>]*name="([^"]+)"[^>]*>(.*?)</select>', html, re.S):
        sel = re.search(r'<option\b[^>]*value="([^"]*)"[^>]*selected', m.group(2))
        if sel:
            data[m.group(1)] = sel.group(1)
    for m in re.finditer(r'<textarea\b[^>]*name="([^"]+)"[^>]*>(.*?)</textarea>', html, re.S):
        data[m.group(1)] = m.group(2)
    return data


def test_audit_page_tells_the_retention(client, admin_a, muni_a):
    client.force_login(admin_a)
    page = client.get(f"{C}/xestion/privacidade/auditoria/").content.decode()
    assert "24 meses" in page
