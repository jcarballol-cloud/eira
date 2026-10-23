# SPDX-License-Identifier: EUPL-1.2
"""Vista de deputación/mancomunidade: comparativa entre concellos (con tendencia e satisfacción)
e alta dun concello novo paso a paso: datos, persoa responsable, módulos, imaxe, primeira
instalación e invitación."""

import datetime as dt
from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST

from apps.accounts.models import AuditLog, Membership, Role, User, audit
from apps.analytics.indicators import hbar, summary
from apps.bookings import ratings
from apps.facilities.catalog import TEMPLATES, apply_template
from apps.facilities.models import AccessLevel, Facility, Parish
from apps.facilities.photos import make_variants
from apps.integrations.registry import get_adapter

from .models import DEFAULT_MODULES, Municipality, Region
from .uploads import clean_image
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


def _delta(now, before):
    if now is None or before is None:
        return None
    return round(now - before, 1)


def compare(region, weeks=4):
    """Indicadores por concello no período e variación fronte ao período anterior."""
    today = timezone.localdate()
    rows = []
    for m in region.municipalities.filter(is_active=True).order_by("name"):
        s = summary(m, weeks=weeks)
        prev = summary(m, weeks=weeks, today=today - dt.timedelta(weeks=weeks))
        rs = ratings.stats(m, days=7 * weeks)
        per_1000 = round(1000 * s["booked"] / m.population, 1) if m.population else None
        prev_1000 = round(1000 * prev["booked"] / m.population, 1) if m.population else None
        admin = (
            Membership.objects.filter(municipality=m, role=Role.ADMIN)
            .select_related("user")
            .first()
        )
        invited = (
            AuditLog.objects.filter(municipality=m, action="tenant.invite").order_by("-at").first()
        )
        rows.append(
            {
                "m": m,
                "facilities": Facility.objects.for_tenant(m).count(),
                "bookings": s["booked"],
                "bookings_delta": s["booked"] - prev["booked"],
                "occupancy": s["occupancy_pct"],
                "occupancy_delta": s["occupancy_pct"] - prev["occupancy_pct"],
                "no_show_pct": s["no_show_pct"],
                "open_incidents": s["incidents"]["open"],
                "resolve_hours": s["incidents"]["avg_hours"],
                "revenue": s["revenue_cents"],
                "revenue_per_inh": round(s["revenue_cents"] / 100 / m.population, 2)
                if m.population
                else None,
                "underused": len(s["underused"]),
                "per_1000": per_1000,
                "per_1000_delta": _delta(per_1000, prev_1000),
                "satisfaction": rs["index"],
                "ratings": rs["total"],
                "admin": admin.user if admin else None,
                "invited_at": invited.at if invited else None,
            }
        )
    return rows


@region_admin_required
def dashboard(request):
    from apps.analytics.views import _csv

    rows = compare(request.region)
    if request.GET.get("csv") or request.GET.get("ods"):
        return _csv(
            "rede-concellos.csv",
            [
                "concello",
                "instalacions",
                "reservas",
                "reservas_por_1000_hab",
                "ocupacion_pct",
                "non_presentadas_pct",
                "satisfaccion_0_100",
                "incidencias_abertas",
                "horas_media_resolucion",
                "ingresos_eur",
                "ingresos_por_hab_eur",
            ],
            [
                [
                    r["m"].name,
                    r["facilities"],
                    r["bookings"],
                    r["per_1000"],
                    r["occupancy"],
                    r["no_show_pct"],
                    r["satisfaction"],
                    r["open_incidents"],
                    r["resolve_hours"],
                    r["revenue"] / 100,
                    r["revenue_per_inh"],
                ]
                for r in rows
            ],
            ods=bool(request.GET.get("ods")),
        )
    total_bookings = sum(r["bookings"] for r in rows)
    population = sum(r["m"].population or 0 for r in rows)
    rated = [r for r in rows if r["satisfaction"] is not None]
    network = {
        "bookings": total_bookings,
        "per_1000": round(1000 * total_bookings / population, 1) if population else None,
        "occupancy": round(sum(r["occupancy"] for r in rows) / len(rows)) if rows else 0,
        "satisfaction": round(
            sum(r["satisfaction"] * r["ratings"] for r in rated) / sum(r["ratings"] for r in rated)
        )
        if rated
        else None,
        "open_incidents": sum(r["open_incidents"] for r in rows),
        "revenue": sum(r["revenue"] for r in rows),
    }
    chart_rows = [{"label": r["m"].name, **r} for r in rows]
    return render(
        request,
        "region/dashboard.html",
        {
            "region": request.region,
            "rows": rows,
            "network": network,
            "per_chart": hbar(
                [r for r in chart_rows if r["per_1000"] is not None], "per_1000", "label"
            ),
            "sat_chart": hbar(
                [r for r in chart_rows if r["satisfaction"] is not None],
                "satisfaction",
                "label",
                suffix="/100",
            ),
            "occ_chart": hbar(chart_rows, "occupancy", "label", suffix=" %"),
            "nav": "region",
        },
    )


