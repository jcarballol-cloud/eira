# SPDX-License-Identifier: EUPL-1.2
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.incidents.models import Incident
from apps.maintenance.models import WorkOrder
from apps.maintenance.services import close_order
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db


def jpeg_with_gps():
    img = Image.new("RGB", (64, 48), "green")
    exif = Image.Exif()
    exif[0x010F] = "Fabricante"  # Make
    exif[0x8825] = {1: "N", 2: (42.0, 30.0, 0.0), 3: "W", 4: (8.0, 10.0, 0.0)}  # GPSInfo
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_report_with_photo_strips_exif(client, citizen, padel_a, admin_a):
    raw = jpeg_with_gps()
    assert Image.open(io.BytesIO(raw)).getexif()  # o orixinal ten EXIF
    client.force_login(citizen)
    r = client.post(
        "/c/concello-a/incidencias/nova/",
        {
            "facility": padel_a.pk,
            "category": "damage",
            "description": "Rede rota",
            "photo": SimpleUploadedFile("foto.jpg", raw, content_type="image/jpeg"),
        },
    )
    assert r.status_code == 302
    inc = Incident.objects.get()
    with inc.photo.open("rb") as fh:
        saved = Image.open(fh)
        assert not saved.getexif()
        assert "exif" not in saved.info
    assert Notification.objects.filter(user=admin_a).exists()  # o concello recibe o aviso


def test_rejects_big_or_fake_images(client, citizen, padel_a, settings):
    client.force_login(citizen)
    r = client.post(
        "/c/concello-a/incidencias/nova/",
        {
            "facility": padel_a.pk,
            "category": "damage",
            "description": "x",
            "photo": SimpleUploadedFile(
                "foto.jpg", b"isto non e unha imaxe", content_type="image/jpeg"
            ),
        },
    )
    assert r.status_code == 200 and not Incident.objects.exists()
    settings.EIRA_MAX_UPLOAD_BYTES = 100
    r = client.post(
        "/c/concello-a/incidencias/nova/",
        {
            "facility": padel_a.pk,
            "category": "damage",
            "description": "x",
            "photo": SimpleUploadedFile("foto.jpg", jpeg_with_gps(), content_type="image/jpeg"),
        },
    )
    assert "demasiado grande" in r.content.decode()


def test_cannot_report_facility_of_other_municipality(client, citizen, court_b, padel_a):
    client.force_login(citizen)
    client.post(
        "/c/concello-a/incidencias/nova/",
        {"facility": court_b.pk, "category": "damage", "description": "x"},
    )
    assert not Incident.objects.exists()


def test_full_cycle_notifies_reporter(client, citizen, padel_a, admin_a, operator_a):
    inc = Incident.objects.create(
        municipality=padel_a.municipality,
        facility=padel_a,
        reporter=citizen,
        description="Luz fundida",
    )
    client.force_login(admin_a)
    url = f"/c/concello-a/xestion/incidencias/{inc.pk}/"
    client.post(url, {"action": "validate"})
    inc.refresh_from_db()
    assert inc.status == "validated"
    client.post(
        url,
        {
            "action": "order",
            "title": "Cambiar lámpada",
            "assigned_to": operator_a.pk,
            "due_date": "2026-11-01",
        },
    )
    inc.refresh_from_db()
    order = WorkOrder.objects.get(incident=inc)
    assert inc.status == "work_order" and order.assigned_to == operator_a
    close_order(order, operator_a, "Lámpada cambiada")
    inc.refresh_from_db()
    assert inc.status == "resolved"
    titles = list(Notification.objects.filter(user=citizen).values_list("title", flat=True))
    assert len(titles) == 3 and any("Arranxado" in t for t in titles)


def test_reporter_sees_only_own_incidents(client, citizen, outsider, padel_a):
    inc = Incident.objects.create(
        municipality=padel_a.municipality, facility=padel_a, reporter=outsider, description="x"
    )
    client.force_login(citizen)
    assert client.get(f"/c/concello-a/incidencias/{inc.pk}/").status_code == 404


def test_incident_photos_are_private(client, citizen, outsider, padel_a, admin_a, admin_b):
    client.force_login(citizen)
    client.post(
        "/c/concello-a/incidencias/nova/",
        {"facility": padel_a.pk, "category": "damage", "description": "x",
         "photo": SimpleUploadedFile("f.jpg", jpeg_with_gps(), content_type="image/jpeg")},
    )
    url = Incident.objects.get().photo.url
    assert client.get(url).status_code == 200  # quen a enviou
    client.force_login(admin_a)
    assert client.get(url).status_code == 200  # persoal do concello
    for who in (outsider, admin_b):
        client.force_login(who)
        assert client.get(url).status_code == 404  # outras persoas e outros concellos
    client.logout()
    assert client.get(url).status_code == 404
