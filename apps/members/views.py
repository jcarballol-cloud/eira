# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · H: carné na app (QR dinámico), carné imprimible, abonos e lector do persoal."""

from django import forms
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST

from apps.accounts.models import User, audit
from apps.tenants.urlutils import neighbour_required, role_required, treverse

from . import services
from .models import MemberCard, PassType, SportsPass


def _module(request):
    if not request.tenant.module_enabled("cards"):
        raise Http404


def _qr_context(card):
    from apps.access.views import qr_svg

    token = services.live_token(card)
    return {
        "card": card,
        "qr": qr_svg(token),
        "token": token,
        "valid_seconds": services.CARD_QR_SECONDS,
        "generated": timezone.now(),
    }


class PhotoForm(forms.Form):
    photo = forms.ImageField(label=gettext_lazy("Foto (opcional)"), required=False)


@neighbour_required
def card(request):
    _module(request)
    t = request.tenant
    c = services.ensure_card(t, request.user)
    if request.method == "POST":
        action = request.POST.get("accion")
        if action == "abono":
            pt = get_object_or_404(
                PassType, municipality=t, pk=request.POST.get("tipo"), active=True
            )
            p = services.buy_pass(pt, request.user)
            from apps.bookings.payments import start_online_payment

            back = treverse(t, "members:card")
            return redirect(
                start_online_payment(
                    sports_pass=p, url_ok=back + "?resultado=ok", url_ko=back + "?resultado=ko"
                )
            )
        if action == "foto":
            form = PhotoForm(request.POST, request.FILES)
            if form.is_valid() and form.cleaned_data["photo"]:
                from apps.tenants.uploads import clean_image

                try:
                    c.photo.save(f"carne-{c.number}.jpg", clean_image(form.cleaned_data["photo"]))
                except forms.ValidationError as exc:
                    messages.error(request, " ".join(exc.messages))
                else:
                    messages.success(request, _("Foto gardada no teu carné."))
            return redirect(treverse(t, "members:card"))
        if action == "sen-foto" and c.photo:
            c.photo.delete(save=False)
            c.photo = ""
            c.save(update_fields=["photo"])
            messages.success(request, _("Quitamos a foto do teu carné."))
            return redirect(treverse(t, "members:card"))
    return render(
        request,
        "members/card.html",
        {
            **_qr_context(c),
            "pass": services.active_pass(t, request.user),
            "history": SportsPass.objects.filter(municipality=t, user=request.user).select_related(
                "type"
            )[:5],
            "types": PassType.objects.filter(municipality=t, active=True),
            "vouchers": request.user.vouchers.filter(
                municipality=t, status="active"
            ).select_related("type"),
            "returned": request.GET.get("resultado", ""),
            "photo_form": PhotoForm(),
            "nav": "card",
        },
    )


@neighbour_required
def card_qr(request):
    """Fragmento HTMX: QR novo (a páxina pídeo cada minuto)."""
    _module(request)
    c = services.ensure_card(request.tenant, request.user)
    return render(request, "members/_qr.html", _qr_context(c))


@neighbour_required
def card_pdf(request):
    """Carné imprimible (PDF etiquetado, tamaño tarxeta) para quen non usa o móbil."""
    _module(request)
    from .pdf import build_card

    c = services.ensure_card(request.tenant, request.user)
    p = services.active_pass(request.tenant, request.user)
    response = HttpResponse(build_card(c, p), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="carne-{c.number}.pdf"'
    return response


# ---------------------------------------------------------------- xestión
class PassTypeForm(forms.ModelForm):
    class Meta:
        model = PassType
        fields = [
            "name",
            "kind",
            "price_cents",
            "valid_days",
            "discount_pct",
            "description",
            "active",
        ]


class SellForm(forms.Form):
    email = forms.CharField(label=gettext_lazy("Correo da persoa"), max_length=254)
    type = forms.ModelChoiceField(label=gettext_lazy("Abono"), queryset=PassType.objects.none())
    method = forms.ChoiceField(
        label=gettext_lazy("Cobro"),
        choices=[
            ("cash", gettext_lazy("Efectivo")),
            ("card_terminal", gettext_lazy("Tarxeta no TPV físico")),
        ],
    )

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].queryset = PassType.objects.filter(municipality=tenant, active=True)


