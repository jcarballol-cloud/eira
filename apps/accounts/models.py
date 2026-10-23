# SPDX-License-Identifier: EUPL-1.2
"""Persoas usuarias, roles por concello, empadroamento, unidade familiar e auditoría.

Minimización: só se garda o imprescindible. Non hai contrasinais para a cidadanía
(acceso con código ao correo ou identidade pública), non se garda o DNI (só un
identificador opaco do provedor de identidade) e da idade só se garda o ano.
"""

import hashlib
import hmac
import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import Municipality, Region


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("correo electrónico"), unique=True)
    display_name = models.CharField(_("nome para mostrar"), max_length=80, blank=True)
    phone = models.CharField(_("teléfono"), max_length=20, blank=True)
    birth_year = models.PositiveIntegerField(_("ano de nacemento"), null=True, blank=True)
    preferred_language = models.CharField(_("idioma preferido"), max_length=5, default="gl")
    identity_subject = models.CharField(
        max_length=128, unique=True, null=True, blank=True, editable=False
    )
    notify_email = models.BooleanField(_("avisos por correo"), default=True)
    notify_telegram = models.BooleanField(_("avisos por Telegram"), default=False)
    telegram_chat = models.CharField(_("chat de Telegram"), max_length=64, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"

    class Meta:
        verbose_name = _("persoa usuaria")
        verbose_name_plural = _("persoas usuarias")

    def __str__(self):
        return self.display_name or self.email

    @property
    def age(self):
        return timezone.localdate().year - self.birth_year if self.birth_year else None

    def is_resident(self, municipality):
        return self.residencies.filter(municipality=municipality, revoked_at__isnull=True).exists()


class Role(models.TextChoices):
    CITIZEN = "citizen", _("Veciñanza")
    ADMIN = "admin", _("Administración do concello")
    MAINTENANCE = "maintenance", _("Mantemento")
    MONITOR = "monitor", _("Monitor/a")


class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    municipality = models.ForeignKey(
        Municipality, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(_("rol"), max_length=20, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("rol no concello")
        verbose_name_plural = _("roles nos concellos")
        constraints = [
            models.UniqueConstraint(fields=["user", "municipality", "role"], name="uniq_membership")
        ]

    def __str__(self):
        return f"{self.user} · {self.municipality} · {self.get_role_display()}"


class RegionMembership(models.Model):
    """Rol `region_admin`: persoal da deputación ou mancomunidade."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="region_memberships")
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="members")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "region"], name="uniq_region_membership")
        ]


class ResidencyInvitation(models.Model):
    """Código que o concello entrega (no mostrador ou por carta) para validar o empadroamento."""

    municipality = models.ForeignKey(
        Municipality, on_delete=models.CASCADE, related_name="residency_invitations"
    )
    code = models.CharField(max_length=12, unique=True)
    note = models.CharField(_("nota interna"), max_length=120, blank=True)
    # Se se envía a un correo concreto, só esa conta pode usalo
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    used_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def issue(cls, municipality, note="", days=30, email=""):
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        code = "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(2))
        return cls.objects.create(
            municipality=municipality,
            code=code,
            note=note,
            email=email.lower(),
            expires_at=timezone.now() + timezone.timedelta(days=days),
        )

    @property
    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()

    @classmethod
    def redeem(cls, user, code):
        """Valida o empadroamento de `user` co código. Devolve o concello ou None."""
        code = (code or "").strip().upper().replace(" ", "")
        if len(code) == 8 and "-" not in code:
            code = f"{code[:4]}-{code[4:]}"
        inv = cls.objects.filter(code=code).select_related("municipality").first()
        if not inv or not inv.is_valid or (inv.email and inv.email != user.email.lower()):
            return None
        Residency.objects.get_or_create(
            user=user,
            municipality=inv.municipality,
            revoked_at=None,
            defaults={"method": Residency.Method.INVITATION},
        )
        inv.used_by, inv.used_at = user, timezone.now()
        inv.save(update_fields=["used_by", "used_at"])
        audit("residency.redeem", user, inv.municipality, inv)
        return inv.municipality


class AppRequest(models.Model):
    """Solicitude da app: en liña desde a web do concello ou no mostrador."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pendente de revisar")
        SENT = "sent", _("Código enviado")
        REJECTED = "rejected", _("Non figura no padrón")

    class Channel(models.TextChoices):
        ONLINE = "online", _("En liña")
        COUNTER = "counter", _("Mostrador")

    municipality = models.ForeignKey(
        Municipality, on_delete=models.CASCADE, related_name="app_requests"
    )
    name = models.CharField(_("nome"), max_length=80)
    email = models.EmailField(_("correo electrónico"), blank=True)
    birth_year = models.PositiveIntegerField(_("ano de nacemento"), null=True, blank=True)
    postcode = models.CharField(_("código postal"), max_length=5, blank=True)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.ONLINE)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    padron_match = models.BooleanField(_("figura no padrón"), default=False)
    invitation = models.ForeignKey(
        ResidencyInvitation, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = _("solicitude da app")
        verbose_name_plural = _("solicitudes da app")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class Residency(models.Model):
    class Method(models.TextChoices):
        INVITATION = "invitation", _("Código de invitación")
        COUNTER = "counter", _("Mostrador")
        IDENTITY = "identity", _("Identidade pública + padrón")

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="residencies")
    municipality = models.ForeignKey(
        Municipality, on_delete=models.CASCADE, related_name="residencies"
    )
    method = models.CharField(max_length=20, choices=Method.choices)
    validated_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("empadroamento validado")
        verbose_name_plural = _("empadroamentos validados")


def _hash_code(email, code):
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f"{email.lower()}:{code}".encode(), hashlib.sha256).hexdigest()


