# SPDX-License-Identifier: EUPL-1.2
"""Cobros de reservas e inscricións.

Regras (v2, fase 3):
- Unha reserva **só se confirma cun pagamento aceptado**: notificación verificada da pasarela ou
  cobro rexistrado polo persoal no mostrador.
- Un pagamento **rexeitado** libera a franxa e **non** envía confirmación.
- Mentres se paga, a franxa queda bloqueada `EIRA_PAYMENT_HOLD_MINUTES` (10 min). Se caduca, a reserva
  pasa a «caducada» e a franxa queda libre.
- Un pagamento resolto (pagado, rexeitado, caducado ou devolto) **xa non cambia** por outra notificación.
- Se chega un pagamento aceptado tarde (reserva caducada), confírmase se a franxa segue libre; se non,
  devólvese automaticamente.
"""

import logging
import secrets

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import audit
from apps.integrations.payments import InvalidSignature
from apps.integrations.registry import get_adapter
from apps.notifications.services import notify

from .models import Booking, Payment

log = logging.getLogger("eira.payments")


def new_reference():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "EI" + "".join(secrets.choice(alphabet) for _ in range(10))


def start_online_payment(*, booking=None, enrollment=None, url_ok, url_ko):
    """Crea un pagamento pendente e devolve a URL da pasarela."""
    target = booking or enrollment
    pending = Payment.objects.filter(status=Payment.Status.PENDING)
    pending = pending.filter(booking=booking) if booking else pending.filter(enrollment=enrollment)
    pending.update(
        status=Payment.Status.EXPIRED, resolved_at=timezone.now()
    )  # un só pagamento vivo
    if booking:
        concept = f"{booking.facility.name} · {timezone.localtime(booking.start):%d/%m %H:%M} · {booking.reference}"
        amount = booking.price_cents
    else:
        concept = f"{enrollment.group} · {enrollment.participant_name}"
        amount = enrollment.group.fee_cents
    payment = Payment.objects.create(
        municipality=target.municipality,
        booking=booking,
        enrollment=enrollment,
        concept=concept[:200],
        amount_cents=amount,
        reference=new_reference(),
    )
    if booking:
        booking.payment_reference = payment.reference
        booking.save(update_fields=["payment_reference"])
    return get_adapter("payment").start(payment, url_ok, url_ko)


def handle_notification(data):
    """Notificación servidor a servidor da pasarela. Devolve o Payment ou levanta InvalidSignature."""
    result = get_adapter("payment").parse_notification(data)
    with transaction.atomic():
        payment = Payment.objects.select_for_update().filter(reference=result.reference).first()
        if payment is None:
            log.warning("Notificación para unha referencia descoñecida: %s", result.reference)
            return None
        if payment.is_final:
            log.info("Notificación repetida ignorada: %s (%s)", payment.reference, payment.status)
            return payment
        payment.signature_ok = True
        payment.provider_code = result.code
        payment.resolved_at = timezone.now()
        if result.ok and result.amount_cents == payment.amount_cents:
            payment.status = Payment.Status.PAID
            payment.save()
            _apply_paid(payment)
        else:
            payment.status = Payment.Status.REJECTED
            payment.save()
            _apply_rejected(payment)
    audit(
        "payment.notification",
        None,
        payment.municipality,
        payment,
        status=payment.status,
        code=result.code,
    )
    return payment


def _apply_paid(payment):
    from .services import BookingError, _validate_slot, mark_paid

    if payment.enrollment_id:
        from apps.activities.services import mark_enrollment_paid

        mark_enrollment_paid(payment.enrollment, payment.reference, payment.amount_cents)
        return
    booking = payment.booking
    if booking is None:
        return
    if booking.status == Booking.Status.PENDING_PAYMENT:
        mark_paid(booking, payment.reference, payment.amount_cents)
        return
    if booking.status in (Booking.Status.EXPIRED, Booking.Status.REJECTED):
        # Pagamento aceptado tarde: confírmase se a franxa segue libre; se non, devólvese.
        try:
            _validate_slot(
                booking.facility, booking.start, booking.end, exclude=booking, check_past=False
            )
        except BookingError:
            refund_payment(payment, payment.amount_cents, reason=_("A franxa xa non estaba libre"))
            notify(
                booking.user,
                _("Pagamento devolto: %(f)s") % {"f": booking.facility.name},
                _(
                    "O pagamento chegou despois de caducar a reserva e a franxa xa estaba ocupada. "
                    "Devolvémosche o importe íntegro."
                ),
                municipality=booking.municipality,
                level="warning",
            )
            return
        booking.status = Booking.Status.PENDING_PAYMENT
        booking.save(update_fields=["status"])
        mark_paid(booking, payment.reference, payment.amount_cents)


