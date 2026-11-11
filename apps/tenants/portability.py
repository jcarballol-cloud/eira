# SPDX-License-Identifier: EUPL-1.2
"""Portabilidade íntegra dun concello: exportación a ZIP (JSON + CSV + iCal + ficheiros) e importación
noutra instancia de Eira, remapeando identificadores. Formato documentado en docs/interoperabilidade.md.
"""

import csv
import datetime as dt
import io
import json
import zipfile

from django import forms
from django.contrib import messages
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.access.models import AccessEvent, KeyHandover, LockDevice
from apps.accounts.models import Consent, Dependent, Household, Membership, Residency, User, audit
from apps.activities.models import (
    Activity,
    Attendance,
    Enrollment,
    FitnessBattery,
    FitnessResult,
    FitnessTest,
    Group,
    Session,
)
from apps.bookings import ics
from apps.bookings.models import Booking
from apps.facilities.models import Closure, Facility, OpeningHours, Parish, RulesVersion, Tariff
from apps.incidents.models import Incident
from apps.maintenance.models import MaintenancePlan, MaintenanceTask, WorkOrder, WorkOrderPhoto

from .models import Municipality
from .urlutils import role_required, treverse

FORMAT = "eira-municipality-export/1"
USER_FIELDS = ["email", "display_name", "phone", "birth_year", "preferred_language", "notify_email"]


def _user_ids(t):
    ids = set(Membership.objects.filter(municipality=t).values_list("user_id", flat=True))
    ids |= set(Residency.objects.filter(municipality=t).values_list("user_id", flat=True))
    ids |= set(
        Booking.objects.filter(municipality=t, user__isnull=False).values_list("user_id", flat=True)
    )
    ids |= set(
        Enrollment.objects.filter(municipality=t, user__isnull=False).values_list(
            "user_id", flat=True
        )
    )
    ids |= set(
        Incident.objects.filter(municipality=t, reporter__isnull=False).values_list(
            "reporter_id", flat=True
        )
    )
    return ids


# Orde de exportación/importación (as dependencias primeiro) e filtro por concello.
SPEC = [
    (Membership, lambda t: Membership.objects.filter(municipality=t)),
    (Residency, lambda t: Residency.objects.filter(municipality=t)),
    (Household, lambda t: Household.objects.filter(responsible_id__in=_user_ids(t))),
    (Dependent, lambda t: Dependent.objects.filter(household__responsible_id__in=_user_ids(t))),
    (
        Consent,
        lambda t: Consent.objects.filter(dependent__household__responsible_id__in=_user_ids(t)),
    ),
    (Parish, lambda t: Parish.objects.filter(municipality=t)),
    (Facility, lambda t: Facility.objects.filter(municipality=t)),
    (OpeningHours, lambda t: OpeningHours.objects.filter(facility__municipality=t)),
    (Tariff, lambda t: Tariff.objects.filter(facility__municipality=t)),
    (RulesVersion, lambda t: RulesVersion.objects.filter(facility__municipality=t)),
    (Closure, lambda t: Closure.objects.filter(municipality=t)),
    (LockDevice, lambda t: LockDevice.objects.filter(municipality=t)),
    (Booking, lambda t: Booking.objects.filter(municipality=t)),
    (KeyHandover, lambda t: KeyHandover.objects.filter(municipality=t)),
    (AccessEvent, lambda t: AccessEvent.objects.filter(municipality=t)),
    (Incident, lambda t: Incident.objects.filter(municipality=t)),
    (MaintenancePlan, lambda t: MaintenancePlan.objects.filter(municipality=t)),
    (MaintenanceTask, lambda t: MaintenanceTask.objects.filter(plan__municipality=t)),
    (WorkOrder, lambda t: WorkOrder.objects.filter(municipality=t)),
    (WorkOrderPhoto, lambda t: WorkOrderPhoto.objects.filter(order__municipality=t)),
    (Activity, lambda t: Activity.objects.filter(municipality=t)),
    (Group, lambda t: Group.objects.filter(municipality=t)),
    (Enrollment, lambda t: Enrollment.objects.filter(municipality=t)),
    (Session, lambda t: Session.objects.filter(municipality=t)),
    (Attendance, lambda t: Attendance.objects.filter(session__municipality=t)),
    (FitnessBattery, lambda t: FitnessBattery.objects.filter(municipality=t)),
    (FitnessTest, lambda t: FitnessTest.objects.filter(battery__municipality=t)),
    (FitnessResult, lambda t: FitnessResult.objects.filter(enrollment__municipality=t)),
]
UNIQUE_REGEN = {"checkin_token", "reference"}
TENANT_FIELDS = [
    "name",
    "slug",
    "ine_code",
    "accent_color",
    "languages",
    "contact_email",
    "contact_phone",
    "address",
    "population",
    "privacy_text",
    "accessibility_statement",
    "accessibility_unit",  # v1.5.1
    "accessibility_email",
    "accessibility_phone",
    "accessibility_complaint_url",
    "accessibility_reviewed_on",
    "legal_notice",
    "modules",
    "cancellation_hours",
    "late_cancel_penalty_pct",
    "max_advance_days",
    "max_active_bookings",
    "no_show_grace_minutes",
]


