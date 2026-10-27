# SPDX-License-Identifier: EUPL-1.2
"""Instalacións, horarios, peches, tarifas e normas versionadas."""

import secrets

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import TenantModel


class Parish(TenantModel):
    name = models.CharField(_("nome"), max_length=80)

    class Meta:
        verbose_name = _("parroquia")
        verbose_name_plural = _("parroquias")
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["municipality", "name"], name="uniq_parish")]

    def __str__(self):
        return self.name


class FacilityKind(models.TextChoices):
    OUTDOOR_COURT = "outdoor_court", _("Pista exterior")
    SPORTS_HALL = "sports_hall", _("Pavillón")
    GRASS_FIELD = "grass_field", _("Campo de herba")
    GYM = "gym", _("Ximnasio")
    POOL = "pool", _("Piscina")
    PADEL = "padel", _("Pista de pádel")
    OTHER = "other", _("Outra")


class BookingMode(models.TextChoices):
    DIRECT = "direct", _("Reserva directa")
    APPROVAL = "approval", _("Con aprobación do concello")


class AccessLevel(models.IntegerChoices):
    OPEN = 0, _("Aberta (QR de entrada)")
    CUSTODIAN = 1, _("Chave custodiada")
    OFFLINE_CODE = 2, _("Código temporal sen conexión")
    CONNECTED = 3, _("Pechadura conectada")


def new_token():
    return secrets.token_urlsafe(16)


