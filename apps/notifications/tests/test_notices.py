# SPDX-License-Identifier: EUPL-1.2
"""v4: avisos do concello. Segmentación, consentimento, preferencias, programación, cancelación
de reservas e vinculación do bot de Telegram."""

import datetime as dt
import json
from unittest import mock

import pytest
from django.utils import timezone

from apps.accounts.models import Membership, Role, User
from apps.activities.models import Activity, Enrollment, Group
from apps.bookings import services as booking_services
from apps.bookings.models import Booking
from apps.integrations.models import DevMail, OutboundMessage
from apps.notifications import notices
from apps.notifications.models import Notice, NoticePreference, Notification, TelegramLink
from conftest import next_slot

pytestmark = pytest.mark.django_db


def book(facility, user, start=None):
    return booking_services.create_booking(
        facility, start or next_slot(facility), user, rules_version=facility.current_rules()
    )


def neighbour(muni, email, consent=False):
    u = User.objects.create_user(email, display_name=email.split("@")[0])
    Membership.objects.create(user=u, municipality=muni, role=Role.CITIZEN)
    if consent:
        NoticePreference.objects.create(user=u, municipality=muni, comms_consent_at=timezone.now())
    return u


def notice(muni, **kw):
    data = {
        "category": "event",
        "title": "Festas",
        "body": "Programa das festas.",
        "channels": ["app", "email"],
    }
    data.update(kw)
    return Notice.objects.create(municipality=muni, **data)


# ---------- segmentación ----------
def test_audience_all_is_only_this_municipality(muni_a, muni_b, citizen):
    other = neighbour(muni_b, "outra@example.org")
    n = notice(muni_a, audience="all")
    people = set(notices.audience(n))
    assert citizen in people and other not in people


def test_audience_facility_only_bookers_in_window(muni_a, padel_a, gym_a, citizen):
    other = neighbour(muni_a, "ximnasio@example.org")
    b = book(padel_a, citizen)
    book(gym_a, other)
    n = notice(
        muni_a,
        category="closure",
        audience="facility",
        facility=padel_a,
        window_start=b.start - dt.timedelta(hours=1),
        window_end=b.end + dt.timedelta(hours=1),
    )
    assert set(notices.audience(n)) == {citizen}
    # fóra da franxa, ninguén
    n.window_start, n.window_end = b.end + dt.timedelta(hours=2), b.end + dt.timedelta(hours=3)
    assert not notices.audience(n).exists()


def test_audience_activity_only_enrolled(muni_a, citizen):
    other = neighbour(muni_a, "non-inscrita@example.org")
    act = Activity.objects.create(municipality=muni_a, name="Multideporte")
    g = Group.objects.create(
        municipality=muni_a,
        activity=act,
        name="G",
        min_age=0,
        max_age=110,
        places=10,
        fee_cents=0,
        weekdays="0",
        start_time=dt.time(17),
    )
    Enrollment.objects.create(municipality=muni_a, group=g, user=citizen, status="active")
    n = notice(muni_a, category="activity", audience="activity", activity=act)
    assert set(notices.audience(n)) == {citizen} and other not in notices.audience(n)


# ---------- consentimento e preferencias ----------
def test_informative_notice_is_not_sent_without_consent(muni_a, citizen):
    with_consent = neighbour(muni_a, "si@example.org", consent=True)
    notices.send(notice(muni_a, audience="all"))
    assert not Notification.objects.filter(user=citizen).exists()
    assert not DevMail.objects.filter(to=citizen.email).exists()
    assert Notification.objects.filter(user=with_consent, category="event").exists()
    assert DevMail.objects.filter(to=with_consent.email).count() == 1


def test_service_notice_reaches_affected_people_without_consent(muni_a, padel_a, citizen):
    b = book(padel_a, citizen)
    n = notice(
        muni_a,
        category="closure",
        audience="facility",
        facility=padel_a,
        window_start=b.start,
        window_end=b.end,
        cancel_bookings=True,
        title="Peche da pista",
    )
    notices.send(n)
    n.refresh_from_db()
    b.refresh_from_db()
    assert b.status == Booking.Status.CANCELLED and n.cancelled == 1
    assert Notification.objects.filter(user=citizen, notice=n).exists()
    assert n.recipients == 1


