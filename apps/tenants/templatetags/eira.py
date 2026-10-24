# SPDX-License-Identifier: EUPL-1.2
from django import template
from django.templatetags.static import static
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime

register = template.Library()


@register.simple_tag(takes_context=True)
def turl(context, name, *args):
    """{% turl 'bookings:detail' booking.pk %} → /c/<slug>/reservas/<pk>/"""
    tenant = context.get("tenant")
    slug = getattr(tenant, "slug", None) or context.get("tenant_slug")
    return reverse(name, args=[slug, *args])


@register.simple_tag
def icon(name, css="icon"):
    """Icona decorativa do sprite propio (oculta aos lectores de pantalla)."""
    href = static("img/icons.svg") + "#" + escape(name)
    return mark_safe(
        f'<svg class="{escape(css)}" aria-hidden="true" focusable="false"><use href="{href}"></use></svg>'
    )


@register.filter
def a11y(bound_field):
    """Renderiza o widget enlazando axuda e erros con aria-describedby e marcando aria-invalid."""
    describedby = []
    if bound_field.help_text:
        describedby.append(f"{bound_field.auto_id}_help")
    if bound_field.errors:
        describedby.append(f"{bound_field.auto_id}_errors")
    attrs = {}
    if describedby:
        attrs["aria-describedby"] = " ".join(describedby)
    if bound_field.errors:
        attrs["aria-invalid"] = "true"
    return bound_field.as_widget(attrs=attrs)


@register.filter
def is_checkbox(bound_field):
    return getattr(bound_field.field.widget, "input_type", None) == "checkbox"


@register.filter
def is_multiple(bound_field):
    return bound_field.field.widget.__class__.__name__ in ("CheckboxSelectMultiple", "RadioSelect")


@register.filter
def euros(cents):
    if cents is None:
        return ""
    value = f"{int(cents) / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{value} €"


@register.filter
def hhmm(dt):
    return localtime(dt).strftime("%H:%M") if dt else ""


@register.filter
def longdate(dt):
    if not dt:
        return ""
    if hasattr(dt, "tzinfo"):
        try:
            dt = localtime(dt)
        except ValueError:
            pass
    return date_format(dt, "l j \\d\\e F")


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except AttributeError:
        return None


@register.filter
def bucket5(value):
    """Redondea unha porcentaxe ao múltiplo de 5 (para as clases .w-N, sen estilos en liña)."""
    try:
        return min(100, max(0, int(round(float(value) / 5) * 5)))
    except (TypeError, ValueError):
        return 0


@register.filter
def pct(value, total):
    try:
        return round(100 * float(value) / float(total)) if total else 0
    except (TypeError, ValueError):
        return 0


@register.inclusion_tag("includes/facility_photo.html")
def facility_photo(facility, sizes="(min-width: 700px) 360px, 100vw", caption=False, eager=False):
    from apps.facilities.photos import photo_for

    return {"p": photo_for(facility), "sizes": sizes, "caption": caption, "eager": eager}


@register.filter
def signed(value):
    """Variación con signo explícito e menos tipográfico: +37, −2,9 (v4: mesmo formato en todas partes)."""
    if value is None:
        return ""
    from django.utils.formats import number_format

    text = number_format(abs(value), use_l10n=True)
    return ("+" if value > 0 else "−" if value < 0 else "") + text


@register.filter
def tg_markdown(text):
    """Mínimo do Markdown de Telegram para o simulador: *negra* e saltos de liña (escapado)."""
    import re

    from django.utils.html import escape
    from django.utils.safestring import mark_safe

    html = re.sub(r"\*([^*\n]+)\*", r"<strong>\1</strong>", escape(text or ""))
    return mark_safe(html.replace("\n", "<br>"))


@register.filter
def channel_labels(value):
    """«app,email,telegram» → «App · Correo · Telegram»."""
    from django.utils.translation import gettext as _

    names = {"app": "App", "email": _("Correo"), "telegram": "Telegram", "push": "Push"}
    return " · ".join(names.get(c, c) for c in (value or "").split(",") if c)


@register.filter
def code_groups(code):
    """Parte un código numérico en grupos de 3 («163120» → ["163", "120"]) para que caiba en móbil."""
    code = str(code or "")
    return [code[i : i + 3] for i in range(0, len(code), 3)]
