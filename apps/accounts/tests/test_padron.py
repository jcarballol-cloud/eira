# SPDX-License-Identifier: EUPL-1.2
"""v4: padrón semiautomático (CSV → HMAC). Coincidencia exacta, sen coincidencia, formatos,
recarga, que o CSV non se garda e que o nome nunca se usa para casar."""

import datetime as dt

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts import padron
from apps.accounts.models import AppRequest, AuditLog, PadronEntry, PadronImport
from apps.integrations.models import DevMail
from apps.integrations.padron import CsvPadronAdapter

pytestmark = pytest.mark.django_db

CSV = b"dni_nie;data_nacemento\n12345678Z;14/05/1990\nX1234567L;1985-02-03\nnon-valido;01/01/2000\n"


def upload(muni, content=CSV, by=None):
    return padron.import_csv(muni, SimpleUploadedFile("padron.csv", content), by=by)


def ask(client, **over):
    data = {
        "name": "Ana",
        "surnames": "Souto Rial",
        "email": "ana@example.org",
        "id_number": "12345678Z",
        "birth_date": "1990-05-14",
        "resident": "on",
    }
    data.update(over)
    return client.post("/c/concello-a/app/solicitar/", data)


# ---------- normalización ----------
@pytest.mark.parametrize(
    "raw, norm, ok",
    [
        ("12345678Z", "12345678Z", True),
        ("12345678z", "12345678Z", True),
        (" 12.345.678-z ", "12345678Z", True),
        ("x1234567l", "X1234567L", True),
        ("1234567L", "01234567L", True),
        ("12345678A", "12345678A", False),  # letra de control errada
        ("ABC", "ABC", False),
    ],
)
def test_normalize_and_validate_id(raw, norm, ok):
    assert padron.normalize_id(raw) == norm and padron.valid_id(raw) is ok


@pytest.mark.parametrize(
    "raw", ["14/05/1990", "1990-05-14", "14-05-1990", "14.05.1990", "14/05/90"]
)
def test_date_formats(raw):
    assert padron.parse_date(raw) == dt.date(1990, 5, 14)


# ---------- importación ----------
def test_import_keeps_only_hmac_and_logs(muni_a, admin_a):
    batch = upload(muni_a, by=admin_a)
    assert (batch.count, batch.rejected, batch.imported_by) == (2, 1, admin_a)
    digests = list(PadronEntry.objects.values_list("digest", flat=True))
    assert len(digests) == 2 and all(len(d) == 64 for d in digests)
    assert AuditLog.objects.filter(action="padron.import").exists()


def test_original_csv_is_not_kept(muni_a, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    upload(muni_a)
    # nin ficheiro no disco…
    assert not any(tmp_path.rglob("*"))
    # …nin ningún dato do CSV en claro na base de datos
    rows = [str(v) for e in PadronEntry.objects.values() for v in e.values()]
    rows += [str(v) for e in PadronImport.objects.values() for v in e.values()]
    assert not any(x in r for r in rows for x in ("12345678", "1990", "X1234567"))
    assert not [f for f in PadronImport._meta.fields if f.get_internal_type() == "FileField"]


def test_reimport_replaces_previous(muni_a):
    upload(muni_a)
    assert padron.matches(muni_a, "12345678Z", "1990-05-14")
    upload(muni_a, b"dni_nie,data_nacemento\n00000001R,01/01/1970\n")  # outro separador
    assert not padron.matches(muni_a, "12345678Z", "1990-05-14")
    assert padron.matches(muni_a, "00000001R", dt.date(1970, 1, 1))
    assert PadronImport.objects.count() == 2 and PadronEntry.objects.count() == 1


def test_hmac_depends_on_municipality_and_secret(muni_a, muni_b, settings):
    a = padron.digest(muni_a, "12345678Z", "1990-05-14")
    assert a != padron.digest(muni_b, "12345678Z", "1990-05-14")
    settings.EIRA_PADRON_SECRET = "outro-segredo"
    assert a != padron.digest(muni_a, "12345678Z", "1990-05-14")


def test_template_download(client, muni_a, admin_a):
    client.force_login(admin_a)
    r = client.get("/c/concello-a/xestion/altas/padron/modelo.csv")
    assert r["Content-Type"].startswith("text/csv") and b"dni_nie;data_nacemento" in r.content
    # o modelo tal cal non engade ninguén (as liñas de exemplo van comentadas)
    assert upload(muni_a, r.content).count == 0


def test_upload_from_admin_page(client, muni_a, admin_a, citizen):
    client.force_login(citizen)
    assert client.get("/c/concello-a/xestion/altas/padron/").status_code in (302, 403)
    client.force_login(admin_a)
    r = client.post(
        "/c/concello-a/xestion/altas/padron/", {"file": SimpleUploadedFile("p.csv", CSV)}
    )
    assert r.status_code == 302 and PadronImport.objects.get().count == 2
    html = client.get("/c/concello-a/xestion/altas/padron/").content.decode()
    assert "Rexistro de cargas" in html and "12345678Z" not in html


# ---------- contraste na alta ----------
def test_exact_match_registers_instantly_and_mails_code(client, muni_a):
    upload(muni_a)
    ask(client)
    req = AppRequest.objects.get()
    assert req.padron_match and req.status == AppRequest.Status.SENT
    assert req.invitation.code in DevMail.objects.get(to="ana@example.org").body
    # minimización: resolta, xa non se garda o DNI nin a data
    assert req.id_number == "" and req.birth_date is None


def test_lowercase_and_spaces_in_id_still_match(client, muni_a):
    upload(muni_a)
    ask(client, id_number=" 12345678 z ")
    assert AppRequest.objects.get().padron_match


def test_no_match_goes_to_review_with_reason(client, muni_a):
    upload(muni_a)
    ask(client, birth_date="1990-05-15")  # un día de diferenza
    req = AppRequest.objects.get()
    assert not req.padron_match and req.status == AppRequest.Status.PENDING
    assert req.review_reason == "no_match" and req.review_reason_label
    assert req.id_number == "12345678Z"  # mentres está pendente, para que o concello revise


def test_without_padron_loaded_reason_is_no_padron(client, muni_a):
    ask(client)
    assert AppRequest.objects.get().review_reason == "no_padron"


def test_name_is_never_used_for_matching(muni_a):
    upload(muni_a)
    adapter = CsvPadronAdapter()
    # a interface nin sequera recibe o nome
    with pytest.raises(TypeError):
        adapter.check(muni_a, name="Ana", id_number="12345678Z", birth_date="1990-05-14")
    assert adapter.check(muni_a, id_number="12345678Z", birth_date="1990-05-14").found
    assert not adapter.check(muni_a, id_number="00000001R", birth_date="1990-05-14").found


def test_invalid_id_is_rejected_by_form(client, muni_a):
    upload(muni_a)
    r = ask(client, id_number="12345678A")
    assert r.status_code == 200 and not AppRequest.objects.exists()
    assert "Revisa o DNI/NIE" in r.content.decode()


def test_resolution_forgets_identity(client, muni_a, admin_a):
    upload(muni_a)
    ask(client, id_number="00000001R")
    req = AppRequest.objects.get()
    client.force_login(admin_a)
    client.post(f"/c/concello-a/xestion/altas/{req.pk}/resolver/", {"action": "approve"})
    req.refresh_from_db()
    assert req.status == AppRequest.Status.SENT and req.id_number == "" and req.birth_date is None