def send_admin_invitation(request, m, user, actor):
    login_url = request.build_absolute_uri(
        reverse("accounts:login") + "?next=" + treverse(m, "manage:dashboard")
    )
    get_adapter("mail").send(
        user.email,
        _("Invitación para xestionar as instalacións deportivas de %(m)s") % {"m": m.name},
        _(
            "Ola%(n)s:\n\n%(r)s deu de alta %(m)s en Eira e figuras como persoa responsable.\n\n"
            "1. Entra con este correo (recibirás un código, sen contrasinal):\n   %(u)s\n"
            "2. Revisa a primeira instalación, o horario e as tarifas.\n"
            "3. Publícaa cando estea lista. A veciñanza poderá reservar desde ese momento.\n\n"
            "Se tes dúbidas, responde a este correo."
        )
        % {
            "n": f" {user.display_name}" if user.display_name else "",
            "r": m.region.name if m.region else "A deputación",
            "m": m.name,
            "u": login_url,
        },
    )
    audit("tenant.invite", actor, m, user)


@region_admin_required
@require_POST
def resend_invitation(request, slug):
    """Acción de soporte: reenviar a invitación á persoa responsable dun concello da rede."""
    m = get_object_or_404(Municipality, slug=slug, region=request.region)
    admin = (
        Membership.objects.filter(municipality=m, role=Role.ADMIN).select_related("user").first()
    )
    if not admin:
        messages.error(request, _("Este concello aínda non ten persoa responsable."))
    else:
        send_admin_invitation(request, m, admin.user, request.user)
        messages.success(request, _("Invitación reenviada a %(e)s.") % {"e": admin.user.email})
    return redirect("region:dashboard", request.region.slug)


# ---------------------------------------------------------------- alta paso a paso


class StepBasics(forms.Form):
    name = forms.CharField(label=gettext_lazy("Nome do concello"), max_length=120)
    slug = forms.SlugField(
        label=gettext_lazy("Identificador na URL"),
        help_text=gettext_lazy("Só minúsculas, números e guións. Quedará en /c/identificador/."),
    )
    ine_code = forms.CharField(label=gettext_lazy("Código INE"), max_length=5, required=False)
    population = forms.IntegerField(label=gettext_lazy("Poboación"), required=False, min_value=0)
    postcodes = forms.CharField(
        label=gettext_lazy("Códigos postais do termo"),
        max_length=120,
        required=False,
        help_text=gettext_lazy(
            "Separados por comas. Úsanse para contrastar as solicitudes co padrón."
        ),
    )

    def clean_slug(self):
        slug = self.cleaned_data["slug"]
        if Municipality.objects.filter(slug=slug).exists():
            raise forms.ValidationError(_("Xa existe un concello con ese identificador."))
        return slug


class StepResponsible(forms.Form):
    admin_name = forms.CharField(label=gettext_lazy("Nome da persoa responsable"), max_length=80)
    admin_email = forms.EmailField(label=gettext_lazy("Correo da persoa responsable"))
    admin_phone = forms.CharField(
        label=gettext_lazy("Teléfono de contacto do servizo"), max_length=20, required=False
    )
    contact_email = forms.EmailField(
        label=gettext_lazy("Correo público do servizo de deportes"),
        required=False,
        help_text=gettext_lazy("Aparece no pé das páxinas. Pode ser distinto do persoal."),
    )


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


class StepBrand(forms.Form):
    accent_color = forms.CharField(
        label=gettext_lazy("Cor de acento"),
        initial="#2E6A4F",
        widget=forms.TextInput(attrs={"type": "color"}),
        help_text=gettext_lazy("Compróbase o contraste co texto branco (WCAG AA)."),
    )
    coat_of_arms = forms.ImageField(
        label=gettext_lazy("Escudo ou logotipo (opcional)"),
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}),
    )

    def clean_accent_color(self):
        from .models import contrast_ratio

        value = self.cleaned_data["accent_color"]
        if contrast_ratio(value, "#FFFFFF") < 4.5:
            raise forms.ValidationError(
                _("Esta cor ten pouco contraste co texto branco. Escolle unha máis escura.")
            )
        return value

    def clean_coat_of_arms(self):
        f = self.cleaned_data.get("coat_of_arms")
        return clean_image(f) if f and hasattr(f, "content_type") else None


class StepFacility(forms.Form):
    template = forms.ChoiceField(
        label=gettext_lazy("Tipo da primeira instalación"),
        choices=[("", gettext_lazy("Ningunha polo momento"))]
        + [(k, t["label"]) for k, t in TEMPLATES.items()],
        required=False,
    )
    facility_name = forms.CharField(label=gettext_lazy("Nome"), max_length=120, required=False)
    parish = forms.CharField(
        label=gettext_lazy("Parroquia ou lugar"), max_length=80, required=False
    )

    def clean(self):
        d = super().clean()
        if d.get("template") and not d.get("facility_name"):
            self.add_error("facility_name", _("Ponlle nome á instalación."))
        return d


