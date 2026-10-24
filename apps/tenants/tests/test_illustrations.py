# SPDX-License-Identifier: EUPL-1.2
"""v4.1: ilustración propia en AVIF e WebP, decorativa, e o orixinal non se serve."""

import pytest
from django.contrib.staticfiles import finders
from django.template import Context, Template

pytestmark = pytest.mark.django_db


def render(tag):
    return Template("{% load eira %}" + tag).render(Context({}))


def test_header_has_avif_webp_three_widths_and_night_version():
    html = render('{% illustration "cabecera-eira" eager=True night=True %}')
    for w in (480, 960, 1600):
        assert f"cabecera-eira-{w}.avif {w}w" in html and f"cabecera-eira-{w}.webp {w}w" in html
        assert f"cabecera-eira-noite-{w}.avif" in html
    assert 'alt=""' in html and 'loading="eager"' in html
    # v4.1: día e noite superpostos; o tema (.theme-dark) escolle cal se ve
    assert "illus--day" in html and "illus--night" in html and html.count('loading="eager"') == 1


def test_empty_states_are_lazy_and_decorative():
    html = render('{% illustration "baleiro-avisos" %}')
    assert 'loading="lazy"' in html and 'alt=""' in html and "noite" not in html


def test_original_png_is_not_served():
    assert finders.find("cabecera-eira.png") is None
    assert finders.find("img/ilustracions/cabecera-eira-1600.avif")


def test_credits_mention_ai_illustration_license(client):
    html = client.get("/creditos/").content.decode()
    assert "Ilustración xerada con IA para o proxecto Eira" in html and "CC BY-SA 4.0" in html
