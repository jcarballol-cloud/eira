# SPDX-License-Identifier: EUPL-1.2
"""App do operario (móbil, con cola sen conexión) e calendario compartido de mantemento."""

import calendar
import datetime as dt

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.tenants.uploads import clean_image
from apps.tenants.urlutils import role_required, treverse

from . import services
from .models import Frequency, MaintenancePlan, MaintenanceTask, WorkOrder, WorkOrderPhoto

STAFF = ("admin", "region_admin", "maintenance")


@role_required(*STAFF)
def my_orders(request):
    today = timezone.localdate()
    qs = WorkOrder.objects.for_tenant(request.tenant).select_related("facility", "incident")
    if "maintenance" in request.roles and request.GET.get("todas") != "1":
        from django.db.models import Q

        qs = qs.filter(Q(assigned_to=request.user) | Q(assigned_to__isnull=True))
    pending = qs.exclude(status=WorkOrder.Status.DONE).filter(due_date__lte=today + dt.timedelta(days=1)).order_by("due_date")
    done_today = qs.filter(status=WorkOrder.Status.DONE, closed_at__date=today)
    return render(request, "maintenance/my_orders.html", {
        "pending": pending, "done_today": done_today, "today": today, "nav": "operator",
    })


class CloseForm(forms.Form):
    closing_notes = forms.CharField(label=gettext_lazy("Notas de peche"), required=False, widget=forms.Textarea(attrs={"rows": 3}))
    photo = forms.ImageField(label=gettext_lazy("Foto do traballo feito"), required=False,
                             widget=forms.ClearableFileInput(attrs={"accept": "image/*", "capture": "environment"}))

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        return clean_image(photo) if photo else None


@role_required(*STAFF)
def order_detail(request, pk):
    order = get_object_or_404(WorkOrder.objects.select_related("facility", "incident"), municipality=request.tenant, pk=pk)
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
                if form.cleaned_data.get("photo"):
                    WorkOrderPhoto.objects.create(order=order, image=form.cleaned_data["photo"])
                services.close_order(order, request.user, form.cleaned_data["closing_notes"])
                if synced:
                    return HttpResponse(status=204)
                messages.success(request, _("Orde pechada. Bo traballo!"))
                return redirect(treverse(request.tenant, "maintenance:my_orders"))
            messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
        return redirect(treverse(request.tenant, "maintenance:order", order.pk))
    return render(request, "maintenance/order.html", {"order": order, "form": CloseForm(), "nav": "operator"})


@role_required(*STAFF)
def shared_calendar(request):
    today = timezone.localdate()
    try:
        month = dt.date.fromisoformat(request.GET.get("mes", "") + "-01") if request.GET.get("mes") else today.replace(day=1)
    except ValueError:
        month = today.replace(day=1)
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(month.year, month.month)
    first, last = weeks[0][0], weeks[-1][-1]
    orders = WorkOrder.objects.for_tenant(request.tenant).filter(due_date__range=(first, last)).select_related("facility")
    by_day = {}
    for o in orders:
        by_day.setdefault(o.due_date, []).append(o)
    prev_month = (month - dt.timedelta(days=1)).replace(day=1)
    next_month = (month + dt.timedelta(days=32)).replace(day=1)
    return render(request, "maintenance/calendar.html", {
        "weeks": [[(d, by_day.get(d, [])) for d in w] for w in weeks], "month": month, "today": today,
        "prev_month": prev_month, "next_month": next_month, "nav": "manage" if request.roles & {"admin", "region_admin"} else "operator",
        "sub": "maintenance",
    })


class TaskForm(forms.ModelForm):
    class Meta:
        model = MaintenanceTask
        fields = ["title", "frequency", "checklist", "start_date"]
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}), "checklist": forms.Textarea(attrs={"rows": 3})}


@role_required("admin", "region_admin")
def plans(request):
    plans_qs = MaintenancePlan.objects.for_tenant(request.tenant).select_related("facility").prefetch_related("tasks")
    form = TaskForm(request.POST or None)
    plan_id = request.POST.get("plan")
    if request.method == "POST" and request.POST.get("action") == "generate":
        n = services.generate_orders(days=int(request.POST.get("days", 14)), municipality=request.tenant)
        messages.success(request, _("Xeradas %(n)s ordes novas.") % {"n": n})
        return redirect(treverse(request.tenant, "manage:maintenance_plans"))
    if request.method == "POST" and plan_id and form.is_valid():
        plan = get_object_or_404(MaintenancePlan, municipality=request.tenant, pk=plan_id)
        task = form.save(commit=False)
        task.plan = plan
        task.save()
        messages.success(request, _("Tarefa engadida."))
        return redirect(treverse(request.tenant, "manage:maintenance_plans"))
    return render(request, "manage/maintenance_plans.html", {
        "plans": plans_qs, "form": form, "frequencies": Frequency.choices, "nav": "manage", "sub": "maintenance",
    })
