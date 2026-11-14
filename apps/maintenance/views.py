# SPDX-License-Identifier: EUPL-1.2
"""App do operario (móbil, con cola sen conexión) e calendario compartido de mantemento."""

import calendar
import datetime as dt

from django import forms
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.accounts.freetext import hint
from apps.tenants.uploads import clean_image
from apps.tenants.urlutils import aggregate_view, role_required, treverse

from . import services
from .models import Frequency, MaintenancePlan, MaintenanceTask, WorkOrder, WorkOrderPhoto

OPERATOR = ("maintenance", "cleaning")


def operator_orders(request):
    """Ordes que ve o operario: as asignadas a el e as pendentes sen asignar (para collelas).

    v1.1: o persoal de limpeza só ve as de limpeza. Mantemento segue vendo todo, agás as de
    limpeza cando o concello xa ten persoal de limpeza (sen el, a limpeza segue sendo súa)."""
    from .cleaning import has_cleaning_staff

    qs = WorkOrder.objects.for_tenant(request.tenant).filter(
        Q(assigned_to=request.user) | Q(assigned_to__isnull=True)
    )
    if "maintenance" not in request.roles:
        return qs.filter(kind="cleaning")
    if has_cleaning_staff(request.tenant):
        qs = qs.exclude(Q(kind="cleaning") & ~Q(assigned_to=request.user))
    return qs


@role_required(*OPERATOR)
def my_orders(request):
    today = timezone.localdate()
    tomorrow = request.GET.get("dia") == "manha"  # v4.1: filtro «Hoxe» / «Mañá»
    qs = operator_orders(request).select_related("facility", "incident")
    pending = qs.exclude(status=WorkOrder.Status.DONE)
    if tomorrow:
        pending = pending.filter(due_date=today + dt.timedelta(days=1))
    else:
        pending = pending.filter(due_date__lte=today)
    done_today = qs.filter(status=WorkOrder.Status.DONE, closed_at__date=today)
    zones = []
    if "cleaning" in request.roles:
        # v1.1: zonas con QR, a súa última limpeza e se van atrasadas
        from .cleaning import zone_status
        from .models import CleaningZone

        zones = [
            zone_status(z)
            for z in CleaningZone.objects.for_tenant(request.tenant)
            .filter(active=True)
            .select_related("facility")
        ]
        zones.sort(key=lambda r: (not r["overdue"], r["zone"].facility.name, r["zone"].name))
    return render(
        request,
        "maintenance/my_orders.html",
        {
            "pending": pending.order_by("due_date", "slot"),
            "done_today": done_today,
            "today": today,
            "tomorrow": tomorrow,
            "zones": zones,
            "nav": "operator",
        },
    )