class LoginCode(models.Model):
    """Código dun só uso enviado ao correo. Só se garda o seu HMAC."""

    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def issue(cls, email):
        code = f"{secrets.randbelow(10**6):06d}"
        cls.objects.filter(email=email.lower(), used_at__isnull=True).update(used_at=timezone.now())
        obj = cls.objects.create(
            email=email.lower(),
            code_hash=_hash_code(email, code),
            expires_at=timezone.now()
            + timezone.timedelta(seconds=settings.EIRA_LOGIN_CODE_TTL_SECONDS),
        )
        return obj, code

    @classmethod
    def verify(cls, email, code):
        """Devolve True se o código é válido. Conta intentos e invalida tras o máximo."""
        email = email.lower()
        obj = (
            cls.objects.filter(email=email, used_at__isnull=True, expires_at__gt=timezone.now())
            .order_by("-created_at")
            .first()
        )
        if obj is None:
            return False
        if obj.attempts >= settings.EIRA_LOGIN_CODE_MAX_ATTEMPTS:
            return False
        obj.attempts += 1
        ok = hmac.compare_digest(obj.code_hash, _hash_code(email, code.strip()))
        if ok:
            obj.used_at = timezone.now()
        obj.save(update_fields=["attempts", "used_at"])
        return ok


class Eligibility(models.Model):
    """Dereito a tarifa reducida (discapacidade, desemprego, familia numerosa…) validado polo persoal.
    Non se garda a documentación nin o motivo detallado: só o colectivo e a data."""

    class Kind(models.TextChoices):
        DISABILITY = "disability", _("Persoa con discapacidade")
        UNEMPLOYED = "unemployed", _("Persoa en desemprego")
        LARGE_FAMILY = "large_family", _("Familia numerosa ou monoparental")

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="eligibilities")
    municipality = models.ForeignKey(
        Municipality, on_delete=models.CASCADE, related_name="eligibilities"
    )
    kind = models.CharField(_("colectivo"), max_length=20, choices=Kind.choices)
    validated_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    validated_at = models.DateTimeField(default=timezone.now)
    expires_on = models.DateField(_("válido ata"), null=True, blank=True)

    class Meta:
        verbose_name = _("tarifa reducida validada")
        verbose_name_plural = _("tarifas reducidas validadas")

    @property
    def is_valid(self):
        return self.expires_on is None or self.expires_on >= timezone.localdate()


class Household(models.Model):
    """Unidade familiar: unha persoa adulta responsable e menores ao seu cargo."""

    responsible = models.OneToOneField(User, on_delete=models.CASCADE, related_name="household")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.responsible)


class Dependent(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="dependents")
    first_name = models.CharField(_("nome"), max_length=60)
    birth_year = models.PositiveIntegerField(_("ano de nacemento"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("menor ao cargo")
        verbose_name_plural = _("menores ao cargo")

    def __str__(self):
        return self.first_name

    @property
    def age(self):
        return timezone.localdate().year - self.birth_year

    def has_consent(self, kind):
        return self.consents.filter(kind=kind, revoked_at__isnull=True).exists()


class Consent(models.Model):
    class Kind(models.TextChoices):
        DATA = "data", _("Tratamento de datos para a actividade")
        IMAGE = "image", _("Uso da imaxe en comunicacións municipais")
        PERFORMANCE = "performance", _("Rexistro de esforzo e probas físicas")

    dependent = models.ForeignKey(Dependent, on_delete=models.CASCADE, related_name="consents")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    granted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    text_version = models.CharField(max_length=20, default="2026-1")
    granted_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("consentimento")
        verbose_name_plural = _("consentimentos")
        ordering = ["-granted_at"]


class AuditLog(models.Model):
    """Rexistro de accións sensibles (ENS: trazabilidade)."""

    at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    municipality = models.ForeignKey(Municipality, null=True, blank=True, on_delete=models.CASCADE)
    action = models.CharField(max_length=60)
    object_type = models.CharField(max_length=60, blank=True)
    object_id = models.CharField(max_length=40, blank=True)
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-at"]

    def __str__(self):
        return f"{self.at:%Y-%m-%d %H:%M} {self.action}"


def audit(action, actor=None, municipality=None, obj=None, **detail):
    return AuditLog.objects.create(
        action=action,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        municipality=municipality,
        object_type=obj.__class__.__name__ if obj is not None else "",
        object_id=str(getattr(obj, "pk", "")) if obj is not None else "",
        detail=detail,
    )
