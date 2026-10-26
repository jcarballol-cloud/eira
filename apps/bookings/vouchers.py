# SPDX-License-Identifier: EUPL-1.2
"""v5 · Bonos: tipos (concello), venda na oficina e compra en liña co TPV do concello."""

from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.accounts.models import User, audit
from apps.facilities.models import Facility
from apps.tenants.urlutils import neighbour_required, role_required, treverse

from . import payments
from .models import Payment, Voucher, VoucherType

ADMIN_ROLES = ("admin", "region_admin")


class VoucherTypeForm(forms.ModelForm):
    class Meta:
        model = VoucherType
        fields = ["name", "facility", "uses", "price_cents", "valid_days", "active"]

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["facility"].queryset = Facility.objects.for_tenant(tenant)
        self.fields["facility"].empty_label = _("Todas as que admitan bono")


class SellForm(forms.Form):
    type = forms.ModelChoiceField(label=gettext_lazy("Bono"), queryset=VoucherType.objects.none())
    email = forms.EmailField(
        label=gettext_lazy("Correo da persoa"),
        help_text=gettext_lazy("O bono queda na súa conta da app."),
    )
    method = forms.ChoiceField(
        label=gettext_lazy("Cobro"),
        choices=[
            (Payment.Method.CASH, gettext_lazy("Efectivo")),
            (Payment.Method.CARD_TERMINAL, gettext_lazy("Tarxeta no TPV físico")),
        ],
        widget=forms.RadioSelect,
        initial=Payment.Method.CASH,
    )

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].queryset = VoucherType.objects.for_tenant(tenant).filter(active=True)

    def clean_email(self):
        user = User.objects.filter(email=self.cleaned_data["email"].lower()).first()
        if user is None:
            raise forms.ValidationError(_("Non hai ningunha conta con ese correo."))
        return user


@role_required(*ADMIN_ROLES)
def manage_vouchers(request):
    tenant = request.tenant
    type_form = VoucherTypeForm(
        request.POST if request.POST.get("action") == "type" else None, tenant=tenant
    )
    sell_form = SellForm(
        request.POST if request.POST.get("action") == "sell" else None, tenant=tenant
    )
    if request.method == "POST":
        if request.POST.get("action") == "type" and type_form.is_valid():
            vt = type_form.save(commit=False)
            vt.municipality = tenant
            vt.save()
            audit("voucher_type.create", request.user, tenant, vt)
            messages.success(request, _("Bono creado."))
            return redirect(treverse(tenant, "manage:vouchers"))
        if request.POST.get("action") == "sell" and sell_form.is_valid():
            d = sell_form.cleaned_data
            v = payments.sell_voucher(d["type"], d["email"], method=d["method"], by=request.user)
            messages.success(
                request,
                _("Bono vendido a %(p)s: %(u)s usos.") % {"p": d["email"], "u": v.uses_total},
            )
            return redirect(treverse(tenant, "manage:vouchers"))
    return render(
        request,
        "manage/vouchers.html",
        {
            "types": VoucherType.objects.for_tenant(tenant).select_related("facility"),
            "vouchers": Voucher.objects.for_tenant(tenant)
            .select_related("type", "user")
            .exclude(status=Voucher.Status.PENDING)[:100],
            "type_form": type_form,
            "sell_form": sell_form,
            "nav": "manage",
            "sub": "payments",
        },
    )


@neighbour_required
def my_vouchers(request):
    """Os meus bonos e os que se poden comprar co TPV do concello."""
    tenant = request.tenant
    if request.method == "POST":
        vt = get_object_or_404(
            VoucherType, municipality=tenant, pk=request.POST.get("type"), active=True
        )
        v = payments.sell_voucher(vt, request.user)
        back = treverse(tenant, "bookings:vouchers")
        return redirect(
            payments.start_online_payment(
                voucher=v, url_ok=back + "?resultado=ok", url_ko=back + "?resultado=ko"
            )
        )
    return render(
        request,
        "bookings/vouchers.html",
        {
            "vouchers": Voucher.objects.filter(user=request.user, municipality=tenant)
            .exclude(status=Voucher.Status.PENDING)
            .select_related("type", "type__facility"),
            "types": VoucherType.objects.for_tenant(tenant)
            .filter(active=True)
            .select_related("facility"),
            "returned": request.GET.get("resultado", ""),
            "nav": "bookings",
        },
    )
