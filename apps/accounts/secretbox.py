# SPDX-License-Identifier: EUPL-1.2
"""v1.4 · A2: cifrado en repouso de segredos curtos (o segredo TOTP do dobre factor).

Fernet (AES-128-CBC + HMAC-SHA256, da biblioteca `cryptography`). A chave sae de:

- `EIRA_TOTP_KEY`, se está definida (recomendado en produción: así cambiar `EIRA_SECRET_KEY` non
  deixa ninguén sen dobre factor e quen só ten a copia de seguridade da base de datos non ten a chave);
- se non, derívase de `EIRA_SECRET_KEY` con HKDF-SHA256 (contexto propio, non reutiliza a chave tal cal).

Con `EIRA_TOTP_KEY` definida, os valores cifrados antes coa chave derivada de `EIRA_SECRET_KEY`
séguense lendo (MultiFernet) e rescríbense coa chave nova co comando `rotate_totp_key`.
Os valores gárdanse con prefixo `enc1:`; un valor sen prefixo é texto claro antigo (anterior á
v1.4) e lese tal cal ata que a migración ou a seguinte escritura o cifra. Ver docs/seguridade-rxpd.md.
"""

import base64

from django.conf import settings
from django.db import models

PREFIX = "enc1:"
_INFO = b"eira-v1.4-totp-secret"


class DecryptError(Exception):
    pass


def _derive(material):
    # Importación diferida: os comandos que só cargan os modelos (makemessages) non a precisan
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    raw = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"eira", info=_INFO).derive(
        material.encode()
    )
    return base64.urlsafe_b64encode(raw)


def _box():
    from cryptography.fernet import Fernet, MultiFernet

    keys = []
    own = getattr(settings, "EIRA_TOTP_KEY", "")
    if own:
        keys.append(_derive(own))
    keys.append(_derive(settings.SECRET_KEY))
    return MultiFernet([Fernet(k) for k in keys])


def encrypt(value):
    if not value:
        return value
    return PREFIX + _box().encrypt(value.encode()).decode()


def decrypt(value):
    if not value or not value.startswith(PREFIX):
        return value  # baleiro ou texto claro anterior á v1.4
    from cryptography.fernet import InvalidToken

    try:
        return _box().decrypt(value[len(PREFIX) :].encode()).decode()
    except InvalidToken as exc:
        raise DecryptError("Non se pode descifrar: cambiou a chave?") from exc


def rotate(value):
    """Volve cifrar coa chave principal actual (devolve o mesmo se xa o estaba)."""
    if not value:
        return value
    if not value.startswith(PREFIX):
        return encrypt(value)
    return PREFIX + _box().rotate(value[len(PREFIX) :].encode()).decode()


class EncryptedCharField(models.CharField):
    """CharField que cifra ao gardar e descifra ao ler. Non se pode buscar polo seu valor.

    Se a chave cambiou e o valor non se pode descifrar, le cadea baleira: o dobre factor desa
    persoa deixa de validar códigos (pode entrar cun código de recuperación ou que a
    administración llo restableza), pero a aplicación non falla."""

    def from_db_value(self, value, expression, connection):
        try:
            return decrypt(value)
        except DecryptError:
            return ""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value and not value.startswith(PREFIX):
            return encrypt(value)
        return value