def test_preference_matrix_per_category_and_channel(muni_a):
    u = neighbour(muni_a, "prefs@example.org", consent=True)
    pref = NoticePreference.objects.get(user=u)
    pref.matrix = {"event": ["app"], "news": []}
    pref.save()
    notices.send(notice(muni_a, audience="all"))
    assert Notification.objects.filter(user=u, category="event").exists()
    assert not DevMail.objects.filter(to=u.email).exists()  # correo desactivado para festas
    notices.send(notice(muni_a, audience="all", category="news", title="Nova pista"))
    assert not Notification.objects.filter(user=u, category="news").exists()  # categoría silenciada


def test_service_notice_keeps_app_even_if_muted(muni_a, padel_a, citizen):
    NoticePreference.objects.create(user=citizen, municipality=muni_a, matrix={"closure": []})
    b = book(padel_a, citizen)
    n = notice(
        muni_a,
        category="closure",
        audience="facility",
        facility=padel_a,
        window_start=b.start,
        window_end=b.end,
    )
    assert notices.channels_for(citizen, n) == {"app"}


def test_preferences_view_saves_consent_and_matrix(client, muni_a, citizen):
    client.force_login(citizen)
    r = client.post(
        "/c/concello-a/avisos/preferencias/",
        {"consent": "1", "event:app": "1", "event:telegram": "1"},
    )
    assert r.status_code == 302
    pref = NoticePreference.objects.get(user=citizen)
    assert pref.comms_consent_at and pref.matrix["event"] == ["app", "telegram"]
    assert pref.matrix["closure"] == ["app"]  # servizo: a app non se pode quitar
    client.post("/c/concello-a/avisos/preferencias/", {})
    assert NoticePreference.objects.get(user=citizen).comms_consent_at is None


# ---------- programación ----------
def test_scheduled_notice_is_sent_once_when_due(muni_a):
    u = neighbour(muni_a, "prog@example.org", consent=True)
    when = timezone.now() + dt.timedelta(hours=2)
    n = notice(muni_a, audience="all", publish_at=when)
    assert notices.send_due() == []
    assert not Notification.objects.filter(user=u).exists()
    assert len(notices.send_due(now=when + dt.timedelta(minutes=1))) == 1
    assert len(notices.send_due(now=when + dt.timedelta(minutes=2))) == 0  # non se repite
    notices.send(n)  # idempotente
    assert Notification.objects.filter(user=u, notice=n).count() == 1


