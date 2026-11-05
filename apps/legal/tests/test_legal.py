# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · D: fluxo deputación → concello → apps, versións, rexistro e retirada."""

import pytest

from apps.accounts.models import (
    AuditLog,
    Dependent,
    HealthProfile,
    Household,
    Membership,
    RegionMembership,
    Role,
    User,
)
from apps.accounts.views import delete_user, export_user_data
from apps.legal import services
from apps.legal.models import DocKind, LegalAcceptance, LegalModel, LegalVersion
from apps.tenants.models import Municipality, Region

pytestmark = pytest.mark.django_db
NOTICE_GL = "MODELO DE EXEMPLO — non é un documento legal válido"
NOTICE_ES = "MODELO DE EJEMPLO — no es un documento legal válido"
VALUES = {"responsible": "Concello de Proba", "dpo": "dpd@example.org", "address": "Praza 1"}


@pytest.fixture
def world():
    region = Region.objects.create(name="Deputación", slug="dep-legal")
    town = Municipality.objects.create(
        name="Legalia",
        slug="legalia",
        region=region,
        address="Praza 1",
        dpo_contact="dpd@x.example",
    )
    admin = User.objects.create_user("admin-legal@example.org")
    Membership.objects.create(user=admin, municipality=town, role=Role.ADMIN)
    person = User.objects.create_user("persoa-legal@example.org", display_name="Persoa")
    dep = User.objects.create_user("dep-legal@example.org")
    RegionMembership.objects.create(user=dep, region=region)
    return region, town, admin, person, dep


def publish(town, kind=DocKind.TERMS, **kw):
    model = services.latest_model(town.region, kind)
    return services.publish_version(town, kind, model, **{**VALUES, **kw})


def test_included_models_exist_in_both_languages_with_notice():
    from pathlib import Path

    from django.conf import settings

    folder = Path(settings.BASE_DIR) / "docs" / "legal" / "modelos"
    for slug in ("privacidade", "condicions", "menores", "imaxe", "normas", "saude"):
        assert NOTICE_GL in (folder / f"{slug}.gl.md").read_text(encoding="utf-8")
        assert NOTICE_ES in (folder / f"{slug}.es.md").read_text(encoding="utf-8")


def test_included_model_strips_notice_from_body():
    model = services.included_model(DocKind.PRIVACY)
    assert model.region is None and model.title_gl == "Información de privacidade"
    assert "MODELO DE EXEMPLO" not in model.body_gl and "[RESPONSABLE]" in model.body_gl


def test_region_publishes_then_town_sees_new_model(client, world):
    region, town, _admin, _person, dep = world
    client.force_login(dep)
    url = f"/rexion/{region.slug}/legal/terms/"
    assert client.get(url).status_code == 200
    resp = client.post(
        url,
        {
            "title_gl": "Condicións da deputación",
            "title_es": "Condiciones de la diputación",
            "body_gl": "Texto [CONCELLO]",
            "body_es": "Texto [CONCELLO]",
            "substantial": "on",
        },
    )
    assert resp.status_code == 302
    model = LegalModel.objects.get(region=region, kind="terms")
    assert services.latest_model(region, "terms") == model
    assert NOTICE_GL in client.get(f"/rexion/{region.slug}/legal/").content.decode()


def test_other_region_cannot_publish(client, world):
    region, *_rest = world
    other = User.objects.create_user("outra-dep@example.org")
    client.force_login(other)
    assert client.get(f"/rexion/{region.slug}/legal/").status_code == 403


def test_adopt_as_is_fills_data_and_keeps_notice(client, world):
    _region, town, admin, _person, _dep = world
    client.force_login(admin)
    url = f"/c/{town.slug}/xestion/legal/privacy/"
    assert NOTICE_GL in client.get(url).content.decode()
    client.post(url, {**VALUES, "substantial": "on"})
    version = LegalVersion.objects.get(document__kind="privacy")
    assert version.mode == "as_is" and version.is_example
    assert "Concello de Proba" in version.body_gl and "[RESPONSABLE]" not in version.body_gl
    assert "dpd@example.org" in version.body_es and "[DPD]" not in version.body_es
    html = client.get(f"/c/{town.slug}/legal/privacy/").content.decode()
    assert NOTICE_GL in html and "Concello de Proba" in html


def test_required_data_to_publish(client, world):
    _region, town, admin, _person, _dep = world
    client.force_login(admin)
    resp = client.post(f"/c/{town.slug}/xestion/legal/privacy/", {"responsible": "X"})
    assert resp.status_code == 200 and not LegalVersion.objects.exists()


