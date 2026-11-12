# SPDX-License-Identifier: EUPL-1.2
"""Acceso sen contrasinal (código ao correo ou identidade pública) e xestión da propia conta."""

import hashlib
import json
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.integrations.registry import get_adapter
from apps.tenants.public_demo import client_ip, rejects_email

from . import twofactor
from .forms import (
    CONSENT_FIELDS,
    CodeForm,
    DeleteAccountForm,
    DependentForm,
    EmailForm,
    PrivacyForm,
    ProfileForm,
    ResidencyCodeForm,
)
from .models import (
    Consent,
    Dependent,
    Household,
    LoginCode,
    ResidencyInvitation,
    User,
    audit,
)
from .profiles import home_url


def _next(request):
    nxt = (
        request.POST.get("next")
        or request.GET.get("next")
        or request.session.get("login_next")
        or "/"
    )
    return nxt if url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}) else "/"


def _after_login(request, user, nxt, last_tenant):
    """Destino tras identificarse. `nxt` e `last_tenant` lense ANTES de login(): ao cambiar de
    persoa, login() baleira a sesión."""
    if nxt != "/":
        return nxt
    if last_tenant and not user.memberships.exists():
        from apps.tenants.models import Municipality

        tenant = Municipality.objects.filter(slug=last_tenant, is_active=True).first()
        if tenant:
            return home_url(user, tenant=tenant, roles=set())
    return home_url(user)


def _client_ip(request):
    return client_ip(request)


def _rate_limited(email, ip):
    """Limita envíos por correo e por IP nunha xanela dunha hora."""
    keys = [
        (
            f"eira:rl:mail:{hashlib.sha256(email.encode()).hexdigest()[:16]}",
            settings.EIRA_LOGIN_RATE_LIMIT,
        ),
        (
            f"eira:rl:ip:{hashlib.sha256(ip.encode()).hexdigest()[:16]}",
            settings.EIRA_LOGIN_RATE_LIMIT_IP,
        ),
    ]
    for key, limit in keys:
        cache.add(key, 0, 3600)
        if cache.incr(key) > limit:
            return True
    return False


def login_email(request):
    request.layout_override = "public"
    request.session["login_next"] = _next(request)
    form = EmailForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        if rejects_email(email):
            form.add_error("email", _("Nesta demostración non escribas o teu correo real."))
        elif _rate_limited(email, _client_ip(request)):
            form.add_error(
                None, _("Demasiados intentos. Agarda un pouco antes de pedir outro código.")
            )
        else:
            _obj, code = LoginCode.issue(email)
            get_adapter("mail").send(
                email,
                _("O teu código de acceso a Eira: %(c)s") % {"c": code},
                _(
                    "Introduce este código para entrar: %(c)s\n\nCaduca en 10 minutos. Se non o pediches, ignora esta mensaxe."
                )
                % {"c": code},
            )
            request.session["login_email"] = email
            return redirect("accounts:code")
    return render(
        request, "accounts/login.html", {"form": form, "next": request.session["login_next"]}
    )


def login_code(request):
    request.layout_override = "public"
    email = request.session.get("login_email")
    if not email:
        return redirect("accounts:login")
    form = CodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if LoginCode.verify(email, form.cleaned_data["code"]):
            user, created = User.objects.get_or_create(email=email)
            if created:
                user.set_unusable_password()
                user.save()
            nxt, last = _next(request), request.session.get("last_tenant")
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            audit("auth.login", user, method="email_code")
            request.session.pop("login_email", None)
            return redirect(_after_login(request, user, nxt, last))
        form.add_error("code", _("Código incorrecto ou caducado."))
    return render(request, "accounts/code.html", {"form": form, "email": email})


def identity_start(request):
    request.session["login_next"] = _next(request)
    return redirect(get_adapter("identity").start(request, request.session["login_next"]))


def identity_callback(request):
    adapter = get_adapter("identity")
    identity = adapter.complete(request)
    if identity is None:
        messages.error(
            request,
            _(
                "A identificación caducou ou xa se usou (por exemplo, ao volver atrás). Téntao de novo."
            ),
        )
        nxt = request.session.get("identity_next") or request.session.get("login_next") or "/"
        return redirect(reverse("accounts:login") + "?next=" + quote(nxt))
    user = User.objects.filter(identity_subject=identity.subject).first()
    if user is None:
        user, _created = User.objects.get_or_create(email=identity.email.lower())
        if not user.identity_subject:
            user.identity_subject = identity.subject
        if not user.display_name:
            user.display_name = identity.name
        user.save()
    nxt = request.session.pop("identity_next", None) or _next(request)
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = "/"
    last = request.session.get("last_tenant")
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    audit("auth.login", user, method=identity.provider)
    return redirect(_after_login(request, user, nxt, last))


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, _("Saíches da túa conta."))
    return redirect("home")