def test_compose_preview_and_schedule_from_admin(client, muni_a, admin_a):
    neighbour(muni_a, "a@example.org", consent=True)
    client.force_login(admin_a)
    data = {
        "category": "schedule",
        "title": "Horario de Nadal",
        "body": "Do 24 ao 6.",
        "audience": "all",
        "channels": ["app", "email"],
    }
    r = client.post("/c/concello-a/xestion/avisos/novo/", {**data, "action": "preview"})
    assert r.status_code == 200 and r.context["preview"]["estimate"]["people"] == 1
    assert "Asunto:" in r.content.decode()
    when = (timezone.localtime() + dt.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    r = client.post(
        "/c/concello-a/xestion/avisos/novo/", {**data, "publish_at": when, "action": "send"}
    )
    n = Notice.objects.get(title="Horario de Nadal")
    assert r.status_code == 302 and n.sent_at is None and not Notification.objects.exists()


def test_cancel_needs_window_and_affected_audience(client, muni_a, admin_a):
    client.force_login(admin_a)
    r = client.post(
        "/c/concello-a/xestion/avisos/novo/",
        {
            "category": "alert",
            "title": "Vento",
            "body": "Alerta",
            "audience": "all",
            "channels": ["app"],
            "cancel_bookings": "on",
            "action": "preview",
        },
    )
    assert r.context["form"].errors.get("cancel_bookings")


def test_only_municipality_admin_can_compose(client, muni_a, citizen):
    client.force_login(citizen)
    assert client.get("/c/concello-a/xestion/avisos/novo/").status_code in (302, 403)


# ---------- Telegram ----------
def test_bot_linking_with_single_use_code(muni_a, citizen):
    code = notices.new_link_code(citizen)
    reply = notices.handle_bot_message("12345", f"/start {code}")
    citizen.refresh_from_db()
    assert citizen.telegram_chat == "12345" and citizen.notify_telegram and "Listo" in reply
    # o código xa non vale para outro chat
    assert "non vale" in notices.handle_bot_message("999", f"/start {code}")
    assert OutboundMessage.objects.filter(channel="telegram", target="12345").exists()
    notices.handle_bot_message("12345", "/stop")
    citizen.refresh_from_db()
    assert citizen.telegram_chat == "" and not citizen.notify_telegram


def test_bot_code_expires(muni_a, citizen):
    code = notices.new_link_code(citizen)
    TelegramLink.objects.filter(code=code).update(created_at=timezone.now() - dt.timedelta(hours=1))
    assert notices.link_chat(code, "1") is None


def test_telegram_delivery_and_public_channel(muni_a):
    muni_a.telegram_channel = "@deportesconcelloa"
    muni_a.save()
    u = neighbour(muni_a, "tg@example.org", consent=True)
    notices.handle_bot_message("777", f"/start {notices.new_link_code(u)}")
    notices.send(notice(muni_a, audience="all", channels=["app", "telegram", "channel"]))
    assert any("Festas" in m.payload["text"] for m in OutboundMessage.objects.filter(target="777"))
    assert OutboundMessage.objects.filter(target="@deportesconcelloa").count() == 1


def test_webhook_requires_secret(client, citizen, settings):
    settings.EIRA_TELEGRAM_WEBHOOK_SECRET = ""
    assert (
        client.post("/telegram/webhook/x/", "{}", content_type="application/json").status_code
        == 404
    )
    settings.EIRA_TELEGRAM_WEBHOOK_SECRET = "s3"
    code = notices.new_link_code(citizen)
    update = {"message": {"chat": {"id": 4242}, "text": f"/start {code}"}}
    assert (
        client.post(
            "/telegram/webhook/mal/", json.dumps(update), content_type="application/json"
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/telegram/webhook/s3/", json.dumps(update), content_type="application/json"
        ).status_code
        == 200
    )
    citizen.refresh_from_db()
    assert citizen.telegram_chat == "4242"


def test_real_adapter_reads_token_from_settings_only(settings):
    from django.core.exceptions import ImproperlyConfigured

    from apps.integrations.telegram import BotApiTelegramAdapter

    settings.EIRA_TELEGRAM_TOKEN = ""
    with pytest.raises(ImproperlyConfigured):
        BotApiTelegramAdapter()
    settings.EIRA_TELEGRAM_TOKEN = "proba-non-real"
    resp = mock.MagicMock()
    resp.__enter__.return_value.read.return_value = b'{"ok": true}'
    with mock.patch("urllib.request.urlopen", return_value=resp) as urlopen:
        assert BotApiTelegramAdapter().send("@canle", "Ola") is True
    req = urlopen.call_args[0][0]
    assert req.full_url == "https://api.telegram.org/botproba-non-real/sendMessage"
    assert json.loads(req.data)["chat_id"] == "@canle"


# ---------- app ----------
def test_list_filters_by_category_and_shows_board(client, muni_a, citizen):
    sent = notice(muni_a, audience="all", title="Festas de San Roque")
    notices.send(sent)  # sen consentimento: non se lle envía…
    client.force_login(citizen)
    html = client.get("/c/concello-a/avisos/").content.decode()
    assert "Festas de San Roque" in html  # …pero aparece no taboleiro
    html = client.get("/c/concello-a/avisos/?categoria=closure").content.decode()
    assert "Festas de San Roque" not in html


def test_purge_applies_retention(muni_a, citizen):
    old = Notification.objects.create(user=citizen, municipality=muni_a, title="Vello")
    Notification.objects.filter(pk=old.pk).update(
        created_at=timezone.now() - dt.timedelta(days=400)
    )
    Notification.objects.create(user=citizen, municipality=muni_a, title="Novo")
    notices.new_link_code(citizen)
    TelegramLink.objects.update(created_at=timezone.now() - dt.timedelta(days=2))
    assert notices.purge() == 1
    assert list(Notification.objects.values_list("title", flat=True)) == ["Novo"]
    assert not TelegramLink.objects.exists()
