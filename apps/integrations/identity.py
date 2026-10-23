# SPDX-License-Identifier: EUPL-1.2
"""Identidade pública (Cl@ve, Chave365) detrás dun adaptador.

O prototipo inclúe un provedor simulado (/dev/clave/). As implementacións reais
(SAML 2.0 para Cl@ve; OpenID Connect para Chave365) quedan como esqueleto: o resto
da plataforma só depende de `Identity`.
"""

import hashlib
import secrets
from dataclasses import dataclass

from django.conf import settings
from django.urls import reverse


@dataclass
class Identity:
    subject: str  # identificador opaco e estable (nunca o DNI en claro)
    email: str
    name: str
    provider: str
    assurance: str = "substantial"


def opaque_subject(provider, raw_id):
    return hashlib.sha256(f"{settings.SECRET_KEY}:{provider}:{raw_id}".encode()).hexdigest()[:40]


class IdentityAdapter:
    name = "abstract"

    def start(self, request, next_url):
        """Devolve a URL á que redirixir para iniciar a autenticación."""
        raise NotImplementedError

    def complete(self, request):
        """Valida a resposta do provedor e devolve unha Identity ou None."""
        raise NotImplementedError


# Identidades ficticias do provedor simulado (sen datos reais).
FAKE_IDENTITIES = {
    "proba-1": {"name": "Persoa de proba Cl@ve 1", "email": "clave.proba1@example.org"},
    "proba-2": {"name": "Persoa de proba Cl@ve 2", "email": "clave.proba2@example.org"},
}


class FakeClaveAdapter(IdentityAdapter):
    name = "clave-simulado"

    def start(self, request, next_url):
        state = secrets.token_urlsafe(16)
        request.session["identity_state"] = state
        request.session["identity_next"] = next_url
        return f"{reverse('dev:clave')}?state={state}"

    def complete(self, request):
        state = request.POST.get("state") or request.GET.get("state") or ""
        expected = request.session.pop("identity_state", None)
        if not expected or not secrets.compare_digest(str(state), expected):
            return None
        key = request.POST.get("identity") or request.GET.get("identity")
        data = FAKE_IDENTITIES.get(key)
        if not data:
            return None
        return Identity(
            subject=opaque_subject(self.name, key), email=data["email"], name=data["name"], provider=self.name
        )


class ClaveSamlAdapter(IdentityAdapter):
    """Esqueleto: Cl@ve mediante SAML 2.0 (pasarela da AGE).

    Pasos previstos: alta do concello como provedor de servizo, metadatos SP asinados,
    AuthnRequest co nivel de garantía (LoA), validación da Response asinada e
    extracción do identificador. Pódese apoiar en pysaml2 (Apache-2.0).
    """

    name = "clave"

    def start(self, request, next_url):
        raise NotImplementedError("Configura a pasarela Cl@ve (SAML 2.0)")

    def complete(self, request):
        raise NotImplementedError


class Chave365OidcAdapter(IdentityAdapter):
    """Esqueleto: Chave365 (Xunta de Galicia) mediante OpenID Connect (Authorization Code + PKCE)."""

    name = "chave365"

    def start(self, request, next_url):
        raise NotImplementedError("Configura o cliente OIDC de Chave365")

    def complete(self, request):
        raise NotImplementedError
