# SPDX-License-Identifier: EUPL-1.2
"""v4: avisos do concello. Segmentación, preferencias, consentimento, canles, programación e
cancelación das reservas afectadas. As canles externas van detrás dos adaptadores."""

import datetime as dt
import logging
import secrets

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import Role, User
from apps.integrations.registry import get_adapter

from .models import (
    CHANNELS,
    INFO,
    Category,
    Notice,
    NoticePreference,
    Notification,
    TelegramLink,
)

log = logging.getLogger("eira.notices")
PUSH_MAX = 120  # caracteres do corpo nunha notificación push


# ---------- Público ----------
def affected_bookings(notice):
    """Reservas que caen na franxa e nas instalacións do aviso (para avisar e, se se pide, cancelar)."""
    from apps.bookings.models import Booking

    if notice.audience not in (
        Notice.Audience.FACILITY,
        Notice.Audience.OUTDOOR,
        Notice.Audience.PARISH,
    ):
        return Booking.objects.none()
    qs = Booking.objects.filter(municipality=notice.municipality).holding()
    start = notice.window_start or timezone.now()
    end = notice.window_end or start + dt.timedelta(days=30)
    qs = qs.overlapping(start, end)
    if notice.audience == Notice.Audience.FACILITY:
        qs = qs.filter(facility=notice.facility)
    elif notice.audience == Notice.Audience.OUTDOOR:
        qs = qs.filter(facility__indoor=False)
    else:
        qs = qs.filter(facility__parish=notice.parish)
    return qs.select_related("facility", "user")


def audience(notice):
    """Persoas ás que se dirixe o aviso, antes de aplicar consentimento e preferencias."""
    m = notice.municipality
    if notice.audience == Notice.Audience.ALL:
        return User.objects.filter(
            memberships__municipality=m, memberships__role=Role.CITIZEN, is_active=True
        ).distinct()
    if notice.audience == Notice.Audience.ACTIVITY:
        from apps.activities.models import Enrollment

        ids = Enrollment.objects.filter(
            municipality=m, group__activity=notice.activity, status=Enrollment.Status.ACTIVE
        ).values_list("user_id", flat=True)
        return User.objects.filter(pk__in=ids, is_active=True)
    ids = affected_bookings(notice).exclude(user=None).values_list("user_id", flat=True)
    return User.objects.filter(pk__in=ids, is_active=True)


def preference(user, municipality):
    pref = NoticePreference.objects.filter(user=user, municipality=municipality).first()
    return pref or NoticePreference(user=user, municipality=municipality)


def has_consent(user, municipality):
    return bool(preference(user, municipality).comms_consent_at)


def channels_for(user, notice, pref=None):
    """Canles polas que esta persoa recibe este aviso (baleiro = non se lle envía nada).

    - Informativos: só con consentimento de comunicacións; despois, a matriz de preferencias.
    - De servizo: a quen lle afecta chégalle sempre na app; o resto, segundo as súas preferencias.
    """
    pref = pref or preference(user, notice.municipality)
    if notice.basis == INFO and not pref.comms_consent_at:
        return set()
    wanted = pref.channels_for(notice.category)
    if notice.basis != INFO:
        wanted.add("app")
    out = set(notice.channels) & wanted
    if "email" in out and not user.email:
        out.discard("email")
    if "telegram" in out and not user.telegram_chat:
        out.discard("telegram")
    if "push" in out and not user.push_subscriptions.exists():
        out.discard("push")
    return out


def estimate(notice):
    """Para a vista previa: cantas persoas o recibirían e por que canles; reservas afectadas."""
    counts = dict.fromkeys(CHANNELS, 0)
    people = 0
    for user in audience(notice):
        chans = channels_for(user, notice)
        if chans:
            people += 1
            for c in chans:
                counts[c] += 1
    return {
        "people": people,
        "counts": counts,
        "bookings": affected_bookings(notice).count() if notice.cancel_bookings else 0,
        "public_channel": "channel" in notice.channels
        and bool(notice.municipality.telegram_channel),
    }


# ---------- Contido por canle ----------
def render(notice):
    m = notice.municipality
    link = notice.url or ""
    cat = Category(notice.category).label
    telegram = f"*{notice.title}*\n{notice.body}" + (f"\n{link}" if link else "")
    return {
        "app": {"title": notice.title, "body": notice.body, "category": cat},
        "email": {
            "subject": f"{m.name} · {notice.title}",
            "body": f"{notice.body}\n\n{link}\n\n"
            + _("Recibes este aviso de %(m)s. Podes cambiar as túas preferencias na app.")
            % {"m": m.name},
        },
        "telegram": telegram,
        "push": {
            "title": notice.title,
            "body": notice.body
            if len(notice.body) <= PUSH_MAX
            else notice.body[: PUSH_MAX - 1] + "…",
        },
    }


# ---------- Envío ----------
def _close_affected(notice, by):
    """Cancela con devolución íntegra as reservas afectadas creando o peche correspondente."""
    from apps.bookings.services import apply_closure
    from apps.facilities.models import Closure

    start = notice.window_start or timezone.now()
    end = notice.window_end or start + dt.timedelta(hours=6)
    facilities = {b.facility for b in affected_bookings(notice)}
    kind = Closure.Kind.WEATHER if notice.category == Category.ALERT else Closure.Kind.OTHER
    total = 0
    for f in facilities:
        closure = Closure.objects.create(
            municipality=notice.municipality,
            facility=f,
            kind=kind,
            reason=notice.title,
            starts_at=start,
            ends_at=end,
        )
        total += len(apply_closure(closure, by=by))
    return total


