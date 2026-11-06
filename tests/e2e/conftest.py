# SPDX-License-Identifier: EUPL-1.2
"""E2E: servidor en vivo con os datos de demostración e navegador Chromium (Playwright)."""

import os

import pytest
from django.core.management import call_command

# Playwright síncrono usa un bucle asyncio no mesmo fío que a proba.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

MOBILE = {"width": 390, "height": 844}
DESKTOP = {"width": 1280, "height": 900}
TABLET = {"width": 820, "height": 1180}  # tableta vertical (iPad Air)


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("seed_demo", verbosity=0)


@pytest.fixture(autouse=True)
def _clean_state():  # sobrescribe o autouse do conftest raíz (non usa tmp media nin settings)
    yield


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def base(live_server):
    from apps.tenants.models import Municipality

    # live_server baleira a BD tras cada proba (transaccional): volve cargar a demo se fai falla
    if not Municipality.objects.exists():
        call_command("seed_demo", verbosity=0)
    return live_server.url


@pytest.fixture
def new_page(browser, base):
    contexts = []

    def make(viewport=DESKTOP, persona=None, **kw):
        ctx = browser.new_context(viewport=viewport, locale="gl-ES", **kw)
        contexts.append(ctx)
        page = ctx.new_page()
        if persona:
            login_as(page, base, persona)
        return page

    yield make
    for ctx in contexts:
        ctx.close()


def demo_url(base, email):
    """Portada da demo no paso onde está o botón dese perfil (paso 2 do seu concello)."""
    from apps.integrations.demo import BY_EMAIL

    tenant = BY_EMAIL[email]["tenant"]
    return f"{base}/?concello={tenant}" if tenant else f"{base}/"


def login_as(page, base, email):
    page.goto(demo_url(base, email))
    page.locator(f"form:has(input[value='{email}']) button").click()
    page.wait_for_load_state()


def uxia_waitlist_entry():
    """Uxía agardando unha franxa ocupada. A demo só a crea se mañá hai unha reserva doutra persoa
    no pádel, e iso depende da data e da hora: se falta, créase aquí para que a proba non dependa."""
    from django.utils import timezone

    from apps.accounts.models import User
    from apps.bookings.models import Booking, WaitlistEntry
    from apps.bookings.services import slot_starts
    from apps.facilities.models import Facility

    uxia = User.objects.get(email="uxia@demo.eira.example")
    entry = WaitlistEntry.objects.filter(user=uxia, status="waiting").first()
    if entry:
        return entry
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    other = User.objects.filter(email__startswith="vecinanza").order_by("email").first()
    for days in range(1, 8):
        day = timezone.localdate() + timezone.timedelta(days=days)
        for start in slot_starts(padel, day):
            active = Booking.objects.filter(
                facility=padel, start=start, status__in=["confirmed", "used"]
            )
            if active.filter(user=uxia).exists():
                continue
            booking = active.first() or Booking.objects.create(
                municipality=padel.municipality,
                facility=padel,
                user=other,
                start=start,
                end=start + timezone.timedelta(minutes=padel.slot_minutes),
                status=Booking.Status.CONFIRMED,
            )
            return WaitlistEntry.objects.create(
                municipality=padel.municipality,
                facility=padel,
                start=booking.start,
                end=booking.end,
                user=uxia,
            )
    raise AssertionError("Non hai franxas de pádel nos próximos 7 días")


def released_booking_id():
    """Reserva orixinal dunha franxa liberada. A demo só crea o exemplo se hai 3 días houbo un uso
    do pádel, e iso depende da data e da hora: se falta, créase aquí."""
    from django.utils import timezone

    from apps.bookings.models import Booking, SlotRelease
    from apps.facilities.models import Facility

    release = SlotRelease.objects.filter(
        municipality__slug="vilardeiras", released_booking__isnull=False
    ).first()
    if release:
        return release.released_booking_id
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    used = Booking.objects.filter(facility=padel, user__isnull=False, end__lte=timezone.now())
    taken = used.order_by("-start").first()
    original = Booking.objects.create(
        municipality=padel.municipality,
        facility=padel,
        user=taken.user,
        start=taken.start,
        end=taken.end,
        status=Booking.Status.CANCELLED,
    )
    return SlotRelease.objects.create(
        municipality=padel.municipality,
        facility=padel,
        start=taken.start,
        end=taken.end,
        released_booking=original,
        reason=SlotRelease.Reason.CANCELLED,
        taken_booking=taken,
        closed_at=taken.start,
    ).released_booking_id
