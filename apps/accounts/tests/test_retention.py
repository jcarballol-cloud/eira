# SPDX-License-Identifier: EUPL-1.2
"""Auditoría RXPD (14/11/2026): prazos de conservación con purga automática, supresión da conta
sen textos libres e aviso nos campos de texto libre."""

import datetime as dt
import io

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.utils import timezone

from apps.accounts.freetext import NO_SENSITIVE
from apps.accounts.models import AuditLog, LoginCode, ResidencyInvitation, User
from apps.accounts.retention import DEFAULTS, purge_all
from apps.bookings.models import Booking, GameReport, OpenGame, Rating

OLD = timezone.now() - dt.timedelta(days=30 * 25)


def booking(facility, user, start, **extra):
    return Booking.objects.create(
        municipality=facility.municipality,
        facility=facility,
        user=user,
        start=start,
        end=start + dt.timedelta(hours=1),
        status=Booking.Status.CONFIRMED,
        rules_version=facility.current_rules(),
        rules_accepted_at=start,
        **extra,
    )


TEXTS = {
    "holder_name": "Persoa",
    "holder_phone": "600000000",
    "participant_names": "Ana\nXoán",
    "start_state_notes": "Había auga no chan",
    "close_notes": "Todo ben",
    "cancel_reason": "Gripe",
}


def test_old_bookings_are_anonymised_and_recent_ones_kept(padel_a, citizen):
    old = booking(padel_a, citizen, OLD, **TEXTS)
    recent = booking(padel_a, citizen, timezone.now() - dt.timedelta(days=30), **TEXTS)
    OpenGame.objects.create(
        municipality=padel_a.municipality, booking=old, consent_at=OLD, message="Buscamos xente"
    )
    purge_all()
    old.refresh_from_db()
    recent.refresh_from_db()
    assert old.user is None and all(getattr(old, k) == "" for k in TEXTS)
    assert old.price_cents == recent.price_cents  # o importe e a data quedan (contabilidade)
    assert not OpenGame.objects.filter(booking=old).exists()
    assert recent.user == citizen and recent.participant_names == TEXTS["participant_names"]


def test_short_lived_records_are_deleted(padel_a, citizen, muni_a):
    from apps.access.models import AccessEvent
    from apps.maintenance.models import CleaningLog

    ev = AccessEvent.objects.create(
        municipality=muni_a, facility=padel_a, user=citizen, kind=AccessEvent.Kind.values[0]
    )
    AccessEvent.objects.filter(pk=ev.pk).update(at=OLD)
    keep = AccessEvent.objects.create(
        municipality=muni_a, facility=padel_a, user=citizen, kind=AccessEvent.Kind.values[0]
    )
    CleaningLog.objects.create(municipality=muni_a, facility=padel_a, user=citizen, done_at=OLD)
    game = OpenGame.objects.create(
        municipality=muni_a,
        booking=booking(padel_a, citizen, timezone.now() + dt.timedelta(days=1)),
        consent_at=timezone.now(),
    )
    rep = GameReport.objects.create(game=game, user=citizen, reason=GameReport.Reason.FAKE)
    GameReport.objects.filter(pk=rep.pk).update(created_at=timezone.now() - dt.timedelta(days=400))
    LoginCode.issue(citizen.email)
    LoginCode.objects.update(expires_at=timezone.now() - dt.timedelta(days=2))
    inv = ResidencyInvitation.issue(muni_a, email="alguen@example.org", days=1)
    ResidencyInvitation.objects.filter(pk=inv.pk).update(
        expires_at=timezone.now() - dt.timedelta(days=40)
    )
    s = SessionStore()
    s["x"] = 1
    s.create()
    Session.objects.filter(pk=s.session_key).update(expire_date=timezone.now() - dt.timedelta(1))

    done = purge_all()
    assert list(AccessEvent.objects.all()) == [keep]
    assert not CleaningLog.objects.exists() and not GameReport.objects.exists()
    assert not LoginCode.objects.exists() and not ResidencyInvitation.objects.exists()
    assert not Session.objects.filter(pk=s.session_key).exists()
    assert done["access_events"] == 1 and done["cleaning"] == 1 and done["game_reports"] == 1


def test_used_invitations_and_valid_codes_are_kept(muni_a, citizen):
    inv = ResidencyInvitation.issue(muni_a, email="alguen@example.org", days=1)
    ResidencyInvitation.objects.filter(pk=inv.pk).update(
        expires_at=timezone.now() - dt.timedelta(days=40), used_at=timezone.now()
    )
    LoginCode.issue(citizen.email)
    purge_all()
    assert ResidencyInvitation.objects.filter(pk=inv.pk).exists()
    assert LoginCode.objects.count() == 1


