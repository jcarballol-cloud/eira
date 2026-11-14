# SPDX-License-Identifier: EUPL-1.2
"""Auditoría RXPD (14/11/2026): «Protección de datos: primeiros pasos» para a administración e o
DPD. Marcar garda data e persoa e queda no rexistro de auditoría."""

import re

import pytest
from django.utils import translation

from apps.accounts.models import AuditLog, Membership, PrivacyStep, Role, User
from apps.accounts.privacy_steps import DOCS, PACKAGE, STEPS

C = "/c/concello-a"
URL = f"{C}/xestion/privacidade/primeiros-pasos/"


@pytest.fixture
def dpo_a(muni_a):
    u = User.objects.create_user("dpd-a@example.org")
    Membership.objects.create(user=u, municipality=muni_a, role=Role.DPO)
    return u


def test_seven_steps_each_linked_to_a_document_or_screen():
    assert [s.key for s in STEPS] == [
        "dpo",
        "legal",
        "rat",
        "dpia",
        "processor",
        "retention",
        "twofa",
    ]
    for s in STEPS:
        assert s.doc or s.screen, s.key
        if s.doc:
            assert (PACKAGE / DOCS[s.doc][0]).exists(), s.doc


def test_every_package_document_exists_in_both_languages():
    for gl, es, _title in DOCS.values():
        for name in (gl, es):
            text = (PACKAGE / name).read_text(encoding="utf-8")
            assert "MODELO DE EXEMPLO" in text or "MODELO DE EJEMPLO" in text, name


def test_admin_and_dpo_see_it_others_do_not(client, admin_a, dpo_a, citizen, operator_a):
    for user in (admin_a, dpo_a):
        client.force_login(user)
        html = client.get(URL).content.decode()
        assert "0 de 7 pasos feitos" in html
    for user in (citizen, operator_a):
        client.force_login(user)
        assert client.get(URL).status_code == 403


def test_mark_done_keeps_date_person_and_audit(client, admin_a, muni_a):
    client.force_login(admin_a)
    resp = client.post(URL, {"step": "retention", "action": "done"})
    assert resp.status_code == 302 and resp["Location"].endswith("#paso-retention")
    step = PrivacyStep.objects.get(municipality=muni_a, key="retention")
    assert step.done_by == admin_a and step.state == "done"
    entry = AuditLog.objects.get(action="privacy.step_done")
    assert entry.detail["step"] == "retention" and entry.actor == admin_a
    html = client.get(URL).content.decode()
    assert "1 de 7 pasos feitos" in html and "admin-a@example.org" in html
    # Desmarcar tamén queda rexistrado
    client.post(URL, {"step": "retention", "action": "undo"})
    assert not PrivacyStep.objects.filter(key="retention").exists()
    assert AuditLog.objects.filter(action="privacy.step_undo").count() == 1


def test_dpia_needs_the_review_date(client, dpo_a, muni_a):
    client.force_login(dpo_a)
    client.post(URL, {"step": "dpia", "action": "done"})
    assert not PrivacyStep.objects.filter(key="dpia").exists()
    client.post(URL, {"step": "dpia", "action": "done", "reviewed_on": "2026-11-10"})
    step = PrivacyStep.objects.get(key="dpia")
    assert str(step.reviewed_on) == "2026-11-10"
    assert AuditLog.objects.get(action="privacy.step_done").detail["reviewed_on"] == "2026-11-10"


def test_processor_contract_can_be_not_applicable_others_cannot(client, admin_a, muni_a):
    client.force_login(admin_a)
    client.post(URL, {"step": "processor", "action": "na"})
    assert PrivacyStep.objects.get(key="processor").state == "na"
    assert client.post(URL, {"step": "rat", "action": "na"}).status_code == 404
    assert client.post(URL, {"step": "nope", "action": "done"}).status_code == 404


def test_dpo_and_2fa_steps_follow_the_real_settings(client, admin_a, muni_a):
    client.force_login(admin_a)
    muni_a.dpo_contact = ""
    muni_a.require_2fa_admin = False
    muni_a.save()
    html = client.get(URL).content.decode()
    assert "Falta o contacto do DPD" in html and "Aínda non está activado" in html
    assert len(re.findall(r'value="done" disabled', html)) == 2
    client.post(URL, {"step": "dpo", "action": "done"})
    client.post(URL, {"step": "twofa", "action": "done"})
    assert not PrivacyStep.objects.exists()
    muni_a.dpo_contact = "dpd@concello.example"
    muni_a.save()
    client.post(URL, {"step": "dpo", "action": "done"})
    assert PrivacyStep.objects.filter(key="dpo").exists()
    # Co dobre factor obrigatorio, a propia administración ten que entrar con el antes de marcar
    # nada (`test_twofactor.py`); aquí abonda con ver que o paso deixa de estar bloqueado.
    from apps.accounts.privacy_steps import BY_KEY, blocked

    muni_a.require_2fa_admin = True
    assert not blocked(BY_KEY["twofa"], muni_a)


def test_documents_render_and_download_is_audited(client, admin_a):
    client.force_login(admin_a)
    html = client.get(f"{C}/xestion/privacidade/documentos/rexistro/").content.decode()
    assert "Rexistro de actividades de tratamento" in html and "MODELO DE EXEMPLO" in html
    resp = client.get(f"{C}/xestion/privacidade/documentos/rexistro/?descargar=1")
    assert resp["Content-Disposition"] == 'attachment; filename="eira-01-rexistro-actividades.md"'
    assert AuditLog.objects.filter(action="export.download").exists()
    assert client.get(f"{C}/xestion/privacidade/documentos/../settings/").status_code == 404


def test_documents_in_spanish(client, admin_a):
    client.force_login(admin_a)
    with translation.override("es"):
        html = client.get(
            f"{C}/xestion/privacidade/documentos/minimizacion/", HTTP_ACCEPT_LANGUAGE="es"
        ).content.decode()
    assert "MODELO DE EJEMPLO" in html


def test_other_municipality_does_not_see_the_steps(client, admin_b, admin_a, muni_a):
    client.force_login(admin_a)
    client.post(URL, {"step": "retention", "action": "done"})
    client.force_login(admin_b)
    assert client.get(URL).status_code == 403
    html = client.get("/c/concello-b/xestion/privacidade/primeiros-pasos/").content.decode()
    assert "0 de 7 pasos feitos" in html


def test_region_cannot_mark_even_with_support_access(client, muni_a):
    from apps.accounts.models import RegionMembership

    region_user = User.objects.create_user("deputacion@example.org")
    RegionMembership.objects.create(user=region_user, region=muni_a.region)
    client.force_login(region_user)
    assert client.get(URL).status_code in (302, 403)
    assert client.post(URL, {"step": "rat", "action": "done"}).status_code in (302, 403)
    assert not PrivacyStep.objects.exists()


def test_link_in_the_desk_menu(client, admin_a):
    client.force_login(admin_a)
    html = client.get(f"{C}/xestion/").content.decode()
    assert 'href="/c/concello-a/xestion/privacidade/primeiros-pasos/"' in html


def test_public_minimization_page_linked_from_custody(client, muni_a):
    html = client.get(f"{C}/privacidade/datos/").content.decode()
    assert f'href="{C}/privacidade/que-non-garda-eira/"' in html
    page = client.get(f"{C}/privacidade/que-non-garda-eira/").content.decode()
    assert "Que non garda Eira" in page and "O padrón municipal" in page
    assert "github.com/jcarballol-cloud/eira/tree/master/docs/rxpd/paquete" in page