# ---------------------------------------------------------------- conta


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Datos gardados."))
        return redirect("account:profile")
    memberships = request.user.memberships.select_related("municipality")
    residencies = request.user.residencies.filter(revoked_at__isnull=True).select_related(
        "municipality"
    )
    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "memberships": memberships,
            "residencies": residencies,
            "nav": "account",
            "residency_form": ResidencyCodeForm(),
            "two_factor_on": twofactor.enabled(request.user),  # v1.3
        },
    )


@login_required
@require_POST
def redeem_residency(request):
    form = ResidencyCodeForm(request.POST)
    if form.is_valid():
        municipality = ResidencyInvitation.redeem(request.user, form.cleaned_data["code"])
        if municipality:
            messages.success(
                request, _("Empadroamento validado en %(m)s.") % {"m": municipality.name}
            )
        else:
            messages.error(request, _("O código non é válido ou xa se usou."))
    return redirect("account:profile")


def export_user_data(user):
    """Portabilidade (art. 20 RXPD): todos os datos da persoa en JSON aberto."""
    from apps.activities.models import Enrollment
    from apps.bookings.models import Booking
    from apps.incidents.models import Incident
    from apps.notifications.models import Notification

    def dt(v):
        return v.isoformat() if v else None

    household = getattr(user, "household", None)
    return {
        "format": "eira-user-export/1",
        "exported_at": timezone.now().isoformat(),
        "user": {
            "email": user.email,
            "display_name": user.display_name,
            "phone": user.phone,
            "birth_year": user.birth_year,
            "preferred_language": user.preferred_language,
            "date_joined": dt(user.date_joined),
            "notify_email": user.notify_email,
            "notify_telegram": user.notify_telegram,
            "tours_hidden": list(user.tours_hidden or []),
            "linked_public_identity": bool(user.identity_subject),
        },
        # Saúde: só se a persoa a gardou na conta (dereito de acceso; nunca nas exportacións do concello)
        "health": (
            {
                **user.health_profile.as_dict(),
                "consent_version": user.health_profile.consent_version,
                "consent_at": dt(user.health_profile.consent_at),
            }
            if hasattr(user, "health_profile")
            else None
        ),
        "roles": [
            {"municipality": m.municipality.slug, "role": m.role}
            for m in user.memberships.select_related("municipality")
        ],
        "residencies": [
            {
                "municipality": r.municipality.slug,
                "method": r.method,
                "validated_at": dt(r.validated_at),
            }
            for r in user.residencies.select_related("municipality")
        ],
        "bookings": [
            {
                "reference": b.reference,
                "municipality": b.municipality.slug,
                "facility": b.facility.name,
                "start": dt(b.start),
                "end": dt(b.end),
                "status": b.status,
                "price_cents": b.price_cents,
                "paid_cents": b.paid_cents,
                "refunded_cents": b.refunded_cents,
                "rules_version": b.rules_version.version if b.rules_version else None,
                "rules_accepted_at": dt(b.rules_accepted_at),
                "checked_in_at": dt(b.checked_in_at),
            }
            for b in Booking.objects.filter(user=user).select_related(
                "facility", "municipality", "rules_version"
            )
        ],
        "incidents": [
            {
                "id": i.pk,
                "facility": i.facility.name,
                "description": i.description,
                "status": i.status,
                "created_at": dt(i.created_at),
            }
            for i in Incident.objects.filter(reporter=user).select_related("facility")
        ],
        "household": {
            "dependents": [
                {
                    "first_name": d.first_name,
                    "birth_year": d.birth_year,
                    "consents": [
                        {
                            "kind": c.kind,
                            "granted_at": dt(c.granted_at),
                            "revoked_at": dt(c.revoked_at),
                            "text_version": c.text_version,
                        }
                        for c in d.consents.all()
                    ],
                }
                for d in household.dependents.all()
            ]
            if household
            else [],
        },
        "enrollments": [
            {
                "group": str(e.group),
                "participant": e.participant_name,
                "surnames": e.surnames,
                "status": e.status,
            }
            for e in Enrollment.objects.filter(user=user).select_related(
                "group", "group__activity", "dependent"
            )
        ],
        "notifications": [
            {
                "title": n.title,
                "body": n.body,
                "created_at": dt(n.created_at),
                "read_at": dt(n.read_at),
            }
            for n in Notification.objects.filter(user=user)
        ],
        # v1.5 · C: residencia indicada (só parroquia ou concello)
        "residence": {
            "parish": user.residence_parish.name if user.residence_parish else None,
            "municipality": user.residence_municipality.name
            if user.residence_municipality
            else None,
        },
        # v1.5 · D: documentos aceptados
        "legal_acceptances": [
            {
                "municipality": a.municipality.name,
                "document": a.version.document.kind,
                "version": a.version.number,
                "accepted_at": dt(a.accepted_at),
                "channel": a.channel,
                "withdrawn_at": dt(a.withdrawn_at),
            }
            for a in user.legal_acceptances.select_related("version__document", "municipality")
        ],
    }


