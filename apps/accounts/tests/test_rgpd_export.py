# SPDX-License-Identifier: EUPL-1.2
"""Auditoría RXPD (14/11/2026): a descarga dos datos propios (art. 15) inclúe tamén carné,
abonos, bonos, valoracións, partidas abertas e preferencias de avisos."""

import datetime as dt

from django.utils import timezone

from apps.accounts.views import export_user_data
from apps.bookings.models import Booking, OpenGame, Rating


def test_export_has_every_kind_of_personal_data(citizen, padel_a, muni_a):
    from apps.members.models import MemberCard
    from apps.notifications.models import NoticePreference

    start = timezone.now() - dt.timedelta(days=2)
    b = Booking.objects.create(
        municipality=muni_a,
        facility=padel_a,
        user=citizen,
        start=start,
        end=start + dt.timedelta(hours=1),
        status=Booking.Status.CONFIRMED,
        rules_version=padel_a.current_rules(),
        rules_accepted_at=start,
    )
    Rating.objects.create(
        municipality=muni_a, booking=b, facility=padel_a, score="good", comment="Ben"
    )
    OpenGame.objects.create(municipality=muni_a, booking=b, consent_at=start, message="Dobres")
    MemberCard.objects.create(municipality=muni_a, user=citizen, number="A-0001")
    NoticePreference.objects.create(user=citizen, municipality=muni_a, comms_consent_at=start)

    data = export_user_data(citizen)
    assert data["ratings"][0]["comment"] == "Ben"
    assert data["open_games"][0]["message"] == "Dobres"
    assert data["member_cards"][0]["number"] == "A-0001"
    assert data["notice_preferences"][0]["informative_consent_at"]
    for key in ("sports_passes", "vouchers", "game_joins", "preferences"):
        assert key in data


def test_export_never_includes_other_people(citizen, outsider, padel_a, muni_a):
    from apps.members.models import MemberCard

    MemberCard.objects.create(municipality=muni_a, user=outsider, number="B-0002")
    assert export_user_data(citizen)["member_cards"] == []
