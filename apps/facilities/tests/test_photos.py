# SPDX-License-Identifier: EUPL-1.2
"""v2 F4: fotos libres de referencia, créditos e fotos propias do concello en WebP sen metadatos."""

import io
import re

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.facilities.photos import ALT, SIZES, STOCK_DIR, credits, photo_for

pytestmark = pytest.mark.django_db
LICENSES = re.compile(r"^(CC0( 1\.0)?|CC BY [0-9.]+|CC BY-SA [0-9.]+|Public domain)$")


def test_every_stock_photo_has_free_license_credit_alt_and_files():
    items = credits()
    assert len(items) >= 12
    kinds = {c["kind"] for c in items}
    assert kinds == {"padel", "pool", "gym", "sports_hall", "grass_field", "outdoor_court"}
    for c in items:
        assert LICENSES.match(c["license"]), c
        assert c["source"].startswith("https://commons.wikimedia.org/wiki/File:")
        assert c["author"] and ALT.get(c["file"])
        assert (STOCK_DIR / f"{c['file']}-480.webp").exists()
        with Image.open(STOCK_DIR / f"{c['file']}-960.webp") as im:
            assert im.width == 960 and not im.info.get("exif")


def test_listing_uses_lazy_responsive_stock_photo_with_alt(client, padel_a):
    html = client.get("/c/concello-a/").content.decode()
    img = re.search(r'<img src="[^"]*/img/fotos/padel-\d-960\.webp"[^>]*>', html).group(0)
    assert 'loading="lazy"' in img and "480w" in img and 'alt="' in img and 'alt=""' not in img


def test_detail_credits_the_author_and_license(client, padel_a):
    html = client.get(f"/c/concello-a/instalacions/{padel_a.pk}/").content.decode()
    item = photo_for(padel_a)["credit"]
    assert item["license"] in html and "Wikimedia Commons" in html


def test_credits_page_lists_all(client, db):
    html = client.get("/creditos/").content.decode()
    for c in credits():
        assert c["source"] in html


def _jpeg_with_exif():
    im = Image.new("RGB", (1600, 1100), (40, 120, 90))
    exif = Image.Exif()
    exif[0x010F] = "Fabricante"  # Make
    exif[0x0131] = "Teléfono de proba"  # Software
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def test_uploaded_photo_replaces_stock_in_webp_sizes_without_metadata(client, admin_a, padel_a):
    client.force_login(admin_a)
    url = f"/c/concello-a/xestion/instalacions/{padel_a.pk}/"
    data = {k: v for k, v in client.get(url).context["form"].initial.items() if v is not None}
    data.update(
        {
            "photo": SimpleUploadedFile("pista.jpg", _jpeg_with_exif(), content_type="image/jpeg"),
            "photo_alt": "Pista de pádel do concello",
            "parish": padel_a.parish_id or "",
        }
    )
    data = {k: v for k, v in data.items() if v is not False}
    r = client.post(url, data)
    assert r.status_code == 302, r.context["form"].errors if r.context else r
    padel_a.refresh_from_db()
    base = padel_a.photo.name.rsplit(".", 1)[0]
    for size in SIZES:
        name = f"{base}-{size}.webp"
        assert default_storage.exists(name)
        with default_storage.open(name) as fh, Image.open(fh) as im:
            assert not im.info.get("exif") and not dict(im.getexif())
    with padel_a.photo.open("rb") as fh, Image.open(fh) as im:
        assert im.getexif().get(0x010F) is None
    p = photo_for(padel_a)
    assert (
        p["credit"] is None and p["alt"] == "Pista de pádel do concello" and "1440w" in p["srcset"]
    )
