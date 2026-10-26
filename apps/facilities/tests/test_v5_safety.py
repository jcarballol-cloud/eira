# SPDX-License-Identifier: EUPL-1.2
"""v5 · B (ficha de seguridade e cartel da porta) e H (revisión de seguridade inicial)."""

import datetime as dt
import zlib

import pytest
from django.utils import timezone

from apps.bookings.pdf import _esc
from apps.facilities.poster import build_poster, text_width, wrap
from apps.maintenance.models import WorkOrder
from apps.maintenance.safety import SAFETY_CHECKLIST, create_safety_review

pytestmark = pytest.mark.django_db
C = "/c/concello-a"


def test_equipment_protocol_and_last_supervision_on_facility_page(client, padel_a, muni_a):
    padel_a.equipment = "2 balóns\n1 rede de recambio\nbotiquín"
    padel_a.accident_protocol = "Chama ao 112 e avisa ao concello."
    padel_a.aed_location = "Recepción do pavillón (50 m)"
    padel_a.save()
    assert padel_a.equipment_items() == [
        {"qty": 2, "name": "balóns"},
        {"qty": 1, "name": "rede de recambio"},
        {"qty": None, "name": "botiquín"},
    ]
    assert padel_a.last_supervision() is None
    closed = timezone.now() - dt.timedelta(days=4)
    WorkOrder.objects.create(
        municipality=muni_a,
        facility=padel_a,
        title="Revisar",
        due_date=timezone.localdate(),
        status="done",
        closed_at=closed,
    )
    WorkOrder.objects.create(
        municipality=muni_a,
        facility=padel_a,
        title="Aberta",
        due_date=timezone.localdate(),
        status="open",
    )
    assert padel_a.last_supervision() == closed
    html = client.get(f"{C}/instalacions/{padel_a.pk}/").content.decode()
    for text in (
        "2 balóns",
        "rede de recambio",
        "Chama ao 112",
        "Recepción do pavillón",
        'href="tel:112"',
    ):
        assert text in html
    assert "Última supervisión" in html and timezone.localtime(closed).strftime("%d/%m/%Y") in html


def _content(pdf):
    start = pdf.index(b"stream\n", pdf.index(b"/FlateDecode")) + 7
    end = pdf.index(b"\nendstream", start)
    return zlib.decompress(pdf[start:end]).decode("latin-1")


def test_poster_pdf_is_tagged_and_has_everything(client, admin_a, padel_a, muni_a):
    muni_a.contact_phone = "982 000 000"
    muni_a.save()
    padel_a.aed_location = "Recepción"
    padel_a.save()
    client.force_login(admin_a)
    r = client.get(f"{C}/xestion/instalacions/{padel_a.pk}/cartel.pdf")
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf"
    pdf = r.content
    for marker in (
        b"/MarkInfo << /Marked true >>",
        b"/StructTreeRoot",
        b"/Lang (gl-ES)",
        b"/Figure",
        b"/Alt (",
        b"/H1",
        b"/DisplayDocTitle true",
        b"/Artifact",
    ):
        assert marker in pdf or marker in _content(pdf).encode("latin-1"), marker
    text = _content(pdf)
    for needle in (
        padel_a.name,
        "112",
        "982 000 000",
        "DEA",
        "Normas de uso",
        "En caso de accidente",
    ):
        assert _esc(needle) in text, needle
    # Plantilla do concello (sen instalación) co escudo
    r = client.get(f"{C}/xestion/instalacions/cartel-modelo.pdf")
    assert r.status_code == 200 and b"/Figure" in r.content and b"Escudo" in r.content


def test_poster_pdf_builder_wraps_long_text(padel_a):
    lines = wrap("palabra " * 60, 12, 200)
    assert all(text_width(line, 12) <= 200 for line in lines)
    pdf = build_poster(padel_a.municipality, padel_a, "https://exemplo.gal/c/x/")
    assert pdf.startswith(b"%PDF-1.7") and pdf.rstrip().endswith(b"%%EOF")


def test_poster_requires_staff(client, citizen, padel_a):
    client.force_login(citizen)
    assert client.get(f"{C}/xestion/instalacions/{padel_a.pk}/cartel.pdf").status_code == 403


def test_safety_review_template_and_reviewed_badge(client, admin_a, padel_a, operator_a):
    client.force_login(admin_a)
    r = client.post(f"{C}/xestion/instalacions/{padel_a.pk}/revision-seguridade/")
    order = WorkOrder.objects.get(facility=padel_a, kind="safety_review")
    assert r.status_code == 302
    assert order.title.startswith("Revisión de seguridade inicial Eira")
    labels = [i["label"] for i in order.checklist_state]
    assert len(labels) == len(SAFETY_CHECKLIST) == 10
    for word in (
        "Pavimento",
        "porterías",
        "Iluminación",
        "Valado",
        "Sinalización",
        "Botiquín",
        "DEA",
        "evacuación",
        "Accesibilidade",
        "Protocolo",
    ):
        assert any(word.lower() in label.lower() for label in labels), word
    # Mentres non se pecha, a ficha non di «Revisada»
    assert "Revisada o" not in client.get(f"{C}/instalacions/{padel_a.pk}/").content.decode()
    order.status, order.closed_at = WorkOrder.Status.DONE, timezone.now()
    order.save()
    html = client.get(f"{C}/instalacions/{padel_a.pk}/").content.decode()
    assert f"Revisada o {timezone.localdate():%d/%m/%Y}" in html
    # Non se crea outra se xa hai unha aberta
    again = create_safety_review(padel_a, by=admin_a)
    assert WorkOrder.objects.filter(facility=padel_a, kind="safety_review").count() == 2
    assert again.status == WorkOrder.Status.OPEN
    assert create_safety_review(padel_a, by=admin_a) == again