class CloseForm(forms.Form):
    closing_notes = forms.CharField(
        label=gettext_lazy("Notas de peche"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text=hint(),
    )
    photo = forms.ImageField(
        label=gettext_lazy("Foto do traballo feito"),
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": "image/*", "capture": "environment"}),
    )

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        return clean_image(photo) if photo else None


@role_required(*OPERATOR)
def order_detail(request, pk):
    order = get_object_or_404(
        operator_orders(request).select_related("facility", "incident"), pk=pk
    )
    synced = request.headers.get("X-Eira-Sync") == "1"
    if request.method == "POST":
        action = request.POST.get("action")
        if order.status == WorkOrder.Status.DONE and action in ("checklist", "close"):
            if synced:
                return HttpResponse(status=409)
            messages.info(request, _("Esta orde xa estaba pechada."))
            return redirect(treverse(request.tenant, "maintenance:order", order.pk))
        if action == "checklist":
            done = {int(i) for i in request.POST.getlist("done") if i.isdigit()}
            services.update_checklist(order, done)
            if synced:
                return HttpResponse(status=204)
            messages.success(request, _("Checklist gardado."))
        elif action == "close":
            form = CloseForm(request.POST, request.FILES)
            if form.is_valid():
                done = {int(i) for i in request.POST.getlist("done") if i.isdigit()}
                if done:
                    services.update_checklist(order, done)
                photo = None
                if form.cleaned_data.get("photo"):
                    photo = WorkOrderPhoto.objects.create(
                        order=order, image=form.cleaned_data["photo"]
                    ).image.name
                services.close_order(
                    order, request.user, form.cleaned_data["closing_notes"], photo=photo
                )
                if synced:
                    return HttpResponse(status=204)
                messages.success(request, _("Orde pechada. Bo traballo!"))
                return redirect(treverse(request.tenant, "maintenance:my_orders"))
            messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
        return redirect(treverse(request.tenant, "maintenance:order", order.pk))
    return render(
        request, "maintenance/order.html", {"order": order, "form": CloseForm(), "nav": "operator"}
    )


def _calendar(request, orders_qs, template, extra):
    today = timezone.localdate()
    try:
        month = (
            dt.date.fromisoformat(request.GET.get("mes", "") + "-01")
            if request.GET.get("mes")
            else today.replace(day=1)
        )
    except ValueError:
        month = today.replace(day=1)
    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(month.year, month.month)
    first, last = weeks[0][0], weeks[-1][-1]
    by_day = {}
    for o in orders_qs.filter(due_date__range=(first, last)).select_related("facility"):
        by_day.setdefault(o.due_date, []).append(o)
    return render(
        request,
        template,
        {
            "weeks": [[(d, by_day.get(d, [])) for d in w] for w in weeks],
            "month": month,
            "today": today,
            "prev_month": (month - dt.timedelta(days=1)).replace(day=1),
            "next_month": (month + dt.timedelta(days=32)).replace(day=1),
            **extra,
        },
    )


@role_required(*OPERATOR)
def operator_calendar(request):
    """Calendario do operario: só as súas ordes e as pendentes sen asignar."""
    return _calendar(
        request,
        operator_orders(request),
        "maintenance/calendar.html",
        {"nav": "operator_calendar", "order_url": "maintenance:order"},
    )


@role_required("admin", "region_admin")
def manage_calendar(request):
    """Calendario compartido de mantemento para a administración (todas as ordes)."""
    return _calendar(
        request,
        WorkOrder.objects.for_tenant(request.tenant),
        "manage/maintenance_calendar.html",
        {"nav": "manage", "sub": "maintenance", "order_url": "manage:work_order"},
    )


class AssignForm(forms.Form):
    assigned_to = forms.ModelChoiceField(
        label=gettext_lazy("Asignar a"), queryset=None, required=False
    )
    due_date = forms.DateField(
        label=gettext_lazy("Data prevista"), widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import Membership, Role, User

        # v1.1: tamén o persoal de limpeza (as ordes de limpeza van para el)
        ids = Membership.objects.filter(
            municipality=tenant, role__in=[Role.MAINTENANCE, Role.CLEANING]
        ).values_list("user_id", flat=True)
        self.fields["assigned_to"].queryset = User.objects.filter(pk__in=ids)
        self.fields["assigned_to"].empty_label = gettext_lazy("Sen asignar")


@role_required("admin", "region_admin")
def manage_orders(request):
    status = request.GET.get("estado", "pendentes")
    qs = WorkOrder.objects.for_tenant(request.tenant).select_related(
        "facility", "assigned_to", "incident"
    )
    if status == "pendentes":
        qs = qs.exclude(status=WorkOrder.Status.DONE)
    elif status in WorkOrder.Status.values:
        qs = qs.filter(status=status)
    return render(
        request,
        "manage/work_orders.html",
        {
            "orders": qs.order_by("due_date")[:300],
            "status": status,
            "statuses": WorkOrder.Status.choices,
            "nav": "manage",
            "sub": "work_orders",
        },
    )


@role_required("admin", "region_admin")
def manage_order(request, pk):
    order = get_object_or_404(
        WorkOrder.objects.select_related("facility", "incident", "assigned_to"),
        municipality=request.tenant,
        pk=pk,
    )
    form = AssignForm(
        request.POST or None,
        tenant=request.tenant,
        initial={"assigned_to": order.assigned_to_id, "due_date": order.due_date},
    )
    if request.method == "POST" and form.is_valid():
        order.assigned_to = form.cleaned_data["assigned_to"]
        order.due_date = form.cleaned_data["due_date"]
        order.save(update_fields=["assigned_to", "due_date"])
        if order.assigned_to:
            from apps.notifications.services import notify

            notify(
                order.assigned_to,
                _("Nova orde de traballo: %(t)s") % {"t": order.title},
                order.facility.name,
                url=treverse(request.tenant, "maintenance:order", order.pk),
                municipality=request.tenant,
            )
        messages.success(request, _("Orde actualizada."))
        return redirect(treverse(request.tenant, "manage:work_order", order.pk))
    return render(
        request,
        "manage/work_order.html",
        {"order": order, "form": form, "nav": "manage", "sub": "work_orders"},
    )


class TaskForm(forms.ModelForm):
    class Meta:
        model = MaintenanceTask
        fields = ["title", "frequency", "checklist", "start_date"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "checklist": forms.Textarea(attrs={"rows": 3}),
        }


@role_required("admin", "region_admin")
@aggregate_view
def plans(request):
    plans_qs = (
        MaintenancePlan.objects.for_tenant(request.tenant)
        .select_related("facility")
        .prefetch_related("tasks")
    )
    form = TaskForm(request.POST or None)
    plan_id = request.POST.get("plan")
    if request.method == "POST" and request.POST.get("action") == "generate":
        n = services.generate_orders(
            days=int(request.POST.get("days", 14)), municipality=request.tenant
        )
        messages.success(request, _("Xeradas %(n)s ordes novas.") % {"n": n})
        return redirect(treverse(request.tenant, "manage:maintenance_plans"))
    if request.method == "POST" and plan_id and form.is_valid():
        plan = get_object_or_404(MaintenancePlan, municipality=request.tenant, pk=plan_id)
        task = form.save(commit=False)
        task.plan = plan
        task.save()
        messages.success(request, _("Tarefa engadida."))
        return redirect(treverse(request.tenant, "manage:maintenance_plans"))
    return render(
        request,
        "manage/maintenance_plans.html",
        {
            "plans": plans_qs,
            "form": form,
            "frequencies": Frequency.choices,
            "nav": "manage",
            "sub": "maintenance",
        },
    )
