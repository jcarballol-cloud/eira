# SPDX-License-Identifier: EUPL-1.2
"""v4: avisos de demostración (ficticios). Envíanse de verdade polos adaptadores simulados, así
que a bandexa de correo e o simulador de Telegram nunca quedan baleiros despois de rexenerar."""

import datetime as dt

from django.utils import timezone

from apps.accounts.models import Role, User
from apps.bookings.models import Booking
from apps.facilities.models import Facility
from apps.integrations.models import DevMail, OutboundMessage

from . import notices
from .models import Notice, NoticePreference, Notification
from .services import notify

# Nomes de canle claramente de demo (non usar nomes que poidan existir en Telegram)
CHANNELS = {"vilardeiras": "@eira_demo_vilardeiras", "pontedouro": "@eira_demo_pontedouro"}
UXIA_CHAT = "100000001"  # identificador ficticio do chat de Uxía co bot


def _at(days=0, hour=10, minute=0):
    d = timezone.localdate() + dt.timedelta(days=days)
    return timezone.make_aware(dt.datetime.combine(d, dt.time(hour, minute)))


def _backdate(since_ids, when):
    """Pon a data do aviso nos correos, mensaxes e avisos creados ao envialo."""
    mail_id, msg_id, notif_id = since_ids
    DevMail.objects.filter(pk__gt=mail_id).update(sent_at=when)
    OutboundMessage.objects.filter(pk__gt=msg_id).update(sent_at=when)
    Notification.objects.filter(pk__gt=notif_id).update(created_at=when)


def _marks():
    last = lambda qs: qs.order_by("-pk").values_list("pk", flat=True).first() or 0  # noqa: E731
    return last(DevMail.objects), last(OutboundMessage.objects), last(Notification.objects)


def _send(m, when, **data):
    data.setdefault("channels", ["app", "email", "telegram", "channel"])
    n = Notice.objects.create(municipality=m, **data)
    marks = _marks()
    notices.send(n, now=when)
    _backdate(marks, when)
    return n


def preferences(m, users, rng):
    """Consentimentos e preferencias: Uxía e Manuel aceptan; a metade da veciñanza tamén."""
    now = timezone.now()
    for u in users:
        consent = u.email.startswith(("uxia", "manuel", "rosa")) or rng.random() < 0.5
        NoticePreference.objects.update_or_create(
            user=u,
            municipality=m,
            defaults={
                "comms_consent_at": now - dt.timedelta(days=60) if consent else None,
                # Manuel prefire correo e app, sen Telegram nin push
                "matrix": {}
                if not u.email.startswith("manuel")
                else {
                    c: ["app", "email"]
                    for c in (
                        "closure",
                        "alert",
                        "schedule",
                        "activity",
                        "activity_change",
                        "event",
                        "news",
                    )
                },
            },
        )


def outdoor_bookings(m, start, end, rng):
    """Reservas pagadas nas pistas descubertas na franxa da alerta, para que se vexa a cancelación."""
    from apps.bookings.models import Payment
    from apps.bookings.payments import new_reference
    from apps.bookings.services import slot_starts

    people = list(
        User.objects.filter(
            memberships__municipality=m,
            memberships__role=Role.CITIZEN,
            email__startswith="vecinanza",
        )[:12]
    )
    for f in Facility.objects.filter(municipality=m, indoor=False, is_published=True)[:3]:
        price = {t.audience: t.price_cents for t in f.tariffs.all()}.get("resident", 0)
        slots = [s for s in slot_starts(f, timezone.localdate(start)) if start <= s < end]
        for s in slots[:2]:
            e = s + dt.timedelta(minutes=f.slot_minutes)
            if Booking.objects.filter(facility=f, start__lt=e, end__gt=s).holding().exists():
                continue
            ref = new_reference() if price else ""
            b = Booking.objects.create(
                municipality=m,
                facility=f,
                user=rng.choice(people),
                start=s,
                end=e,
                status="confirmed",
                tariff_audience="resident",
                price_cents=price,
                base_price_cents=price,
                paid_cents=price,
                payment_reference=ref,
                rules_version=f.current_rules(),
                rules_accepted_at=timezone.now(),
            )
            if price:
                Payment.objects.create(
                    municipality=m,
                    booking=b,
                    concept=f"{f.name} · {b.reference}",
                    amount_cents=price,
                    status=Payment.Status.PAID,
                    reference=ref,
                    signature_ok=True,
                    provider_code="0000",
                    resolved_at=timezone.now(),
                )


