# SPDX-License-Identifier: EUPL-1.2
from django.apps import AppConfig


def remember_language_on_login(sender, request, user, **kwargs):
    """Quen escolleu idioma antes de entrar e non ten ningún no perfil: gárdase no perfil."""
    from django.conf import settings

    from apps.tenants.language import valid

    if settings.EIRA_PUBLIC_DEMO:  # contas compartidas: só a cookie
        return
    code = valid(request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME, "")) if request else ""
    if code and not valid(user.preferred_language):
        user.preferred_language = code
        user.save(update_fields=["preferred_language"])


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    label = "accounts"

    def ready(self):
        from django.contrib.auth.signals import user_logged_in

        user_logged_in.connect(remember_language_on_login, dispatch_uid="eira-language-on-login")
