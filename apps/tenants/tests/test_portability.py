# SPDX-License-Identifier: EUPL-1.2
"""Exportación íntegra dun concello e importación (ida e volta)."""

import io
import zipfile

import pytest

from apps.access.models import LockDevice
from apps.bookings.models import Booking
from apps.bookings.services import create_booking, mark_paid
from apps.facilities.models import Facility, OpeningHours, RulesVersion, Tariff
from apps.incidents.models import Incident
from apps.maintenance.models import MaintenanceTask
from apps.tenants.portability import export_municipality, import_municipality
from conftest import next_slot

pytestmark = pytest.mark.django_db


def test_round_trip(padel_a, gym_a, citizen):
    b = create_booking(padel_a, next_slot(padel_a), citizen, rules_version=padel_a.current_rules())
    mark_paid(b, "FR1", b.price_cents)
    Incident.objects.create(
        municipality=padel_a.municipality, facility=padel_a, reporter=citizen, description="x"
    )
    raw = export_municipality(padel_a.municipality)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = zf.namelist()
    assert {
        "eira.json",
        "csv/reservas.csv",
        "ical/reservas.ics",
        "geo/instalacions.geojson",
    } <= set(names)

    copy = import_municipality(raw, slug="copia", name="Copia")
    src = padel_a.municipality
    for model in (Facility, Booking, Incident, LockDevice):
        assert (
            model.objects.filter(municipality=copy).count()
            == model.objects.filter(municipality=src).count()
        )
    for model in (OpeningHours, Tariff, RulesVersion):
        assert (
            model.objects.filter(facility__municipality=copy).count()
            == model.objects.filter(facility__municipality=src).count()
        )
    assert (
        MaintenanceTask.objects.filter(plan__municipality=copy).count()
        == MaintenanceTask.objects.filter(plan__municipality=src).count()
    )
    nb = Booking.objects.get(municipality=copy)
    assert nb.user == citizen and nb.start == b.start and nb.paid_cents == b.paid_cents
    assert nb.facility.municipality == copy and nb.rules_version.facility == nb.facility
    assert nb.reference != b.reference  # as referencias únicas rexenéranse se chocan
    # As pechaduras conservan o segredo: os códigos seguen funcionando tras a migración
    new_padel = Facility.objects.get(municipality=copy, name=padel_a.name)
    assert new_padel.lock.secret == padel_a.lock.secret


def test_round_trip_into_empty_instance(padel_a, citizen):
    """Simula outra instancia: borra o concello orixinal e importa."""
    create_booking(padel_a, next_slot(padel_a), citizen, rules_version=padel_a.current_rules())
    raw = export_municipality(padel_a.municipality)
    ref = Booking.objects.get().reference
    Booking.objects.all().delete()
    padel_a.municipality.delete()
    imported = import_municipality(raw)
    assert imported.slug == "concello-a"
    assert Booking.objects.get(municipality=imported).reference == ref


def test_export_requires_admin(client, citizen, admin_a, padel_a):
    client.force_login(citizen)
    assert client.get("/c/concello-a/xestion/portabilidade/exportar.zip").status_code == 403
    client.force_login(admin_a)
    r = client.get("/c/concello-a/xestion/portabilidade/exportar.zip")
    assert r.status_code == 200 and r["Content-Type"] == "application/zip"
