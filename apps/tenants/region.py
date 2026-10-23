# SPDX-License-Identifier: EUPL-1.2
"""Vista de deputación/mancomunidade: comparativa entre concellos e alta dun concello novo en 3 pasos."""

from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.accounts.models import Membership, Role, User, audit
from apps.analytics.indicators import summary
from apps.facilities.catalog import TEMPLATES, apply_template
from apps.facilities.models import Facility

from .models import DEFAULT_MODULES, Municipality, Region
from .urlutils import treverse


def region_admin_required(view):
    @wraps(view)
    def wrapper(request, region, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        obj = get_object_or_404(Region, slug=region)
        if not (
            request.user.is_superuser or request.user.region_memberships.filter(region=obj).exists()
        ):
            raise PermissionDenied
        request.region = obj
        return view(request, *args, **kwargs)

    return wrapper


@region_admin_required
def dashboard(request):
    rows = []
    for m in request.region.municipalities.filter(is_active=True):
        s = summary(m, weeks=4)
        rows.append(
            {
                "m": m,
                "facilities": Facility.objects.for_tenant(m).count(),
                "bookings": s["booked"],
                "occupancy": s["occupancy_pct"],
                "no_show_pct": s["no_show_pct"],
                "open_incidents": s["incidents"]["open"],
                "revenue": s["revenue_cents"],
                "underused": len(s["underused"]),
                "per_1000": round(1000 * s["booked"] / m.population, 1) if m.population else None,
            }
        )
    return render(
        request, "region/dashboard.html", {"region": request.region, "rows": rows, "nav": "region"}
    )


class StepBasics(forms.Form):
    name = forms.CharField(label=gettext_lazy("Nome do concello"), max_length=120)
    slug = forms.SlugField(
        label=gettext_lazy("Identificador na URL"),
        help_text=gettext_lazy("Só minúsculas, números e guións."),
    )
    ine_code = forms.CharField(label=gettext_lazy("Código INE"), max_length=5, required=False)
    population = forms.IntegerField(label=gettext_lazy("Poboación"), required=False, min_value=0)
    accent_color = forms.CharField(
        label=gettext_lazy("Cor de acento"),
        initial="#2E6A4F",
        widget=forms.TextInput(attrs={"type": "color"}),
    )

    def clean_slug(self):
        slug = self.cleaned_data["slug"]
        if Municipality.objects.filter(slug=slug).exists():
            raise forms.ValidationError(_("Xa existe un concello con ese identificador."))
        return slug


class StepModules(forms.Form):
    modules = forms.MultipleChoiceField(
        label=gettext_lazy("Módulos activos"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[(k, k) for k in DEFAULT_MODULES],
    )
    cancellation_hours = forms.IntegerField(
        label=gettext_lazy("Horas para cancelar sen penalización"), initial=24, min_value=0
    )
    max_advance_days = forms.IntegerField(
        label=gettext_lazy("Días máximos de antelación"), initial=14, min_value=1
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .manage import MODULE_LABELS

        self.fields["modules"].choices = list(MODULE_LABELS.items())
        self.fields["modules"].initial = [k for k, v in DEFAULT_MODULES.items() if v]


class StepAdmin(forms.Form):
    admin_email = forms.EmailField(
        label=gettext_lazy("Correo da persoa administradora do concello")
    )
    templates = forms.MultipleChoiceField(
        label=gettext_lazy("Crear instalacións de exemplo a partir de plantillas"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[(k, t["label"]) for k, t in TEMPLATES.items()],
    )


STEPS = [StepBasics, StepModules, StepAdmin]


@region_admin_required
def new_municipality(request):
    step = int(request.POST.get("step", request.GET.get("paso", 1)))
    step = min(max(step, 1), 3)
    data = request.session.get("new_municipality", {})
    form = STEPS[step - 1](
        request.POST if request.method == "POST" else None, initial=data.get(str(step))
    )
    if request.method == "POST" and form.is_valid():
        data[str(step)] = form.cleaned_data
        request.session["new_municipality"] = data
        if step < 3:
            return redirect(f"{request.path}?paso={step + 1}")
        b, mods = data["1"], data["2"]
        m = Municipality.objects.create(
            name=b["name"],
            slug=b["slug"],
            ine_code=b.get("ine_code", ""),
            population=b.get("population"),
            accent_color=b.get("accent_color") or "#2E6A4F",
            region=request.region,
            modules={k: k in mods.get("modules", []) for k in DEFAULT_MODULES},
            cancellation_hours=mods["cancellation_hours"],
            max_advance_days=mods["max_advance_days"],
        )
        admin, _c = User.objects.get_or_create(email=form.cleaned_data["admin_email"].lower())
        Membership.objects.get_or_create(user=admin, municipality=m, role=Role.ADMIN)
        for key in form.cleaned_data["templates"]:
            f = Facility.objects.create(
                municipality=m,
                name=str(TEMPLATES[key]["label"]),
                kind=TEMPLATES[key]["kind"],
                capacity=TEMPLATES[key]["capacity"],
                slot_minutes=TEMPLATES[key]["slot_minutes"],
                access_level=TEMPLATES[key]["access_level"],
                indoor=TEMPLATES[key]["indoor"],
                lighting=TEMPLATES[key]["lighting"],
                is_published=False,
                key_holder_name=_("Concello") if TEMPLATES[key]["access_level"] == 1 else "",
            )
            apply_template(f, key, request.user)
        audit("tenant.create", request.user, m, m)
        request.session.pop("new_municipality", None)
        messages.success(
            request, _("Concello %(n)s creado. Xa podes entrar na súa xestión.") % {"n": m.name}
        )
        return redirect(treverse(m, "manage:dashboard"))
    return render(
        request,
        "region/new_municipality.html",
        {"region": request.region, "form": form, "step": step, "data": data, "nav": "region_new"},
    )