@transaction.atomic
def send(notice, by=None, now=None):
    """Envía o aviso agora. Idempotente: un aviso xa enviado non se volve enviar."""
    notice = Notice.objects.select_for_update().get(pk=notice.pk)
    if notice.sent_at:
        return notice
    content = render(notice)
    people = list(audience(notice))  # antes de cancelar: despois as reservas xa non «ocupan»
    cancelled = _close_affected(notice, by) if notice.cancel_bookings else 0
    counts = dict.fromkeys(CHANNELS, 0)
    reached = 0
    for user in people:
        chans = channels_for(user, notice)
        if not chans:
            continue
        reached += 1
        try:
            if "email" in chans:
                get_adapter("mail").send(
                    user.email, content["email"]["subject"], content["email"]["body"]
                )
            if "telegram" in chans:
                get_adapter("telegram").send(user.telegram_chat, content["telegram"])
            if "push" in chans:
                for sub in user.push_subscriptions.all()[:5]:
                    get_adapter("push").send(
                        sub, content["push"]["title"], content["push"]["body"], notice.url
                    )
        except Exception:  # unha canle que falla non impide o resto nin o aviso na app
            log.exception("Fallo enviando o aviso %s", notice.pk)
        for c in chans:
            counts[c] += 1
        if "app" in chans:
            Notification.objects.create(
                user=user,
                municipality=notice.municipality,
                title=notice.title[:160],
                body=notice.body,
                url=notice.url,
                level=Notification.Level.WARNING
                if notice.basis != INFO
                else Notification.Level.INFO,
                channels=",".join(sorted(chans)),
                notice=notice,
                category=notice.category,
            )
    if "channel" in notice.channels and notice.municipality.telegram_channel:
        get_adapter("telegram").send(notice.municipality.telegram_channel, content["telegram"])
        counts["channel"] = 1
    notice.sent_at = now or timezone.now()
    notice.recipients, notice.cancelled, notice.sent_counts = reached, cancelled, counts
    notice.save(update_fields=["sent_at", "recipients", "cancelled", "sent_counts"])
    from apps.accounts.models import audit

    audit("notice.send", by, notice.municipality, notice, recipients=reached, cancelled=cancelled)
    return notice


def send_due(now=None):
    """Envía os avisos programados que xa tocan (orde `send_notices`, para cron/systemd timer)."""
    now = now or timezone.now()
    done = []
    for n in Notice.objects.filter(sent_at__isnull=True, publish_at__lte=now):
        done.append(send(n, by=n.created_by, now=now))
    return done


# ---------- Telegram: vinculación do bot persoal ----------
def new_link_code(user):
    TelegramLink.objects.filter(user=user, used_at__isnull=True).delete()
    code = secrets.token_hex(4).upper()
    TelegramLink.objects.create(user=user, code=code)
    return code


def bot_link_url(code):
    bot = getattr(settings, "EIRA_TELEGRAM_BOT", "") or "EiraDemoBot"
    return f"https://t.me/{bot}?start={code}"


def link_chat(code, chat_id, now=None):
    """`/start CODE` no bot: vincula o chat á conta. Un só uso e 30 minutos de validez."""
    now = now or timezone.now()
    link = (
        TelegramLink.objects.select_related("user")
        .filter(code=(code or "").strip().upper(), used_at__isnull=True)
        .first()
    )
    if not link or link.created_at < now - dt.timedelta(minutes=TelegramLink.TTL_MINUTES):
        return None
    link.used_at = now
    link.save(update_fields=["used_at"])
    user = link.user
    user.telegram_chat, user.notify_telegram = str(chat_id), True
    user.save(update_fields=["telegram_chat", "notify_telegram"])
    return user


def unlink(user):
    user.telegram_chat, user.notify_telegram = "", False
    user.save(update_fields=["telegram_chat", "notify_telegram"])


def handle_bot_message(chat_id, text):
    """Mensaxe recibida polo bot (webhook real ou simulador). Devolve a resposta enviada."""
    text = (text or "").strip()
    bot = get_adapter("telegram")
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        user = link_chat(parts[1] if len(parts) > 1 else "", chat_id)
        reply = (
            _(
                "Listo! Este chat queda vinculado á túa conta de Eira. Escribe /stop para desvincular."
            )
            if user
            else _("Ese código non vale ou xa caducou. Xera outro en Avisos › Preferencias.")
        )
    elif text == "/stop":
        user = User.objects.filter(telegram_chat=str(chat_id)).first()
        if user:
            unlink(user)
        reply = _("Desvinculado. Non recibirás máis avisos por aquí.")
    else:
        reply = _(
            "Son o bot de avisos de Eira. Para vincular a túa conta, abre a ligazón que che dá a app."
        )
    bot.send(str(chat_id), reply)
    return reply


def purge(now=None, months=12):
    """Prazos de conservación (docs/rxpd/avisos.md): avisos recibidos 12 meses; códigos de
    vinculación de Telegram, 1 día (caducan aos 30 min)."""
    now = now or timezone.now()
    n, _ = Notification.objects.filter(created_at__lt=now - dt.timedelta(days=30 * months)).delete()
    TelegramLink.objects.filter(created_at__lt=now - dt.timedelta(days=1)).delete()
    return n