@role_required("admin", "region_admin")
def manage_passes(request):
    _module(request)
    t = request.tenant
    type_form = PassTypeForm(
        request.POST if request.POST.get("accion") == "tipo" else None, prefix="t"
    )
    sell_form = SellForm(
        request.POST if request.POST.get("accion") == "vender" else None, tenant=t, prefix="v"
    )
    if request.method == "POST" and "admin" in request.roles:
        if request.POST.get("accion") == "tipo" and type_form.is_valid():
            pt = type_form.save(commit=False)
            pt.municipality = t
            pt.save()
            audit("pass_type.create", request.user, t, pt)
            messages.success(request, _("Tipo de abono creado."))
            return redirect(treverse(t, "manage:passes"))
        if request.POST.get("accion") == "vender" and sell_form.is_valid():
            person = User.objects.filter(email__iexact=sell_form.cleaned_data["email"]).first()
            if person is None:
                sell_form.add_error("email", _("Non hai ningunha conta con ese correo."))
            else:
                p = services.buy_pass(
                    sell_form.cleaned_data["type"],
                    person,
                    method=sell_form.cleaned_data["method"],
                    by=request.user,
                )
                messages.success(
                    request,
                    _("Abono activo ata o %(d)s.") % {"d": p.expires_on.strftime("%d/%m/%Y")},
                )
                return redirect(treverse(t, "manage:passes"))
        if request.POST.get("accion") == "alternar":
            pt = get_object_or_404(PassType, municipality=t, pk=request.POST.get("tipo"))
            pt.active = not pt.active
            pt.save(update_fields=["active"])
            return redirect(treverse(t, "manage:passes"))
    today = timezone.localdate()
    passes = SportsPass.objects.filter(municipality=t).select_related("type", "user")
    return render(
        request,
        "manage/passes.html",
        {
            "types": PassType.objects.filter(municipality=t),
            "passes": passes[:30],
            "active_count": passes.filter(status="active", expires_on__gte=today).count(),
            "type_form": type_form,
            "sell_form": sell_form,
            "nav": "manage",
            "sub": "passes",
        },
    )


@role_required("admin", "maintenance")
def reader(request):
    """Lector do carné para o persoal: escanear (ou pegar) o QR e ver abono, bonos e reserva."""
    _module(request)
    status, error = None, None
    token = request.POST.get("qr", "") or request.GET.get("qr", "")
    if token:
        try:
            c = services.read_token(token, request.tenant)
        except services.CardError as exc:
            error = str(exc)
        else:
            if request.method == "POST" and request.POST.get("accion") == "entrada":
                try:
                    b = services.checkin_with_card(c, by=request.user)
                    messages.success(
                        request, _("Entrada rexistrada: %(f)s.") % {"f": b.facility.name}
                    )
                except services.CardError as exc:
                    error = str(exc)
            status = services.card_status(c)
    return render(
        request,
        "manage/card_reader.html",
        {"status": status, "error": error, "token": token, "nav": "manage", "sub": "passes"},
    )


@role_required("admin")
@require_POST
def revoke(request, pk):
    c = get_object_or_404(MemberCard, municipality=request.tenant, pk=pk)
    services.revoke_printed(c, by=request.user)
    messages.success(request, _("O carné impreso anterior xa non vale."))
    return redirect(treverse(request.tenant, "manage:card_reader"))


@role_required("monitor")
@require_POST
def monitor_card(request, pk):
    """Tableta: ler o carné marca presente á persoa (ou ás crianzas que ten inscritas no grupo).
    A lista por nome (o «abecedario») segue igual; isto é unha alternativa."""
    from apps.activities.models import Attendance, Session

    session = get_object_or_404(
        Session, pk=pk, group__municipality=request.tenant, group__monitor=request.user
    )
    back = treverse(request.tenant, "monitor:attendance", session.pk)
    try:
        c = services.read_token(request.POST.get("qr", ""), request.tenant)
    except services.CardError as exc:
        messages.error(request, str(exc))
        return redirect(back)
    enrolled = session.group.enrolled().select_related("dependent", "user")
    mine = [e for e in enrolled if e.user_id == c.user_id and e.dependent_id is None]
    if not mine:
        household = getattr(c.user, "household", None)
        mine = [
            e
            for e in enrolled
            if household and e.dependent and e.dependent.household_id == household.pk
        ]
    if not mine:
        messages.error(request, _("Este carné non ten ninguén inscrito neste grupo."))
        return redirect(back)
    for e in mine:
        Attendance.objects.update_or_create(
            session=session,
            enrollment=e,
            defaults={"present": True, "minutes": session.duration_minutes},
        )
    messages.success(
        request,
        _("Presente: %(n)s") % {"n": ", ".join(e.participant_name for e in mine)},
    )
    return redirect(back)
