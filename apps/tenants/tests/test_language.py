# SPDX-License-Identifier: EUPL-1.2
"""Idioma (14/11/2026): o galego é sempre o de partida, aínda que o navegador estea en castelán.
Só cambia se a persoa o escolle no selector; a escolla lémbrase (perfil con sesión, cookie sen
ela) e o concello pode cambiar o seu idioma por defecto."""

import re

import pytest

from apps.accounts.models import User
from apps.integrations.models import DevMail

C = "/c/concello-a"
ES = {"HTTP_ACCEPT_LANGUAGE": "es-ES,es;q=0.9,en;q=0.8"}


def lang(html):
    return re.search(r'<html lang="([a-z-]+)"', html).group(1)


@pytest.fixture
def es_client(client):
    """Un navegador configurado en castelán (Accept-Language: es-ES)."""
    client.defaults.update(ES)
    return client


@pytest.mark.parametrize(
    "path,gl,es",
    [
        (f"{C}/", "Instalacións", "Instalaciones"),
        ("/acceso/", "Acceder sen contrasinal", "Acceder sin contraseña"),
        (f"{C}/privacidade/", "Privacidade", "Privacidad<"),
        (f"{C}/accesibilidade/", "Declaración de accesibilidade", "accesibilidad<"),
        ("/accesibilidade/", "Declaración de accesibilidade", "accesibilidad<"),
        ("/axuda/", "Guía de Eira", "Guía de la app"),
    ],
)
def test_first_visit_from_a_spanish_browser_is_in_galician(
    es_client, muni_a, padel_a, path, gl, es
):
    resp = es_client.get(path)
    html = resp.content.decode()
    assert resp.status_code == 200, path
    assert lang(html) == "gl", path
    assert resp["Content-Language"] == "gl"
    assert gl in html and es not in html, path
    assert "django_language" not in resp.cookies  # ninguén escolleu nada


def test_simulated_login_mail_is_in_galician(es_client, muni_a):
    es_client.post("/acceso/", {"email": "ana@example.org"})
    mail = DevMail.objects.get(to="ana@example.org")
    assert mail.subject.startswith("O teu código de acceso a Eira")
    assert "Introduce este código" in mail.body


def test_guided_tour_is_in_galician(es_client, settings, citizen, muni_a):
    settings.EIRA_DEMO_TOOLS = True
    es_client.force_login(citizen)
    from apps.tenants.tests.test_tours import tour_json

    html = es_client.get(f"{C}/app/").content.decode()
    assert "Non volver amosar a guía" in html
    assert lang(html) == "gl" and tour_json(html)["title"] == "Guía da app"


def test_choosing_spanish_is_remembered_without_a_session(es_client, muni_a):
    resp = es_client.post("/i18n/setlang/", {"language": "es", "next": f"{C}/"})
    assert resp.status_code == 302 and resp["Location"] == f"{C}/"
    cookie = resp.cookies["django_language"]
    assert cookie.value == "es" and int(cookie["max-age"]) >= 300 * 24 * 3600
    assert lang(es_client.get(f"{C}/").content.decode()) == "es"
    # Un navegador en galego coa cookie de castelán: manda a escolla, non o navegador
    es_client.defaults["HTTP_ACCEPT_LANGUAGE"] = "gl"
    assert lang(es_client.get("/acceso/").content.decode()) == "es"
    # E volver ao galego tamén se lembra
    es_client.post("/i18n/setlang/", {"language": "gl", "next": f"{C}/"})
    assert lang(es_client.get(f"{C}/").content.decode()) == "gl"


def test_unknown_language_is_ignored(es_client, muni_a):
    es_client.cookies["django_language"] = "fr"
    assert lang(es_client.get(f"{C}/").content.decode()) == "gl"
    es_client.post("/i18n/setlang/", {"language": "fr", "next": "/"})
    assert lang(es_client.get(f"{C}/").content.decode()) == "gl"


def test_choice_with_a_session_goes_to_the_profile_and_follows_the_person(
    es_client, citizen, muni_a
):
    from django.test import Client

    es_client.force_login(citizen)
    es_client.post("/i18n/setlang/", {"language": "es", "next": f"{C}/"})
    citizen.refresh_from_db()
    assert citizen.preferred_language == "es"
    # Outro dispositivo, sen cookie e cun navegador en galego: segue en castelán polo perfil
    other = Client()
    other.force_login(citizen)
    resp = other.get(f"{C}/")
    assert lang(resp.content.decode()) == "es"
    assert resp.cookies["django_language"].value == "es"  # a cookie segue o perfil


def test_profile_without_choice_uses_the_municipality_language(es_client, citizen, muni_a):
    assert citizen.preferred_language == ""
    es_client.force_login(citizen)
    assert lang(es_client.get(f"{C}/").content.decode()) == "gl"


def test_choice_made_before_signing_in_is_kept_in_the_profile(es_client, muni_a):
    es_client.post("/i18n/setlang/", {"language": "es", "next": "/"})
    es_client.post("/acceso/", {"email": "ana@example.org"})
    code = re.search(r"\d{6}", DevMail.objects.get(to="ana@example.org").subject).group(0)
    es_client.post("/acceso/codigo/", {"code": code})
    assert User.objects.get(email="ana@example.org").preferred_language == "es"


def test_profile_form_can_go_back_to_the_municipality_language(client, citizen, muni_a):
    citizen.preferred_language = "es"
    citizen.save()
    client.force_login(citizen)
    client.post(
        "/conta/",
        {"display_name": "Veciña", "phone": "", "birth_year": "1990", "preferred_language": ""},
    )
    citizen.refresh_from_db()
    assert citizen.preferred_language == ""


def test_municipality_can_set_its_default_language(es_client, muni_a):
    assert muni_a.default_language == "gl"
    muni_a.default_language = "es"
    muni_a.save()
    assert lang(es_client.get(f"{C}/").content.decode()) == "es"
    # A escolla da persoa pesa máis que o do concello
    es_client.cookies["django_language"] = "gl"
    assert lang(es_client.get(f"{C}/").content.decode()) == "gl"


def test_default_language_in_the_settings_screen(client, admin_a, muni_a):
    client.force_login(admin_a)
    html = client.get(f"{C}/xestion/configuracion/").content.decode()
    assert 'name="default_language"' in html and "Non se usa o idioma do navegador" in html


def test_public_demo_keeps_the_choice_only_in_the_browser(es_client, settings, citizen, muni_a):
    """Na demo pública as contas son de todo o mundo: o castelán dunha visita non pode pasar á
    seguinte persoa que entre como Uxía."""
    from django.test import Client

    settings.EIRA_PUBLIC_DEMO = True
    es_client.force_login(citizen)
    es_client.post("/i18n/setlang/", {"language": "es", "next": f"{C}/"})
    assert lang(es_client.get(f"{C}/").content.decode()) == "es"
    citizen.refresh_from_db()
    assert citizen.preferred_language == ""
    other = Client(**ES)
    other.force_login(citizen)
    assert lang(other.get(f"{C}/").content.decode()) == "gl"
    # Mesmo cun perfil antigo en castelán, na demo pública non se usa
    User.objects.filter(pk=citizen.pk).update(preferred_language="es")
    assert lang(other.get(f"{C}/").content.decode()) == "gl"


def test_new_installation_defaults(settings):
    from apps.tenants.models import Municipality

    assert settings.LANGUAGE_CODE == "gl"
    assert "django.middleware.locale.LocaleMiddleware" not in settings.MIDDLEWARE
    assert Municipality._meta.get_field("default_language").default == "gl"
    assert User._meta.get_field("preferred_language").default == ""