def _value(obj, field):
    v = getattr(obj, field.attname)
    if isinstance(field, models.FileField):
        return v.name if v else ""
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, (int, float, str, bool, list, dict)) or v is None:
        return v
    return str(v)


def _dump(obj):
    out = {}
    for f in obj._meta.concrete_fields:
        if f.primary_key:
            continue
        if f.is_relation and f.related_model is User:
            target = getattr(obj, f.name)
            out[f.name] = {"user": target.email} if target else None
        elif f.is_relation and f.related_model is Municipality:
            out[f.name] = {"municipality": True}
        else:
            out[f.attname] = _value(obj, f)
    return out


def _export_v15(tenant):
    """v1.5: documentos legais, aceptacións e marcas de acreditación (só quen e cando)."""
    from apps.activities.models import MinorsAccreditation
    from apps.legal.models import LegalAcceptance, LegalVersion

    return {
        "legal_versions": [
            {
                "kind": v.document.kind,
                "number": v.number,
                "title_gl": v.title_gl,
                "title_es": v.title_es,
                "body_gl": v.body_gl,
                "body_es": v.body_es,
                "mode": v.mode,
                "substantial": v.substantial,
                "is_example": v.is_example,
                "published_at": v.published_at.isoformat(),
            }
            for v in LegalVersion.objects.filter(municipality=tenant).select_related("document")
        ],
        "legal_acceptances": [
            {
                "email": a.user.email if a.user else None,
                "kind": a.version.document.kind,
                "number": a.version.number,
                "accepted_at": a.accepted_at.isoformat(),
                "channel": a.channel,
                "withdrawn_at": a.withdrawn_at.isoformat() if a.withdrawn_at else None,
            }
            for a in LegalAcceptance.objects.filter(municipality=tenant).select_related(
                "user", "version__document"
            )
        ],
        "minors_accreditations": [
            {
                "email": r.user.email,
                "confirmed_by": r.confirmed_by.email if r.confirmed_by else None,
                "confirmed_at": r.confirmed_at.isoformat(),
            }
            for r in MinorsAccreditation.objects.filter(municipality=tenant).select_related(
                "user", "confirmed_by"
            )
        ],
    }


def export_municipality(tenant):
    buf = io.BytesIO()
    files = []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        users = User.objects.filter(pk__in=_user_ids(tenant))
        data = {
            "format": FORMAT,
            "exported_at": timezone.now().isoformat(),
            "municipality": {f: _value(tenant, tenant._meta.get_field(f)) for f in TENANT_FIELDS},
            "users": [{f: getattr(u, f) for f in USER_FIELDS} for u in users],
            "objects": [],
        }
        for model, qs in SPEC:
            for obj in qs(tenant).order_by("pk"):
                data["objects"].append(
                    {"model": model._meta.label, "pk": obj.pk, "fields": _dump(obj)}
                )
                for f in obj._meta.concrete_fields:
                    if isinstance(f, models.FileField) and getattr(obj, f.name):
                        files.append(getattr(obj, f.name))
        zf.writestr("eira.json", json.dumps(data, ensure_ascii=False, indent=1))
        zf.writestr("v15.json", json.dumps(_export_v15(tenant), ensure_ascii=False, indent=1))
        # Formatos abertos adicionais para reutilización directa
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["referencia", "instalacion", "inicio", "fin", "estado", "canle", "importe_eur"])
        bookings = Booking.objects.filter(municipality=tenant).select_related(
            "facility", "municipality"
        )
        for b in bookings:
            w.writerow(
                [
                    b.reference,
                    b.facility.name,
                    b.start.isoformat(),
                    b.end.isoformat(),
                    b.status,
                    b.channel,
                    b.paid_cents / 100,
                ]
            )
        zf.writestr("csv/reservas.csv", out.getvalue())
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(
            ["id", "nome", "tipo", "parroquia", "latitude", "lonxitude", "nivel_acceso", "prazas"]
        )
        for f in Facility.objects.filter(municipality=tenant).select_related("parish"):
            w.writerow(
                [
                    f.pk,
                    f.name,
                    f.kind,
                    f.parish.name if f.parish else "",
                    f.latitude,
                    f.longitude,
                    f.access_level,
                    f.capacity,
                ]
            )
        zf.writestr("csv/instalacions.csv", out.getvalue())
        zf.writestr(
            "ical/reservas.ics",
            ics.calendar(bookings.exclude(status="cancelled"), name=tenant.name),
        )
        geo = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": f.name, "kind": f.kind},
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(f.longitude), float(f.latitude)],
                    },
                }
                for f in Facility.objects.filter(municipality=tenant, latitude__isnull=False)
            ],
        }
        zf.writestr("geo/instalacions.geojson", json.dumps(geo, ensure_ascii=False))
        for fieldfile in files:
            try:
                with fieldfile.open("rb") as fh:
                    zf.writestr(f"media/{fieldfile.name}", fh.read())
            except (FileNotFoundError, OSError):
                pass
        zf.writestr(
            "LEME.txt",
            "Exportación íntegra dun concello de Eira (formato " + FORMAT + ").\n"
            "eira.json: todos os datos; csv/, ical/, geo/: formatos abertos; media/: ficheiros.\n"
            "AVISO: contén datos persoais e segredos das pechaduras. Custodia este ficheiro.\n",
        )
    return buf.getvalue()