def seed(rng):
    for slug, channel in CHANNELS.items():
        from apps.tenants.models import Municipality

        Municipality.objects.filter(slug=slug).update(telegram_channel=channel)
    from apps.tenants.models import Municipality

    vil = Municipality.objects.get(slug="vilardeiras")
    pon = Municipality.objects.get(slug="pontedouro")
    admin = User.objects.filter(memberships__municipality=vil, memberships__role=Role.ADMIN).first()
    for m in (vil, pon):
        people = User.objects.filter(memberships__municipality=m, memberships__role=Role.CITIZEN)
        preferences(m, people, rng)

    # Uxía vinculou o bot persoal (como se abrise a ligazón da app)
    uxia = User.objects.get(email="uxia@demo.eira.example")
    code = notices.new_link_code(uxia)
    OutboundMessage.objects.create(
        channel="telegram", target=UXIA_CHAT, payload={"text": f"/start {code}", "from": "user"}
    )
    notices.handle_bot_message(UXIA_CHAT, f"/start {code}")
    OutboundMessage.objects.filter(target=UXIA_CHAT).update(sent_at=_at(-45, 18, 2))

    # Correos e mensaxes coherentes coas reservas próximas das persoas da demo
    for b in Booking.objects.filter(
        user__email__endswith="@demo.eira.example", status="confirmed", start__gte=timezone.now()
    ).select_related("facility", "user", "municipality"):
        from apps.tenants.urlutils import treverse

        marks = _marks()
        notify(
            b.user,
            f"Reserva confirmada: {b.facility.name}",
            f"{timezone.localtime(b.start):%d/%m/%Y} de {timezone.localtime(b.start):%H:%M} a "
            f"{timezone.localtime(b.end):%H:%M}. Referencia {b.reference}.",
            url=treverse(b.municipality, "bookings:detail", b.pk),
            municipality=b.municipality,
            level="success",
        )
        _backdate(marks, b.created_at)

    f = {x.kind: x for x in Facility.objects.filter(municipality=vil)}
    hall = f.get("sports_hall")
    from apps.activities.models import Activity

    multi = Activity.objects.filter(municipality=vil, name__icontains="Ximnasia activa").first()
    senior = Activity.objects.filter(municipality=vil, name__icontains="mantemento").first()
    football = Activity.objects.filter(municipality=vil, name__icontains="fútbol").first()

    plan = [
        (
            -40,
            dict(
                category="event",
                title="Festas de San Roque: horario especial",
                body="Do 14 ao 17 o ximnasio pecha ás 14:00 e as pistas da Pereira ábrense para o torneo de festas. Bo proveito!",
            ),
        ),
        (
            -35,
            dict(
                category="news",
                title="Nova pista de pádel na Pereira",
                body="Xa se pode reservar a nova pista de pádel cuberta da Pereira, con código na porta e luz automática.",
            ),
        ),
        (
            -30,
            dict(
                category="activity",
                title="Abertas as inscricións de multideporte",
                body="Para crianzas de 6 a 12 anos, luns e mércores ás 17:30. Inscrición na app, en Actividades.",
            ),
        ),
        (
            -28,
            dict(
                category="schedule",
                title="Horario de outono do ximnasio",
                body="Desde o 1 de outubro, de luns a venres de 7:30 a 22:00 e sábados de 9:00 a 14:00.",
            ),
        ),
        (
            -20,
            dict(
                category="closure",
                title="Pavillón pechado por mantemento do parqué",
                body="O pavillón estará pechado do 3 ao 5 por traballos no parqué. As reservas afectadas xa se cancelaron con devolución.",
                audience="facility",
                facility=hall,
                window_start=_at(-19, 8),
                window_end=_at(-17, 22),
            ),
        ),
        (
            -12,
            dict(
                category="alert",
                title="Alerta amarela por choiva",
                body="MeteoGalicia prevé choiva intensa á tarde. Revisa a túa reserva nas pistas exteriores.",
                audience="outdoor",
                window_start=_at(-12, 15),
                window_end=_at(-12, 21),
            ),
        ),
        (
            -10,
            dict(
                category="activity",
                title="Ximnasia activa: quedan 4 prazas",
                body="Aínda hai 4 prazas no grupo de ximnasia activa dos sábados ás 11:00.",
                audience="activity",
                activity=multi,
            ),
        ),
        (
            -8,
            dict(
                category="closure",
                title="Piscina: vaso pequeno pechado pola mañá",
                body="O vaso pequeno pecha de 9:00 a 13:00 por revisión da depuradora. O vaso grande segue aberto.",
                audience="all",
            ),
        ),
        (
            -7,
            dict(
                category="news",
                title="Agora abres a porta co código da reserva",
                body="No ximnasio e no pádel xa non fai falta recoller chave: o código aparece na túa reserva.",
            ),
        ),
        (
            -5,
            dict(
                category="event",
                title="Carreira popular do Samaín",
                body="O 31 ás 18:00, saída desde o pavillón. Inscrición gratuíta no mostrador ou na app.",
            ),
        ),
        (
            -3,
            dict(
                category="alert",
                title="Aviso por néboa na estrada de Bustelo",
                body="Pola mañá hai néboa densa na estrada de Bustelo. Achega con coidado ás pistas.",
                audience="parish",
                parish=f["padel"].parish if f.get("padel") else None,
                window_start=_at(-10, 0),
                window_end=_at(-3, 23),
            ),
        ),
        (
            -2,
            dict(
                category="activity_change",
                title="Ximnasia de mantemento: cambio de sala o xoves",
                body="Esta semana a sesión do xoves faise na sala 2 do pavillón.",
                audience="activity",
                activity=senior,
            ),
        ),
        (
            -1,
            dict(
                category="activity_change",
                title="Escola de fútbol: adestramento do venres suspendido",
                body="Polo torneo no campo, o venres non hai adestramento. Recupérase o luns á mesma hora.",
                audience="activity",
                activity=football,
            ),
        ),
        (
            -1,
            dict(
                category="news",
                title="Grazas por valorar as instalacións",
                body="Levamos máis de 600 valoracións «Que tal foi?». Co voso parecer cambiamos o horario do pádel.",
            ),
        ),
    ]
    for days, data in plan:
        if data.get("audience") == "parish" and not data.get("parish"):
            data["audience"] = "all"
        _send(vil, _at(days, 9 + (days % 3), 15), created_by=admin, **data)

    # Alerta amarela por vento con cancelación das reservas exteriores (franxa de mañá)
    start, end = _at(2, 9), _at(2, 14)
    outdoor_bookings(vil, start, end, rng)
    _send(
        vil,
        timezone.now() - dt.timedelta(hours=2),
        created_by=admin,
        category="alert",
        title="Alerta amarela por vento: pistas exteriores pechadas",
        body="Pasado mañá de 9:00 a 14:00 pechan as pistas descubertas. Cancelamos as reservas afectadas e devolvémosche o importe.",
        audience="outdoor",
        window_start=start,
        window_end=end,
        cancel_bookings=True,
    )
    # Horario de Nadal: programado (aínda non enviado)
    Notice.objects.create(
        municipality=vil,
        created_by=admin,
        category="schedule",
        title="Horario de Nadal",
        body="Do 24 de decembro ao 6 de xaneiro, todas as instalacións abren de 10:00 a 14:00. Os días 25 e 1, pechadas.",
        channels=["app", "email", "telegram", "channel"],
        publish_at=_at(5, 10),
    )

    pon_admin = User.objects.filter(
        memberships__municipality=pon, memberships__role=Role.ADMIN
    ).first()
    for days, data in [
        (
            -21,
            dict(
                category="event",
                title="Festa da Ribeira: actividades no campo",
                body="O sábado hai xogos populares no campo municipal. Pola tarde as reservas do campo quedan sen efecto.",
            ),
        ),
        (
            -9,
            dict(
                category="schedule",
                title="O polideportivo abre os domingos",
                body="Desde este mes, o polideportivo abre tamén os domingos de 10:00 a 14:00.",
            ),
        ),
        (
            -4,
            dict(
                category="closure",
                title="Corte de auga no polideportivo",
                body="O mércores de 8:00 a 12:00 non haberá duchas por un corte de auga.",
            ),
        ),
    ]:
        _send(pon, _at(days, 11), created_by=pon_admin, **data)