@login_required
def export_data(request):
    data = export_user_data(request.user)
    audit("account.export", request.user)
    response = HttpResponse(
        json.dumps(data, ensure_ascii=False, indent=2), content_type="application/json"
    )
    response["Content-Disposition"] = 'attachment; filename="eira-os-meus-datos.json"'
    return response


def delete_user(user):
    """Supresión (art. 17 RXPD). As reservas pasadas consérvanse anonimizadas para a contabilidade."""
    from apps.bookings.models import Booking

    Booking.objects.filter(user=user).update(user=None, holder_name="", holder_phone="")
    audit("account.delete", None, detail_user=hashlib.sha256(user.email.encode()).hexdigest()[:12])
    user.delete()


@login_required
def delete_account(request):
    form = DeleteAccountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = request.user
        logout(request)
        delete_user(user)
        messages.success(request, _("A túa conta e os teus datos persoais foron eliminados."))
        return redirect("home")
    return render(request, "accounts/delete.html", {"form": form, "nav": "account"})


def neighbour_global(view):
    """Unidade familiar: só para a veciñanza (o persoal do concello usa outra conta)."""
    from functools import wraps

    from django.core.exceptions import PermissionDenied

    from .profiles import kind_global

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if kind_global(request.user) != "neighbour":
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return login_required(wrapper)


@neighbour_global
def household(request):
    hh, _created = Household.objects.get_or_create(responsible=request.user)
    form = DependentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        dep = form.save(commit=False)
        dep.household = hh
        dep.save()
        for field, kind in CONSENT_FIELDS.items():
            if form.cleaned_data.get(field):
                Consent.objects.create(dependent=dep, kind=kind, granted_by=request.user)
        audit("household.add_dependent", request.user, obj=dep)
        messages.success(
            request, _("Engadiuse a %(n)s á túa unidade familiar.") % {"n": dep.first_name}
        )
        return redirect("account:household")
    dependents = []
    for dep in hh.dependents.prefetch_related("consents"):
        active = {c.kind: c for c in dep.consents.all() if c.revoked_at is None}
        dependents.append(
            (dep, [(value, label, active.get(value)) for value, label in Consent.Kind.choices])
        )
    return render(
        request,
        "accounts/household.html",
        {
            "household": hh,
            "dependents": dependents,
            "form": form,
            "nav": "account",
        },
    )


@neighbour_global
@require_POST
def consent_toggle(request, dependent_id, kind):
    dep = get_object_or_404(Dependent, pk=dependent_id, household__responsible=request.user)
    if kind not in Consent.Kind.values:
        return redirect("account:household")
    active = dep.consents.filter(kind=kind, revoked_at__isnull=True)
    if active.exists():
        active.update(revoked_at=timezone.now())
        audit("consent.revoke", request.user, obj=dep, kind=kind)
        messages.success(request, _("Consentimento retirado."))
    else:
        Consent.objects.create(dependent=dep, kind=kind, granted_by=request.user)
        audit("consent.grant", request.user, obj=dep, kind=kind)
        messages.success(request, _("Consentimento outorgado."))
    return redirect("account:household")


@login_required
def privacy_centre(request):
    """Centro de privacidade: que datos hai, interruptores, descarga, borrado e a quen dirixirse."""
    from apps.bookings.models import Booking, Rating
    from apps.incidents.models import Incident
    from apps.tenants.models import Municipality

    user = request.user
    before = user.photo_consent
    form = PrivacyForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        u = form.save(commit=False)
        if u.photo_consent != before:
            u.photo_consent_at = timezone.now() if u.photo_consent else None
            audit("consent.photo_" + ("grant" if u.photo_consent else "revoke"), user, obj=user)
            if not u.photo_consent:
                from apps.legal.services import sync_photo_withdrawal

                sync_photo_withdrawal(user)  # v1.5 · D
        u.save()
        messages.success(request, _("Preferencias de privacidade gardadas."))
        return redirect("account:privacy")
    household = getattr(user, "household", None)
    dependents = list(household.dependents.prefetch_related("consents")) if household else []
    muni_ids = (
        set(user.memberships.values_list("municipality", flat=True))
        | set(user.residencies.values_list("municipality", flat=True))
        | set(Booking.objects.filter(user=user).values_list("municipality", flat=True).distinct())
    )
    return render(
        request,
        "accounts/privacy.html",
        {
            "form": form,
            "counts": [
                (_("Reservas"), Booking.objects.filter(user=user).count()),
                (_("Avisos de avaría"), Incident.objects.filter(reporter=user).count()),
                (_("Valoracións"), Rating.objects.filter(booking__user=user).count()),
                (_("Menores ao teu cargo"), len(dependents)),
                (
                    _("Empadroamentos validados"),
                    user.residencies.filter(revoked_at__isnull=True).count(),
                ),
            ],
            "dependents": [
                (d, {c.kind for c in d.consents.all() if c.revoked_at is None}) for d in dependents
            ],
            "municipalities": Municipality.objects.filter(pk__in=muni_ids).order_by("name"),
            "nav": "account",
        },
    )