class Facility(TenantModel):
    name = models.CharField(_("nome"), max_length=120)
    kind = models.CharField(_("tipo"), max_length=20, choices=FacilityKind.choices)
    parish = models.ForeignKey(
        Parish, verbose_name=_("parroquia"), null=True, blank=True, on_delete=models.SET_NULL
    )
    description = models.TextField(_("descrición"), blank=True)
    address = models.CharField(_("enderezo"), max_length=200, blank=True)
    latitude = models.DecimalField(
        _("latitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        _("lonxitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    photo = models.ImageField(_("foto"), upload_to="facilities/", blank=True)
    photo_alt = models.CharField(_("texto alternativo da foto"), max_length=200, blank=True)
    indoor = models.BooleanField(_("cuberta"), default=False)
    lighting = models.BooleanField(_("iluminación"), default=False)
    # Accesibilidade física
    step_free = models.BooleanField(_("acceso sen chanzos"), default=False)
    adapted_toilet = models.BooleanField(_("aseo adaptado"), default=False)
    adapted_changing = models.BooleanField(_("vestiario adaptado"), default=False)
    accessible_parking = models.BooleanField(_("aparcadoiro reservado"), default=False)
    lift = models.BooleanField(_("ascensor ou plataforma"), default=False)
    hearing_loop = models.BooleanField(_("bucle magnético"), default=False)
    braille_signage = models.BooleanField(_("sinalización en braille e relevo"), default=False)
    accessibility_notes = models.TextField(_("notas de accesibilidade"), blank=True)
    capacity = models.PositiveIntegerField(
        _("prazas simultáneas"),
        default=1,
        help_text=_("1 = uso exclusivo (pista). Máis de 1 = uso compartido (ximnasio, piscina)."),
    )
    slot_minutes = models.PositiveIntegerField(_("duración da franxa (min)"), default=60)
    access_level = models.IntegerField(
        _("nivel de acceso"), choices=AccessLevel.choices, default=AccessLevel.OPEN
    )
    # Nivel 1: chave custodiada
    key_holder_name = models.CharField(_("custodia da chave"), max_length=120, blank=True)
    key_holder_place = models.CharField(_("onde se recolle"), max_length=200, blank=True)
    key_holder_hours = models.CharField(_("horario de recollida"), max_length=120, blank=True)
    key_holder_phone = models.CharField(_("teléfono da custodia"), max_length=20, blank=True)
    key_holder_email = models.EmailField(_("correo da custodia"), blank=True)
    # Nivel 0: QR fixo de entrada
    checkin_token = models.CharField(max_length=32, default=new_token, unique=True, editable=False)
    is_published = models.BooleanField(_("publicada"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # v5 · Reserva: participantes, aprobación, formas de pagamento e luz
    max_participants = models.PositiveIntegerField(
        _("persoas máximas por reserva"),
        default=12,
        help_text=_("Ao reservar pídese o número de persoas, ata este máximo."),
    )
    booking_mode = models.CharField(
        _("modo de reserva"),
        max_length=10,
        choices=BookingMode.choices,
        default=BookingMode.DIRECT,
    )
    payment_methods = models.JSONField(
        _("formas de pagamento da instalación"),
        default=list,
        blank=True,
        help_text=_("Baleiro = as do concello."),
    )
    lighting_supplement_cents = models.PositiveIntegerField(
        _("suplemento de iluminación (céntimos)"),
        default=0,
        help_text=_("0 = sen suplemento. Aplícase nas franxas que precisan luz ou se se pide."),
    )
    # v5 · Seguridade e confianza (ficha)
    equipment = models.TextField(
        _("material dispoñible"),
        blank=True,
        help_text=_("Un por liña, coa cantidade primeiro. P. ex. «2 balóns»."),
    )
    accident_protocol = models.TextField(
        _("protocolo en caso de accidente"),
        blank=True,
        help_text=_("Texto breve: que facer mentres chega a axuda."),
    )
    aed_location = models.CharField(
        _("DEA máis próximo"),
        max_length=200,
        blank=True,
        help_text=_("Onde está o desfibrilador máis próximo."),
    )
    # v1.2 · C: accesibilidade detallada {clave: {"value": yes|partial|no, "note": ""}}
    accessibility_detail = models.JSONField(_("accesibilidade detallada"), default=dict, blank=True)
    # v1.2 · C: sostibilidade
    bike_parking_spaces = models.PositiveIntegerField(
        _("aparcabicis (prazas)"), null=True, blank=True, help_text=_("Baleiro = sen datos.")
    )
    ev_chargers = models.PositiveIntegerField(
        _("puntos de recarga de vehículo eléctrico"), default=0
    )
    ev_charger_type = models.CharField(
        _("tipo de recarga"), max_length=80, blank=True, help_text=_("P. ex. «Tipo 2, 7 kW»")
    )
    transit_stop = models.CharField(
        _("parada de transporte público próxima"),
        max_length=160,
        blank=True,
        help_text=_("Opcional. P. ex. «Bus liña 2, parada Igrexa (200 m)»"),
    )
    # v1.2 · C: DESA (desfibrilador)
    aed_on_site = models.BooleanField(_("DESA na instalación"), null=True, blank=True)
    aed_inside_location = models.CharField(
        _("ubicación exacta do DESA"), max_length=200, blank=True
    )
    aed_hours = models.CharField(_("horario de acceso ao DESA"), max_length=120, blank=True)
    aed_near_name = models.CharField(_("DESA máis próximo: nome"), max_length=160, blank=True)
    aed_near_address = models.CharField(
        _("DESA máis próximo: enderezo"), max_length=200, blank=True
    )
    aed_near_distance_m = models.PositiveIntegerField(
        _("DESA máis próximo: distancia aproximada (m)"), null=True, blank=True
    )
    aed_near_hours = models.CharField(_("DESA máis próximo: horario"), max_length=120, blank=True)

    class Meta:
        verbose_name = _("instalación")
        verbose_name_plural = _("instalacións")
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_shared(self):
        return self.capacity > 1

    def current_rules(self):
        return self.rules_versions.order_by("-version").first()

    # (campo, icona) na orde en que se amosan
    ACCESSIBILITY = (
        ("step_free", "ramp"),
        ("lift", "lift"),
        ("adapted_toilet", "toilet"),
        ("adapted_changing", "hanger"),
        ("accessible_parking", "parking"),
        ("hearing_loop", "ear"),
        ("braille_signage", "braille"),
    )

    @property
    def needs_approval(self):
        return self.booking_mode == BookingMode.APPROVAL

    def payment_method_list(self):
        """Formas de pagamento efectivas: as da instalación (se as ten) dentro das do concello.

        O aprazado só se o concello o activou."""
        from apps.tenants.models import PaymentMethod

        town = self.municipality.payment_method_list()
        own = [m for m in (self.payment_methods or []) if m in PaymentMethod.values]
        methods = own or town
        if PaymentMethod.DEFERRED in methods and PaymentMethod.DEFERRED not in town:
            methods = [m for m in methods if m != PaymentMethod.DEFERRED]
        return methods or [PaymentMethod.TPV.value]

    def equipment_items(self):
        """«2 balóns» → {"qty": 2, "name": "balóns"}; sen número, cantidade baleira."""
        out = []
        for line in self.equipment.splitlines():
            line = line.strip("-• ").strip()
            if not line:
                continue
            head, _sep, rest = line.partition(" ")
            if head.isdigit() and rest:
                out.append({"qty": int(head), "name": rest.strip()})
            else:
                out.append({"qty": None, "name": line})
        return out

    def last_supervision(self):
        """Data da última orde de mantemento pechada nesta instalación (calculada).

        v1.1: as ordes de limpeza non contan como supervisión (teñen a súa «Última limpeza»)."""
        order = (
            self.work_orders.filter(status="done", closed_at__isnull=False)
            .exclude(kind="cleaning")
            .order_by("-closed_at")
            .first()
        )
        return order.closed_at if order else None

    def last_cleaning(self):
        """v1.1: data e hora do último rexistro de limpeza (QR ou orde de limpeza)."""
        log = self.cleaning_logs.order_by("-done_at").first()
        return log.done_at if log else None

    def safety_review(self):
        """Última revisión de seguridade inicial Eira pechada (v5 · H) ou None."""
        return (
            self.work_orders.filter(kind="safety_review", status="done", closed_at__isnull=False)
            .order_by("-closed_at")
            .first()
        )

    # v1.2 · C: accesibilidade detallada (clave, etiqueta, icona, campo básico que enche)
    ACCESSIBILITY_DETAIL = (
        ("pmr_parking", _("Aparcamento reservado PMR"), "parking", "accessible_parking"),
        ("route", _("Itinerario accesible desde o exterior"), "ramp", "step_free"),
        ("widths", _("Corredores e portas con anchura suficiente"), "door", None),
        ("toilets", _("Aseos adaptados"), "toilet", "adapted_toilet"),
        ("changing", _("Vestiarios adaptados"), "hanger", "adapted_changing"),
        ("stands", _("Bancadas con prazas reservadas"), "users", None),
        ("signage", _("Sinalización accesible"), "braille", "braille_signage"),
    )
    DETAIL_VALUES = (("yes", _("Si")), ("partial", _("Parcial")), ("no", _("Non")))

    def accessibility_points(self):
        """Os 7 puntos con valor (si / parcial / non / sen datos) e nota."""
        labels = dict(self.DETAIL_VALUES)
        detail = self.accessibility_detail or {}
        out = []
        for key, label, icon, _basic in self.ACCESSIBILITY_DETAIL:
            item = detail.get(key) or {}
            value = item.get("value", "")
            out.append(
                {
                    "key": key,
                    "label": label,
                    "icon": icon,
                    "value": value,
                    "value_label": labels.get(value, _("Sen datos")),
                    "note": item.get("note", ""),
                }
            )
        return out

    def has_accessibility_detail(self):
        return any(p["value"] for p in self.accessibility_points())

    def sync_basic_accessibility(self):
        """A lista básica (v2) enchese a partir da detallada: só «si» conta como si.

        Os puntos sen datos non cambian o valor básico que xa houbese."""
        detail = self.accessibility_detail or {}
        for key, _label, _icon, basic in self.ACCESSIBILITY_DETAIL:
            value = (detail.get(key) or {}).get("value", "")
            if basic and value:
                setattr(self, basic, value == "yes")

    @property
    def is_accessible(self):
        """Filtro «accesible»: itinerario desde o exterior e corredores/portas con «si»."""
        d = self.accessibility_detail or {}
        return all((d.get(k) or {}).get("value") == "yes" for k in ("route", "widths"))

    @property
    def has_bike_parking(self):
        return bool(self.bike_parking_spaces)

    def accessibility_features(self):
        return [
            {"icon": icon, "label": self._meta.get_field(field).verbose_name}
            for field, icon in self.ACCESSIBILITY
            if getattr(self, field)
        ]


class Weekday(models.IntegerChoices):
    MON = 0, _("Luns")
    TUE = 1, _("Martes")
    WED = 2, _("Mércores")
    THU = 3, _("Xoves")
    FRI = 4, _("Venres")
    SAT = 5, _("Sábado")
    SUN = 6, _("Domingo")


class OpeningHours(models.Model):
    """Franxas de apertura por día da semana, opcionalmente limitadas a unha tempada."""

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="opening_hours")
    weekday = models.IntegerField(_("día"), choices=Weekday.choices)
    opens = models.TimeField(_("abre"))
    closes = models.TimeField(_("pecha"))
    season_start = models.DateField(_("inicio de tempada"), null=True, blank=True)
    season_end = models.DateField(_("fin de tempada"), null=True, blank=True)

    class Meta:
        verbose_name = _("horario")
        verbose_name_plural = _("horarios")
        ordering = ["weekday", "opens"]

    def applies_on(self, day):
        if self.season_start and day < self.season_start:
            return False
        return not (self.season_end and day > self.season_end)


class Closure(TenantModel):
    """Festivo, evento, obra ou alerta meteorolóxica. Sen instalación = todo o concello."""

    class Kind(models.TextChoices):
        HOLIDAY = "holiday", _("Festivo")
        EVENT = "event", _("Evento")
        WORKS = "works", _("Obras")
        WEATHER = "weather", _("Alerta meteorolóxica")
        OTHER = "other", _("Outro")

    facility = models.ForeignKey(
        Facility,
        verbose_name=_("instalación"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="closures",
    )
    kind = models.CharField(_("motivo"), max_length=20, choices=Kind.choices, default=Kind.OTHER)
    reason = models.CharField(_("descrición"), max_length=200)
    starts_at = models.DateTimeField(_("desde"))
    ends_at = models.DateTimeField(_("ata"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("peche ou bloqueo")
        verbose_name_plural = _("peches e bloqueos")
        ordering = ["starts_at"]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.reason}"


class Tariff(models.Model):
    class Audience(models.TextChoices):
        RESIDENT = "resident", _("Persoas empadroadas")
        NON_RESIDENT = "non_resident", _("Persoas non empadroadas")
        YOUTH = "youth", _("Mocidade (ata 25 anos, empadroada)")
        SENIOR = "senior", _("Maiores de 65 (empadroadas)")
        REDUCED = "reduced", _("Colectivos con tarifa reducida (validado polo concello)")

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="tariffs")
    audience = models.CharField(_("colectivo"), max_length=20, choices=Audience.choices)
    price_cents = models.PositiveIntegerField(_("prezo por franxa (céntimos)"))

    class Meta:
        verbose_name = _("tarifa")
        verbose_name_plural = _("tarifas")
        constraints = [models.UniqueConstraint(fields=["facility", "audience"], name="uniq_tariff")]


class RulesVersion(models.Model):
    """Normas de uso, dereitos e deberes. Inmutables: cada cambio crea unha versión nova."""

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="rules_versions")
    version = models.PositiveIntegerField()
    text = models.TextField(_("normas"))
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = _("versión das normas")
        verbose_name_plural = _("versións das normas")
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["facility", "version"], name="uniq_rules_version")
        ]

    def __str__(self):
        return f"v{self.version}"

    @classmethod
    def publish(cls, facility, text, user=None):
        last = cls.objects.filter(facility=facility).order_by("-version").first()
        if last and last.text.strip() == text.strip():
            return last
        return cls.objects.create(
            facility=facility, version=(last.version + 1 if last else 1), text=text, created_by=user
        )

    def lines(self):
        return [line.strip("-• ").strip() for line in self.text.splitlines() if line.strip()]


class Equipment(models.Model):
    """v1.2 · D: inventario de equipos que consomen enerxía (introdúceo o concello)."""

    class Kind(models.TextChoices):
        LIGHTING = "lighting", _("Iluminación")
        HVAC = "hvac", _("Calefacción ou climatización")
        DHW = "dhw", _("Auga quente sanitaria")
        PUMPS = "pumps", _("Bombas ou depuración")
        OTHER = "other", _("Outros")

    class Mode(models.TextChoices):
        OPENING = "opening", _("Durante a apertura")
        BOOKING = "booking", _("Só con reserva")
        LIGHT = "light", _("Só con suplemento de luz")
        CONTINUOUS = "continuous", _("Continuo")

    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, related_name="energy_equipment"
    )
    kind = models.CharField(_("tipo"), max_length=10, choices=Kind.choices)
    name = models.CharField(_("descrición"), max_length=120, blank=True)
    power_kw = models.DecimalField(_("potencia (kW)"), max_digits=7, decimal_places=2)
    mode = models.CharField(_("modo de uso"), max_length=12, choices=Mode.choices)
    use_factor = models.DecimalField(
        _("factor de uso (0–1)"),
        max_digits=3,
        decimal_places=2,
        default=1,
        help_text=_("Parte do tempo que está a funcionar a potencia indicada."),
    )

    class Meta:
        verbose_name = _("equipo")
        verbose_name_plural = _("equipos")
        ordering = ["kind", "pk"]

    def __str__(self):
        return self.name or self.get_kind_display()


class EnergyReading(models.Model):
    """v1.2 · D: lectura real dunha factura, para comparar co consumo estimado."""

    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="energy_readings")
    period_start = models.DateField(_("desde"))
    period_end = models.DateField(_("ata"))
    kwh = models.DecimalField(_("consumo facturado (kWh)"), max_digits=10, decimal_places=1)
    cost_cents = models.PositiveIntegerField(_("importe (céntimos)"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("lectura de factura")
        verbose_name_plural = _("lecturas de facturas")
        ordering = ["-period_start"]
