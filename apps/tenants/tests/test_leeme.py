# SPDX-License-Identifier: EUPL-1.2
"""v1.5 · F: LEEME en galego e castelán, enlazado desde o README e a axuda da administración."""

from pathlib import Path

import pytest
from django.conf import settings

from apps.tenants.markup import render

ROOT = Path(settings.BASE_DIR)


@pytest.mark.parametrize(
    "name,needles",
    [
        (
            "LEEME.md",
            [
                "Como usar",
                "Requisitos legais",
                "Se modificas Eira",
                "Modelos de exemplo",
                "art. 7",
                "art. 8",
                "ENS",
                "DPD",
                "EIPD",
                "LOPIVI",
            ],
        ),
        (
            "LEEME.es.md",
            [
                "Cómo usar",
                "Requisitos legales",
                "Si modificas Eira",
                "Modelos de ejemplo",
                "art. 7",
                "art. 8",
                "ENS",
                "DPD",
                "EIPD",
                "LOPIVI",
            ],
        ),
    ],
)
def test_leeme_sections(name, needles):
    text = (ROOT / name).read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text, needle


def test_readme_links_both():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "(LEEME.md)" in text and "(LEEME.es.md)" in text


def test_local_links_exist():
    import re

    for name in ("LEEME.md", "LEEME.es.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)#]+)\)", text):
            if not target.startswith("http"):
                assert (ROOT / target).exists(), target


@pytest.mark.django_db
def test_page_in_each_language(client):
    html = client.get("/axuda/leeme/").content.decode()
    assert "Requisitos legais" in html


def test_markup_escapes_html():
    out = str(render("# T\n\n<script>x</script> [a](javascript:alert(1)) **b**"))
    assert "<script>" not in out and "javascript:" not in out and "<strong>b</strong>" in out
    assert "<h1>T</h1>" in out


def test_markup_table_and_external_link():
    out = str(render("| A | B |\n|---|---|\n| [x](https://e.example) | `c` |\n"))
    assert '<a href="https://e.example"' in out and "<code>c</code>" in out and "<th" in out