class StepInvite(forms.Form):
    send_invitation = forms.BooleanField(
        label=gettext_lazy("Enviar agora a invitación á persoa responsable"),
        required=False,
        initial=True,
    )


STEPS = [
    (StepBasics, gettext_lazy("Datos")),
    (StepResponsible, gettext_lazy("Responsable")),
    (StepModules, gettext_lazy("Módulos")),
    (StepBrand, gettext_lazy("Imaxe")),
    (StepFacility, gettext_lazy("Primeira instalación")),
    (StepInvite, gettext_lazy("Invitación")),
]


def _create(request, data, invite):
    b, who, mods, brand, fac = (data[str(i)] for i in range(1, 6))
    m = Municipality.objects.create(
        name=b["name"],
        slug=b["slug"],
        ine_code=b.get("ine_code", ""),
        population=b.get("population"),
        postcodes=b.get("postcodes", ""),
        accent_color=brand.get("accent_color") or "#2E6A4F",
        contact_email=who.get("contact_email") or "",
        contact_phone=who.get("admin_phone") or "",
        region=request.region,
        modules={k: k in mods.get("modules", []) for k in DEFAULT_MODULES},
        cancellation_hours=mods["cancellation_hours"],
        max_advance_days=mods["max_advance_days"],
    )
    if brand.get("coat_path") and default_storage.exists(brand["coat_path"]):
        with default_storage.open(brand["coat_path"]) as fh:
            m.coat_of_arms.save(f"{m.slug}.jpg", fh, save=True)
        default_storage.delete(brand["coat_path"])
    admin, _c = User.objects.get_or_create(email=who["admin_email"].lower())
    if not admin.display_name:
        admin.display_name = who["admin_name"]
        admin.save(update_fields=["display_name"])
    Membership.objects.get_or_create(user=admin, municipality=m, role=Role.ADMIN)
    if fac.get("template"):
        t = TEMPLATES[fac["template"]]
        parish = (
            Parish.objects.create(municipality=m, name=fac["parish"]) if fac.get("parish") else None
        )
        f = Facility.objects.create(
            municipality=m,
            name=fac["facility_name"],
            kind=t["kind"],
            parish=parish,
            capacity=t["capacity"],
            slot_minutes=t["slot_minutes"],
            access_level=t["access_level"],
            indoor=t["indoor"],
            lighting=t["lighting"],
            is_published=False,
            key_holder_name=_("Concello") if t["access_level"] == AccessLevel.CUSTODIAN else "",
        )
        apply_template(f, fac["template"], request.user)
        make_variants(f.photo)
    audit("tenant.create", request.user, m, m)
    if invite:
        send_admin_invitation(request, m, admin, request.user)
    return m


@region_admin_required
def new_municipality(request):
    total = len(STEPS)
    step = int(request.POST.get("step", request.GET.get("paso", 1)) or 1)
    step = min(max(step, 1), total)
    data = request.session.get("new_municipality", {})
    if step > 1 and str(step - 1) not in data:
        return redirect(f"{request.path}?paso=1")
    Form, _title = STEPS[step - 1]
    form = Form(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        initial=data.get(str(step)),
    )
    if request.method == "POST" and form.is_valid():
        clean = dict(form.cleaned_data)
        if step == 4:
            upload = clean.pop("coat_of_arms", None)
            clean["coat_path"] = (data.get("4") or {}).get("coat_path", "")
            if upload:
                clean["coat_path"] = default_storage.save(
                    f"tenants/coats/tmp/{upload.name}", upload
                )
        data[str(step)] = clean
        request.session["new_municipality"] = data
        if step < total:
            return redirect(f"{request.path}?paso={step + 1}")
        m = _create(request, data, invite=clean.get("send_invitation"))
        request.session.pop("new_municipality", None)
        messages.success(
            request,
            _("Concello %(n)s creado.") % {"n": m.name}
            + (
                " " + _("Enviouse a invitación á persoa responsable.")
                if clean.get("send_invitation")
                else ""
            ),
        )
        return redirect(treverse(m, "manage:dashboard"))
    preview = None
    if step == total:
        b, who = data.get("1", {}), data.get("2", {})
        preview = {
            "name": b.get("name"),
            "slug": b.get("slug"),
            "admin": who.get("admin_name"),
            "email": who.get("admin_email"),
            "modules": len(data.get("3", {}).get("modules", [])),
            "facility": data.get("5", {}).get("facility_name"),
            "color": data.get("4", {}).get("accent_color"),
            "coat": bool(data.get("4", {}).get("coat_path")),
        }
    return render(
        request,
        "region/new_municipality.html",
        {
            "region": request.region,
            "form": form,
            "step": step,
            "total": total,
            "titles": [t for _f, t in STEPS],
            "preview": preview,
            "nav": "region_new",
        },
    )