@transaction.atomic
def import_municipality(raw, slug=None, name=None):
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        data = json.loads(zf.read("eira.json"))
        if data.get("format") != FORMAT:
            raise ValueError("Formato descoñecido")
        media = {
            n[len("media/") :]: zf.read(n)
            for n in zf.namelist()
            if n.startswith("media/") and not n.endswith("/")
        }
    m = dict(data["municipality"])
    if slug:
        m["slug"] = slug
    if name:
        m["name"] = name
    tenant = Municipality.objects.create(**m)
    users = {}
    for u in data["users"]:
        user, _c = User.objects.get_or_create(
            email=u["email"], defaults={k: v for k, v in u.items() if k != "email"}
        )
        users[u["email"]] = user
    models_by_label = {model._meta.label: model for model, _q in SPEC}
    pk_map = {}
    for item in data["objects"]:
        model = models_by_label[item["model"]]
        kwargs = {}
        for f in model._meta.concrete_fields:
            if f.primary_key:
                continue
            if f.is_relation and f.related_model is User:
                ref = item["fields"].get(f.name)
                kwargs[f.name] = users.get(ref["user"]) if ref else None
            elif f.is_relation and f.related_model is Municipality:
                kwargs[f.name] = tenant
            elif f.is_relation:
                old = item["fields"].get(f.attname)
                kwargs[f.attname] = (
                    pk_map.get((f.related_model._meta.label, old)) if old is not None else None
                )
            elif isinstance(f, models.FileField):
                name_ = item["fields"].get(f.attname) or ""
                if name_ and name_ in media:
                    kwargs[f.name] = ContentFile(media[name_], name=name_.rsplit("/", 1)[-1])
            elif f.attname in item["fields"]:
                value = item["fields"][f.attname]
                if value is not None and isinstance(f, models.DateTimeField):
                    value = dt.datetime.fromisoformat(value)
                elif value is not None and isinstance(f, models.DateField):
                    value = dt.date.fromisoformat(value)
                elif value is not None and isinstance(f, models.TimeField):
                    value = dt.time.fromisoformat(value)
                if (
                    f.attname in UNIQUE_REGEN
                    and model.objects.filter(**{f.attname: value}).exists()
                ):
                    continue  # rexenérase co valor por defecto
                kwargs[f.attname] = value
        obj = model(**kwargs)
        obj.save()
        # Os campos auto_now_add reciben «agora» ao gardar: restáurase a data orixinal.
        originals = {
            f.attname: dt.datetime.fromisoformat(item["fields"][f.attname])
            for f in model._meta.concrete_fields
            if getattr(f, "auto_now_add", False) and item["fields"].get(f.attname)
        }
        if originals:
            model.objects.filter(pk=obj.pk).update(**originals)
        pk_map[(item["model"], item["pk"])] = obj.pk
    return tenant


class ImportForm(forms.Form):
    file = forms.FileField(label=gettext_lazy("Ficheiro ZIP de Eira"))
    slug = forms.SlugField(label=gettext_lazy("Identificador do novo concello"))


@role_required("admin", "region_admin")
def page(request):
    return render(
        request,
        "manage/portability.html",
        {"form": ImportForm(), "nav": "manage", "sub": "settings"},
    )


@role_required("admin", "region_admin")
def export_view(request):
    audit("tenant.export", request.user, request.tenant)
    response = HttpResponse(export_municipality(request.tenant), content_type="application/zip")
    stamp = timezone.localdate().isoformat()
    response["Content-Disposition"] = (
        f'attachment; filename="eira-{request.tenant.slug}-{stamp}.zip"'
    )
    return response


@role_required("region_admin")
def import_view(request):
    form = ImportForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        if Municipality.objects.filter(slug=form.cleaned_data["slug"]).exists():
            form.add_error("slug", _("Xa existe un concello con ese identificador."))
        else:
            try:
                tenant = import_municipality(
                    form.cleaned_data["file"].read(), slug=form.cleaned_data["slug"]
                )
            except (ValueError, KeyError, zipfile.BadZipFile) as exc:
                form.add_error("file", _("Non se puido importar: %(e)s") % {"e": exc})
            else:
                tenant.region = request.tenant.region
                tenant.save(update_fields=["region"])
                audit("tenant.import", request.user, tenant)
                messages.success(request, _("Concello importado."))
                return redirect(treverse(tenant, "tenant_home"))
    return render(
        request, "manage/portability.html", {"form": form, "nav": "manage", "sub": "settings"}
    )