def test_as_is_cannot_remove_notice(client, world):
    _region, town, admin, _person, _dep = world
    client.force_login(admin)
    client.post(f"/c/{town.slug}/xestion/legal/privacy/", {**VALUES, "reviewed": "on"})
    assert not LegalVersion.objects.exists()


def test_adapted_reviewed_removes_notice_unreviewed_keeps_it(client, world):
    _region, town, admin, _person, _dep = world
    client.force_login(admin)
    data = {
        **VALUES,
        "adapt": "on",
        "title_gl": "Propio",
        "title_es": "Propio",
        "body_gl": "Corpo [CONCELLO]",
        "body_es": "Cuerpo [CONCELLO]",
    }
    client.post(f"/c/{town.slug}/xestion/legal/image/", data)
    first = LegalVersion.objects.get(document__kind="image")
    assert first.is_example and first.body_gl == "Corpo Legalia"
    client.post(f"/c/{town.slug}/xestion/legal/image/", {**data, "reviewed": "on"})
    second = LegalVersion.objects.filter(document__kind="image").order_by("-number").first()
    assert second.number == 2 and not second.is_example and second.reviewed_by == admin
    assert NOTICE_GL not in client.get(f"/c/{town.slug}/legal/image/").content.decode()


def test_permissions_on_town_pages(client, world):
    region, town, _admin, person, dep = world
    publish(town)
    client.force_login(person)
    assert client.get(f"/c/{town.slug}/xestion/legal/").status_code == 403
    assert client.get(f"/c/{town.slug}/xestion/legal/rexistro.csv").status_code == 403
    client.force_login(dep)
    assert client.get(f"/c/{town.slug}/xestion/legal/").status_code == 200
    assert client.get(f"/c/{town.slug}/xestion/legal/rexistro.csv").status_code == 403
    assert client.post(f"/c/{town.slug}/xestion/legal/terms/", VALUES).status_code == 403
    dpo = User.objects.create_user("dpd-legal@example.org")
    Membership.objects.create(user=dpo, municipality=town, role=Role.DPO)
    client.force_login(dpo)
    assert client.get(f"/c/{town.slug}/xestion/legal/rexistro.csv").status_code == 200
    assert client.post(f"/c/{town.slug}/xestion/legal/terms/", VALUES).status_code == 403


def test_app_shows_pending_then_accept_records_all_fields(client, world):
    _region, town, _admin, person, _dep = world
    version = publish(town)
    client.force_login(person)
    html = client.get(f"/c/{town.slug}/app/").content.decode()
    assert "legal-banner" in html
    url = f"/c/{town.slug}/legal/terms/"
    client.post(url, {})
    assert not LegalAcceptance.objects.exists()
    client.post(url, {"accepted": "1"})
    acceptance = LegalAcceptance.objects.get()
    assert (acceptance.user, acceptance.version, acceptance.channel) == (person, version, "app")
    assert acceptance.accepted_at
    assert "legal-banner" not in client.get(f"/c/{town.slug}/app/").content.decode()


def test_substantial_requires_new_acceptance_minor_does_not(world):
    _region, town, _admin, person, _dep = world
    first = publish(town)
    services.accept(person, first)
    assert services.pending_versions(person, town) == []
    publish(town, substantial=False)
    assert services.pending_versions(person, town) == []
    third = publish(town, substantial=True)
    assert services.pending_versions(person, town) == [third]
    services.accept(person, third)
    assert services.pending_versions(person, town) == []


def test_optional_documents_not_pressed_minors_only_with_dependents(world):
    _region, town, _admin, person, _dep = world
    publish(town, DocKind.IMAGE)
    publish(town, DocKind.HEALTH)
    minors = publish(town, DocKind.MINORS)
    assert services.pending_versions(person, town) == []
    household = Household.objects.create(responsible=person)
    Dependent.objects.create(household=household, first_name="Nena", birth_year=2016)
    person.refresh_from_db()
    assert services.pending_versions(person, town) == [minors]


def test_cannot_accept_old_version(client, world):
    _region, town, _admin, person, _dep = world
    publish(town)
    publish(town)
    client.force_login(person)
    client.post(f"/c/{town.slug}/legal/terms/?v=1", {"accepted": "1"})
    assert not LegalAcceptance.objects.exists()


