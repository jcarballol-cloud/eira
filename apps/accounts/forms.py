# SPDX-License-Identifier: EUPL-1.2
from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Consent, Dependent, User


class EmailForm(forms.Form):
    email = forms.EmailField(
        label=_("Correo electrónico"),
        widget=forms.EmailInput(
            attrs={"autocomplete": "email", "inputmode": "email", "autofocus": True}
        ),
        help_text=_("Enviarémosche un código de 6 díxitos. Non necesitas contrasinal."),
    )


class CodeForm(forms.Form):
    code = forms.CharField(
        label=_("Código de 6 díxitos"),
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]{6}",
                "class": "input-code",
                "autofocus": True,
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit():
            raise forms.ValidationError(_("O código só ten números."))
        return code


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "display_name",
            "phone",
            "birth_year",
            "preferred_language",
            "telegram_chat",
        ]
        widgets = {
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
            "display_name": forms.TextInput(attrs={"autocomplete": "nickname"}),
            "preferred_language": forms.Select(choices=[("gl", "Galego"), ("es", "Castellano")]),
        }
        help_texts = {
            "birth_year": _("Opcional. Só o ano, para aplicar tarifas por idade."),
            "telegram_chat": _("Opcional. Identificador do chat co bot do concello."),
        }

    def clean_birth_year(self):
        year = self.cleaned_data.get("birth_year")
        if year and not (1900 <= year <= timezone.localdate().year):
            raise forms.ValidationError(_("Ano non válido."))
        return year


class DependentForm(forms.ModelForm):
    consent_data = forms.BooleanField(
        label=_("Autorizo o tratamento dos datos necesarios para a súa inscrición en actividades."),
        required=True,
    )
    consent_image = forms.BooleanField(
        label=_("Autorizo o uso da súa imaxe en comunicacións municipais."), required=False
    )
    consent_performance = forms.BooleanField(
        label=_("Autorizo rexistrar o esforzo percibido e as probas físicas da actividade."),
        required=False,
    )

    minor_agrees = forms.BooleanField(
        label=_("Ten 14 anos ou máis e está de acordo con estes consentimentos."),
        required=False,
        help_text=_(
            "A partir dos 14 anos a lei permite que consinta por si mesmo/a (art. 7 LOPDGDD)."
        ),
    )

    class Meta:
        model = Dependent
        fields = ["first_name", "birth_year"]
        help_texts = {"first_name": _("Só o nome; non pedimos apelidos.")}

    def clean_birth_year(self):
        year = self.cleaned_data["birth_year"]
        this_year = timezone.localdate().year
        if not (this_year - 17 <= year <= this_year):
            raise forms.ValidationError(_("Só se poden engadir menores de idade."))
        return year

    def clean(self):
        d = super().clean()
        year = d.get("birth_year")
        if year and timezone.localdate().year - year >= 14 and not d.get("minor_agrees"):
            self.add_error(
                "minor_agrees",
                _("Con 14 anos ou máis, confirma que o/a menor está de acordo cos consentimentos."),
            )
        return d


CONSENT_FIELDS = {
    "consent_data": Consent.Kind.DATA,
    "consent_image": Consent.Kind.IMAGE,
    "consent_performance": Consent.Kind.PERFORMANCE,
}


class ResidencyCodeForm(forms.Form):
    code = forms.CharField(
        label=_("Código de empadroamento"),
        max_length=12,
        help_text=_("Facilítao o concello no mostrador ou por carta (p. ex. ABCD-2345)."),
    )


class DeleteAccountForm(forms.Form):
    confirm = forms.BooleanField(
        label=_("Entendo que se eliminarán os meus datos e non se pode desfacer.")
    )


class PrivacyForm(forms.ModelForm):
    """Interruptores do centro de privacidade (cada un, revogable en calquera momento)."""

    class Meta:
        model = User
        fields = ["notify_email", "notify_telegram", "photo_consent"]
        labels = {
            "notify_email": _("Avisos por correo (reservas, cambios e peches)"),
            "notify_telegram": _("Avisos por Telegram"),
            "photo_consent": _(
                "Poden saír fotos miñas nas actividades e nas comunicacións do concello"
            ),
        }
        help_texts = {
            "photo_consent": _(
                "Se non o marcas, o monitor verá unha cámara riscada xunto ao teu nome."
            ),
        }