def test_comments_and_reporters_lose_the_person(padel_a, citizen, muni_a):
    from apps.incidents.models import Incident

    b = booking(padel_a, citizen, timezone.now() - dt.timedelta(days=3))
    r = Rating.objects.create(
        municipality=muni_a, booking=b, facility=padel_a, score="bad", comment="Sucio"
    )
    Rating.objects.filter(pk=r.pk).update(created_at=OLD)
    inc = Incident.objects.create(
        municipality=muni_a,
        facility=padel_a,
        reporter=citizen,
        category="damage",
        description="Rede rota",
        status=Incident.Status.RESOLVED,
        resolved_at=OLD,
    )
    open_inc = Incident.objects.create(
        municipality=muni_a, facility=padel_a, reporter=citizen, category="damage", description="x"
    )
    purge_all()
    r.refresh_from_db()
    inc.refresh_from_db()
    open_inc.refresh_from_db()
    assert r.comment == "" and r.score == "bad"  # a valoración segue contando, sen texto
    assert inc.reporter is None and inc.description == "Rede rota"
    assert open_inc.reporter == citizen  # as abertas non se tocan


def test_survey_answers_lose_person_and_comment(muni_a, citizen):
    from apps.surveys.models import Survey, SurveyResponse

    today = timezone.localdate()
    survey = Survey.objects.create(
        municipality=muni_a, year=today.year - 3, opens_on=today, closes_on=today
    )
    a = SurveyResponse.objects.create(survey=survey, user=citizen, nps=9, comment="Ben")
    SurveyResponse.objects.filter(pk=a.pk).update(created_at=OLD)
    purge_all()
    a.refresh_from_db()
    assert a.user is None and a.comment == "" and a.nps == 9


def test_purge_is_audited_once_and_idempotent(padel_a, citizen):
    booking(padel_a, citizen, OLD, **TEXTS)
    first = purge_all()
    entry = AuditLog.objects.get(action="retention.purge")
    assert entry.detail["bookings"] == first["bookings"] == 1
    second = purge_all()
    assert not any(second.values())
    assert AuditLog.objects.filter(action="retention.purge").count() == 1


def test_retention_can_be_changed_per_installation(settings, padel_a, citizen):
    b = booking(padel_a, citizen, timezone.now() - dt.timedelta(days=100), **TEXTS)
    purge_all()
    b.refresh_from_db()
    assert b.user == citizen
    settings.EIRA_RETENTION = {"bookings": 3}
    purge_all()
    b.refresh_from_db()
    assert b.user is None


def test_every_rule_has_a_documented_term():
    from pathlib import Path

    from django.conf import settings as dj

    doc = (Path(dj.BASE_DIR) / "docs/rxpd/paquete/05-conservacion.md").read_text(encoding="utf-8")
    for key in DEFAULTS:
        assert f"`{key}`" in doc, key


def test_maintenance_command_runs_the_purge(padel_a, citizen):
    from django.core.management import call_command

    b = booking(padel_a, citizen, OLD, **TEXTS)
    out = io.StringIO()
    call_command("booking_maintenance", stdout=out)
    assert "Conservación:" in out.getvalue()
    b.refresh_from_db()
    assert b.user is None


# Supresión da conta


def test_account_deletion_also_clears_free_text_of_bookings(padel_a, citizen):
    from apps.accounts.views import delete_user

    b = booking(padel_a, citizen, timezone.now() - dt.timedelta(days=3), **TEXTS)
    delete_user(citizen)
    b.refresh_from_db()
    assert b.user is None and all(getattr(b, k) == "" for k in TEXTS)
    assert not User.objects.filter(pk=citizen.pk).exists()


# Aviso nos textos libres


@pytest.mark.parametrize(
    "form_path,field",
    [
        ("apps.bookings.views.ChecklistForm", "notes"),
        ("apps.bookings.views.StartStateForm", "notes"),
        ("apps.bookings.ratings.RatingForm", "comment"),
        ("apps.bookings.opengames_views.PublishForm", "message"),
        ("apps.incidents.views.IncidentForm", "description"),
        ("apps.maintenance.views.CloseForm", "closing_notes"),
        ("apps.maintenance.cleaning_views.ZoneLogForm", "notes"),
        ("apps.surveys.views.AnswerForm", "comment"),
    ],
)
def test_free_text_fields_warn_against_health_data(db, form_path, field):
    import importlib

    module, name = form_path.rsplit(".", 1)
    form_class = getattr(importlib.import_module(module), name)
    fields = getattr(form_class, "base_fields", {})
    assert str(NO_SENSITIVE) in str(fields[field].help_text)


def test_hand_written_textareas_carry_the_warning():
    from pathlib import Path

    from django.conf import settings as dj

    for name in (
        "maintenance/cleaning_zone.html",
        "maintenance/order.html",
        "manage/incident_detail.html",
    ):
        text = (Path(dj.BASE_DIR) / "templates" / name).read_text(encoding="utf-8")
        assert "Non escribas datos de saúde nin datos persoais doutras persoas." in text, name
