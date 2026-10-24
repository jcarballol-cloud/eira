# SPDX-License-Identifier: EUPL-1.2
"""v4: o concello redacta, previsualiza, programa e envía avisos (Xestión › Avisos)."""

import datetime as dt

from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.activities.models import Activity
from apps.facilities.models import Facility, Parish
from apps.tenants.urlutils import aggregate_view, role_required, treverse

from . import notices
from .models import CATEGORY_BASIS, INFO, Notice

ADMIN_ROLES = ("admin", "region_admin")
CHANNEL_CHOICES = [
    ("app", gettext_lazy("App e push")),
    ("email", gettext_lazy("Correo")),
    ("telegram", gettext_lazy("Telegram (bot persoal)")),
    ("channel", gettext_lazy("Canle pública de Telegram")),
]
DT = {"type": "datetime-local"}
DT_FORMAT = "%Y-%m-%dT%H:%M"


class NoticeForm(forms.ModelForm):
    channels = forms.MultipleChoiceField(
        label=gettext_lazy("Canles"),
        choices=CHANNEL_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        initial=["app", "email"],
    )

    class Meta:
        model = Notice
        fields = [
            "category",
            "title",
            "body",
            "url",
            "audience",
            "facility",
            "activity",
            "parish",
            "window_start",
            "window_end",
            "cancel_bookings",
            "channels",
            "publish_at",
        ]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 4}),
            "window_start": forms.DateTimeInput(attrs=DT, format=DT_FORMAT),
            "window_end": forms.DateTimeInput(attrs=DT, format=DT_FORMAT),
            "publish_at": forms.DateTimeInput(attrs=DT, format=DT_FORMAT),
        }
        help_texts = {
            "audience": gettext_lazy(
                "As reservas contan na franxa «desde–ata» (por defecto, os próximos 30 días)."
            ),
            "cancel_bookings": gettext_lazy(
                "Peche ou alerta: cancela con devolución íntegra as reservas da franxa."
            ),
            "publish_at": gettext_lazy("Baleiro = enviar agora."),
            "category": gettext_lazy(
                "Peches, alertas e cambios nas actividades chegan a quen lle afectan. Novas "
                "inscricións, horarios, festas e novidades, só a quen deu o consentimento."
            ),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.fields["facility"].queryset = Facility.objects.for_tenant(tenant)
        self.fields["activity"].queryset = Activity.objects.for_tenant(tenant)
        self.fields["parish"].queryset = Parish.objects.filter(municipality=tenant)
        if not tenant.telegram_channel:
            self.fields["channels"].choices = CHANNEL_CHOICES[:3]

    def clean(self):
        data = super().clean()
        aud = data.get("audience")
        needed = {
            Notice.Audience.FACILITY: "facility",
            Notice.Audience.ACTIVITY: "activity",
            Notice.Audience.PARISH: "parish",
        }.get(aud)
        if needed and not data.get(needed):
            self.add_error(needed, _("Escolle a quen vai dirixido."))
        if data.get("category") == "activity_change" and aud != Notice.Audience.ACTIVITY:
            self.add_error(
                "audience",
                _("Os cambios dunha actividade envíanse só ás persoas inscritas nela."),
            )
        if data.get("cancel_bookings"):
            if aud not in (
                Notice.Audience.FACILITY,
                Notice.Audience.OUTDOOR,
                Notice.Audience.PARISH,
            ):
                self.add_error(
                    "cancel_bookings",
                    _(
                        "Só se poden cancelar reservas dunha instalación, das descubertas ou dunha parroquia."
                    ),
                )
            if not (data.get("window_start") and data.get("window_end")):
                self.add_error(
                    "window_end", _("Para cancelar reservas indica a franxa (desde e ata).")
                )
        if (
            data.get("window_start")
            and data.get("window_end")
            and data["window_end"] <= data["window_start"]
        ):
            self.add_error("window_end", _("O fin debe ser posterior ao inicio."))
        if data.get("publish_at") and data["publish_at"] < timezone.now() - dt.timedelta(minutes=5):
            self.add_error("publish_at", _("A data de envío xa pasou."))
        return data


@role_required(*ADMIN_ROLES)
@aggregate_view
def notice_list(request):
    items = Notice.objects.filter(municipality=request.tenant).select_related(
        "facility", "activity", "parish"
    )[:100]
    return render(
        request,
        "manage/notices.html",
        {
            "notices": items,
            "nav": "manage",
            "sub": "notices",
            "scheduled": [n for n in items if n.sent_at is None],
        },
    )


@role_required("admin")
def notice_new(request):
    form = NoticeForm(request.POST or None, tenant=request.tenant)
    preview = None
    if request.method == "POST" and form.is_valid():
        notice = form.save(commit=False)
        notice.municipality = request.tenant
        notice.created_by = request.user
        if request.POST.get("action") == "send":
            notice.save()
            if notice.publish_at and notice.publish_at > timezone.now():
                messages.success(
                    request,
                    _("Aviso programado para o %(d)s.")
                    % {"d": timezone.localtime(notice.publish_at).strftime("%d/%m %H:%M")},
                )
            else:
                notices.send(notice, by=request.user)
                notice.refresh_from_db()
                messages.success(
                    request,
                    _("Aviso enviado a %(n)s persoas. Reservas canceladas: %(c)s.")
                    % {"n": notice.recipients, "c": notice.cancelled},
                )
            return redirect(treverse(request.tenant, "manage:notice", notice.pk))
        preview = {"content": notices.render(notice), "estimate": notices.estimate(notice)}
    return render(
        request,
        "manage/notice_new.html",
        {
            "form": form,
            "preview": preview,
            "nav": "manage",
            "sub": "notices",
            "info_categories": [c for c, b in CATEGORY_BASIS.items() if b == INFO],
        },
    )


@role_required(*ADMIN_ROLES)
@aggregate_view
def notice_detail(request, pk):
    notice = get_object_or_404(Notice, pk=pk, municipality=request.tenant)
    # A deputación (só lectura) pode ver o aviso, pero non envialo nin borralo
    if request.method == "POST" and notice.sent_at is None and "admin" in request.roles:
        if request.POST.get("action") == "send_now":
            notices.send(notice, by=request.user)
            messages.success(request, _("Aviso enviado."))
        elif request.POST.get("action") == "delete":
            notice.delete()
            messages.success(request, _("Aviso programado eliminado."))
            return redirect(treverse(request.tenant, "manage:notices"))
        return redirect(treverse(request.tenant, "manage:notice", notice.pk))
    return render(
        request,
        "manage/notice_detail.html",
        {
            "notice": notice,
            "content": notices.render(notice),
            "estimate": notices.estimate(notice) if notice.sent_at is None else None,
            "nav": "manage",
            "sub": "notices",
        },
    )