def _apply_rejected(payment):
    if payment.enrollment_id:
        e = payment.enrollment
        from apps.activities.models import Enrollment
        from apps.activities.services import promote_waitlist

        if e.status == Enrollment.Status.PENDING_PAYMENT:
            e.status = Enrollment.Status.CANCELLED
            e.save(update_fields=["status"])
            promote_waitlist(e.group)
        return
    booking = payment.booking
    if booking and booking.status == Booking.Status.PENDING_PAYMENT:
        booking.status = Booking.Status.REJECTED
        booking.hold_expires_at = None
        booking.cancel_reason = "payment rejected"
        booking.save(update_fields=["status", "hold_expires_at", "cancel_reason"])
        audit("booking.payment_rejected", None, booking.municipality, booking)
        notify(
            booking.user,
            _("Pagamento non completado: %(f)s") % {"f": booking.facility.name},
            _("O banco rexeitou o pagamento. Non se fixo ningún cargo e a franxa quedou libre."),
            municipality=booking.municipality,
            level="warning",
            email=False,
        )


def record_counter_payment(booking, method, by):
    """Cobro no mostrador (efectivo ou tarxeta no TPV físico), rexistrado polo persoal."""
    from .services import mark_paid

    payment = Payment.objects.create(
        municipality=booking.municipality,
        booking=booking,
        method=method,
        status=Payment.Status.PAID,
        concept=f"{booking.facility.name} · {booking.reference}",
        amount_cents=booking.price_cents,
        reference=new_reference(),
        resolved_at=timezone.now(),
        recorded_by=by,
    )
    Payment.objects.filter(booking=booking, status=Payment.Status.PENDING).update(
        status=Payment.Status.EXPIRED, resolved_at=timezone.now()
    )
    mark_paid(booking, payment.reference, payment.amount_cents)
    audit("payment.counter", by, booking.municipality, payment, method=method)
    return payment


def refund_payment(payment, amount_cents, reason=""):
    if amount_cents <= 0 or payment.status not in (
        Payment.Status.PAID,
        Payment.Status.PARTIALLY_REFUNDED,
    ):
        return 0
    amount_cents = min(amount_cents, payment.amount_cents - payment.refunded_cents)
    if payment.method == Payment.Method.ONLINE:
        get_adapter("payment").refund(payment, amount_cents)
    # Nos cobros de mostrador, a devolución faise en caixa; queda rexistrada igual.
    payment.refunded_cents += amount_cents
    payment.status = (
        Payment.Status.REFUNDED
        if payment.refunded_cents >= payment.amount_cents
        else Payment.Status.PARTIALLY_REFUNDED
    )
    payment.save(update_fields=["refunded_cents", "status"])
    audit("payment.refund", None, payment.municipality, payment, amount=amount_cents, reason=reason)
    return amount_cents


def refund_booking(booking, amount_cents):
    paid = booking.payments.filter(
        status__in=[Payment.Status.PAID, Payment.Status.PARTIALLY_REFUNDED]
    ).first()
    if paid is None:
        return 0
    return refund_payment(paid, amount_cents)


def expire_pending(now=None):
    """Reservas pendentes cuxo bloqueo caducou: «caducada» e franxa libre."""
    now = now or timezone.now()
    qs = Booking.objects.filter(status=Booking.Status.PENDING_PAYMENT, hold_expires_at__lte=now)
    ids = list(qs.values_list("pk", flat=True))
    Payment.objects.filter(booking_id__in=ids, status=Payment.Status.PENDING).update(
        status=Payment.Status.EXPIRED, resolved_at=now
    )
    return qs.update(status=Booking.Status.EXPIRED, cancel_reason="hold expired")


__all__ = [
    "InvalidSignature",
    "handle_notification",
    "start_online_payment",
    "record_counter_payment",
    "refund_payment",
    "refund_booking",
    "expire_pending",
]