def test_withdraw_revocable_and_effects(client, world):
    _region, town, _admin, person, _dep = world
    image = services.accept(person, publish(town, DocKind.IMAGE))
    person.refresh_from_db()
    assert person.photo_consent
    health = services.accept(person, publish(town, DocKind.HEALTH))
    HealthProfile.objects.create(user=person, age=40)
    client.force_login(person)
    assert client.get("/conta/documentos/").status_code == 200
    client.post(f"/conta/documentos/{image.pk}/retirar/")
    client.post(f"/conta/documentos/{health.pk}/retirar/")
    person.refresh_from_db()
    image.refresh_from_db()
    assert image.withdrawn_at and not person.photo_consent
    assert not HealthProfile.objects.filter(user=person).exists()
    assert LegalAcceptance.objects.filter(user=person).count() == 2  # o rexistro consérvase
    assert services.status_for(person, image.version.document) == "withdrawn"
    assert services.pending_versions(person, town) == []


def test_withdraw_not_allowed_for_terms_or_others_records(client, world):
    _region, town, _admin, person, _dep = world
    terms = services.accept(person, publish(town))
    client.force_login(person)
    client.post(f"/conta/documentos/{terms.pk}/retirar/")
    terms.refresh_from_db()
    assert terms.withdrawn_at is None
    other = User.objects.create_user("outra-legal@example.org")
    client.force_login(other)
    assert client.post(f"/conta/documentos/{terms.pk}/retirar/").status_code == 404


def test_privacy_switch_withdraws_image_acceptance(client, world):
    _region, town, _admin, person, _dep = world
    image = services.accept(person, publish(town, DocKind.IMAGE))
    client.force_login(person)
    client.post("/conta/privacidade/", {"notify_email": "on"})
    image.refresh_from_db()
    assert image.withdrawn_at is not None


def test_register_csv_and_audit_and_formula_safety(client, world):
    _region, town, admin, person, _dep = world
    person.display_name = "=SUM(A1)"
    person.save()
    services.accept(person, publish(town), channel="web")
    client.force_login(admin)
    resp = client.get(f"/c/{town.slug}/xestion/legal/rexistro.csv")
    text = resp.content.decode("utf-8-sig")
    assert "persoa,correo,documento,versión,data,canle,retirada" in text
    assert person.email in text and "'=SUM(A1)" in text and ",1," in text and "Web" in text
    assert AuditLog.objects.filter(action="legal.register_export").exists()


def test_tenant_isolation_of_register(client, world):
    _region, town, _admin, person, _dep = world
    other = Municipality.objects.create(name="Outra", slug="outra-legal")
    services.accept(person, publish(other))
    assert list(services.register_rows(town)) == []


def test_export_and_account_deletion_keep_register_without_person(world):
    _region, town, _admin, person, _dep = world
    services.accept(person, publish(town))
    assert export_user_data(person)["legal_acceptances"][0]["document"] == "terms"
    delete_user(person)
    acceptance = LegalAcceptance.objects.get()
    assert acceptance.user is None
    assert "(conta eliminada)" in next(services.register_rows(town))[0]


def test_rules_document_integrates_facility_rules(client, world):
    from apps.facilities.models import RulesVersion
    from conftest import make_facility

    _region, town, _admin, person, _dep = world
    facility = make_facility(town)
    RulesVersion.objects.create(facility=facility, version=99, text="Norma propia da pista")
    publish(town, DocKind.RULES)
    client.force_login(person)
    html = client.get(f"/c/{town.slug}/legal/rules/").content.decode()
    assert "Norma propia da pista" in html and facility.name in html


def test_spanish_view_uses_spanish_text_and_notice(client, world):
    _region, town, _admin, _person, _dep = world
    publish(town, DocKind.PRIVACY)
    client.cookies["django_language"] = "es"
    html = client.get(f"/c/{town.slug}/legal/privacy/").content.decode()
    assert NOTICE_ES in html and "Información de privacidad" in html


def test_public_can_read_but_must_log_in_to_accept(client, world):
    _region, town, _admin, _person, _dep = world
    publish(town)
    url = f"/c/{town.slug}/legal/terms/"
    assert client.get(url).status_code == 200
    assert client.post(url, {"accepted": "1"}).status_code == 302
    assert not LegalAcceptance.objects.exists()


def test_html_in_adapted_text_is_escaped(world):
    _region, town, _admin, _person, _dep = world
    version = publish(
        town,
        adapted={"title_gl": "T", "title_es": "T", "body_gl": "<script>x</script>", "body_es": "y"},
    )
    from apps.tenants.markup import render

    assert "<script>" not in str(render(version.body_gl))
