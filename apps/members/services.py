# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · H: abonos, desconto e QR asinado do carné municipal.

QR do carné:
- **Dixital (app):** `TimestampSigner` co segredo da instalación; caduca aos `CARD_QR_SECONDS`
  (3 min). A páxina renóvao cada minuto. Unha captura de pantalla non serve despois.
- **Impreso (PDF):** asinado sen caducidade curta pero coa versión do carné e a data de fin do
  abono; se se perde, o concello sobe a versión e o impreso deixa de valer.
O QR só leva o identificador do carné (nada de nome nin datos persoais)."""

import datetime as dt

from django.core import signing
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import audit
from apps.notifications.services import notify

from .models import MemberCard, SportsPass

CARD_QR_SECONDS = 180
SALT_LIVE = "eira.card.live"
SALT_PRINT = "eira.card.print"


class CardError(Exception):
    pass


# ------------------------------------------------------------------ abonos
def active_pass(municipality, user, day=None):
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    day = day or timezone.localdate()
    cache = getattr(user, "_eira_pass_cache", None)
    if cache is None:
        cache = {}
        try:
            user._eira_pass_cache = cache
        except AttributeError:
            pass
    key = (municipality.pk, day)
    if key not in cache:
        cache[key] = (
            SportsPass.objects.filter(
                municipality=municipality,
                user=user,
                status=SportsPass.Status.ACTIVE,
                starts_on__lte=day,
                expires_on__gte=day,
            )
            .select_related("type")
            .order_by("-type__discount_pct")
            .first()
        )
    return cache[key]


def member_discount(municipality, user, day=None):
    """Desconto de abonado/a (%) nese día, ou 0."""
    if not municipality.module_enabled("cards"):
        return 0
    p = active_pass(municipality, user, day)
    return p.type.discount_pct if p else 0


def buy_pass(pass_type, user, *, method=None, by=None):
    """Alta ou renovación. Con `method` (oficina: efectivo ou tarxeta) queda activo ao momento;
    sen el, queda pendente do TPV."""
    from apps.bookings.models import Payment
    from apps.bookings.payments import new_reference

    p = SportsPass.objects.create(
        municipality=pass_type.municipality,
        user=user,
        type=pass_type,
        price_cents=pass_type.price_cents,
        channel="office" if method else "online",
        sold_by=by,
    )
    if method:
        Payment.objects.create(
            municipality=p.municipality,
            sports_pass=p,
            method=method,
            status=Payment.Status.PAID,
            concept=f"{pass_type.name} · {user}"[:200],
            amount_cents=p.price_cents,
            reference=new_reference(),
            resolved_at=timezone.now(),
            recorded_by=by,
        )
        activate_pass(p)
        audit("pass.sold", by, p.municipality, p, method=method)
    return p


def activate_pass(p):
    """Renovación: se xa ten un abono activo, o novo empeza cando remata o anterior."""
    if p.status != SportsPass.Status.PENDING:
        return p
    today = timezone.localdate()
    current = (
        SportsPass.objects.filter(
            municipality=p.municipality,
            user=p.user,
            status=SportsPass.Status.ACTIVE,
            expires_on__gte=today,
        )
        .exclude(pk=p.pk)
        .order_by("-expires_on")
        .first()
    )
    p.starts_on = (current.expires_on + dt.timedelta(days=1)) if current else today
    p.expires_on = p.starts_on + dt.timedelta(days=p.type.valid_days - 1)
    p.status = SportsPass.Status.ACTIVE
    p.save(update_fields=["starts_on", "expires_on", "status"])
    ensure_card(p.municipality, p.user)
    notify(
        p.user,
        _("Abono activado: %(n)s") % {"n": p.type.name},
        _("Válido do %(a)s ao %(b)s. O teu carné está na app.")
        % {"a": p.starts_on.strftime("%d/%m/%Y"), "b": p.expires_on.strftime("%d/%m/%Y")},
        municipality=p.municipality,
        level="success",
    )
    return p


def expire_passes(today=None):
    today = today or timezone.localdate()
    return SportsPass.objects.filter(status=SportsPass.Status.ACTIVE, expires_on__lt=today).update(
        status=SportsPass.Status.EXPIRED
    )


# ------------------------------------------------------------------ carné
def ensure_card(municipality, user):
    card = MemberCard.objects.filter(municipality=municipality, user=user).first()
    if card is None:
        for _attempt in range(5):
            candidate = MemberCard(municipality=municipality, user=user)
            if not MemberCard.objects.filter(
                municipality=municipality, number=candidate.number
            ).exists():
                candidate.save()
                return candidate
        raise CardError("Non se puido xerar un número de carné.")
    return card


def live_token(card):
    return signing.TimestampSigner(salt=SALT_LIVE).sign(f"{card.pk}.{card.version}")


def print_token(card, until=None):
    until = until or (timezone.localdate() + dt.timedelta(days=365))
    return signing.Signer(salt=SALT_PRINT).sign(f"{card.pk}.{card.version}.{until.isoformat()}")


def read_token(token, municipality, *, max_age=CARD_QR_SECONDS):
    """Valida o QR do carné (dixital ou impreso) e devolve o carné; se non, CardError."""
    token = (token or "").strip()
    try:
        value = signing.TimestampSigner(salt=SALT_LIVE).unsign(token, max_age=max_age)
        pk, version = value.split(".")
    except signing.SignatureExpired as exc:
        raise CardError(_("O QR caducou: pide que o actualice na app.")) from exc
    except (signing.BadSignature, ValueError):
        try:
            value = signing.Signer(salt=SALT_PRINT).unsign(token)
            pk, version, until = value.split(".")
        except (signing.BadSignature, ValueError) as exc:
            raise CardError(_("Este QR non é un carné válido.")) from exc
        if dt.date.fromisoformat(until) < timezone.localdate():
            raise CardError(_("O carné impreso caducou.")) from None
    card = (
        MemberCard.objects.filter(municipality=municipality, pk=pk)
        .select_related("user", "municipality")
        .first()
    )
    if card is None or str(card.version) != version:
        raise CardError(_("Este carné xa non é válido (anulado ou doutro concello)."))
    return card


def revoke_printed(card, by=None):
    card.version += 1
    card.save(update_fields=["version"])
    audit("card.revoke", by, card.municipality, card)
    return card


def card_status(card, day=None):
    """O que ve o persoal ao ler o carné: nome, abono e validez, bonos e a reserva de agora."""
    from apps.bookings.models import Booking, Voucher

    now = timezone.now()
    p = active_pass(card.municipality, card.user, day)
    booking = (
        Booking.objects.filter(
            municipality=card.municipality,
            user=card.user,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.USED],
            start__lte=now + dt.timedelta(minutes=30),
            end__gt=now,
        )
        .select_related("facility")
        .order_by("start")
        .first()
    )
    vouchers = Voucher.objects.filter(
        municipality=card.municipality, user=card.user, status=Voucher.Status.ACTIVE
    ).select_related("type")
    return {"card": card, "pass": p, "booking": booking, "vouchers": list(vouchers)}


def checkin_with_card(card, by=None):
    """Entrada coa reserva que a persoa ten agora (ou nos próximos 30 min)."""
    from apps.bookings.services import check_in

    status = card_status(card)
    b = status["booking"]
    if b is None:
        raise CardError(_("Esta persoa non ten ningunha reserva agora."))
    check_in(b)
    audit("card.checkin", by, card.municipality, b)
    return b
