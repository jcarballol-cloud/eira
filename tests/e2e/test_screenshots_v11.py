# SPDX-License-Identifier: EUPL-1.2
"""v1.1 · Capturas do rexistro de limpeza en móbil e escritorio → docs/capturas/v1.1/.

    pytest tests/e2e/test_screenshots_v11.py -m video

Non forma parte da CI (marca `video`). Tamén rexenera a miniatura do perfil de Noela na portada
da demo (`static/img/demo/limpeza.webp`)."""

import io
from pathlib import Path

import pytest
from django.conf import settings

from apps.maintenance.models import CleaningZone, WorkOrder

from .conftest import DESKTOP, MOBILE

pytestmark = [pytest.mark.e2e, pytest.mark.video, pytest.mark.django_db(transaction=False)]
OUT = Path(settings.BASE_DIR) / "docs" / "capturas" / "v1.1"
THUMB = Path(settings.BASE_DIR) / "static" / "img" / "demo" / "limpeza.webp"
V = "/c/vilardeiras"
NOELA, ADMIN = "noela@demo.eira.example", "admin@vilardeiras.demo.eira.example"


def shots():
    aseos = CleaningZone.objects.get(facility__municipality__slug="vilardeiras", name="Aseos")
    vest = CleaningZone.objects.get(facility__municipality__slug="vilardeiras", name="Vestiario 2")
    routed = (
        WorkOrder.objects.filter(kind="cleaning", incident__isnull=False)
        .exclude(status="done")
        .first()
    )
    return [
        ("1-tarefas-e-zonas", NOELA, f"{V}/operario/"),
        ("2-qr-checklist-zona", NOELA, f"{V}/operario/limpeza/{vest.token}/"),
        ("3-tarefa-desde-valoracion-sucia", NOELA, f"{V}/operario/orde/{routed.pk}/"),
        ("4-calendario-limpeza", NOELA, f"{V}/operario/calendario/"),
        ("5-ficha-ultima-limpeza", None, f"{V}/instalacions/{aseos.facility.pk}/"),
        ("6-qr-visto-pola-vecinanza", None, f"{V}/operario/limpeza/{aseos.token}/"),
        ("7-panel-limpeza-atrasada", ADMIN, f"{V}/xestion/"),
        ("8-rexistro-limpeza-concello", ADMIN, f"{V}/xestion/limpeza/"),
        ("9-qr-imprimible-zona", ADMIN, f"{V}/xestion/limpeza/zona/{aseos.pk}/qr/"),
        ("10-persoal-con-empresa", ADMIN, f"{V}/xestion/persoal/"),
        ("11-portada-perfil-limpeza", None, "/?concello=vilardeiras#perfil"),
    ]


@pytest.mark.parametrize("viewport,label", [(MOBILE, "movil"), (DESKTOP, "escritorio")])
def test_v11_screenshots(new_page, base, viewport, label):
    OUT.mkdir(parents=True, exist_ok=True)
    pages = {}
    for name, persona, path in shots():
        page = pages.get(persona)
        if page is None:
            page = pages[persona] = new_page(viewport=viewport, persona=persona)
        sep = "&" if "?" in path else "?"
        url = path.replace("#", f"{sep}marco=0#") if "#" in path else f"{path}{sep}marco=0"
        page.goto(f"{base}{url}")
        page.wait_for_load_state("networkidle")
        height = page.evaluate(
            "Math.max(document.documentElement.scrollHeight,"
            " (document.querySelector('.shell-main')||{}).scrollHeight||0)"
        )
        page.set_viewport_size({"width": viewport["width"], "height": min(int(height) + 120, 6000)})
        page.screenshot(path=OUT / f"{name}-{label}.png", full_page=True)
        page.set_viewport_size(viewport)


def test_demo_thumbnail(new_page, base):
    """Miniatura 640×400 como as dos outros perfís: a pantalla do móbil (390 px, sen a barra da
    demo) centrada sobre o fondo verde claro e cortada polo alto."""
    from PIL import Image

    page = new_page(viewport=MOBILE, persona=NOELA, bypass_csp=True)
    page.goto(f"{base}{V}/operario/?marco=0")
    page.wait_for_load_state("networkidle")
    page.add_style_tag(content=".demo-bar { display: none !important; }")
    png = page.screenshot(clip={"x": 0, "y": 0, "width": 390, "height": 244})
    canvas = Image.new("RGB", (640, 400), (229, 239, 233))
    canvas.paste(Image.open(io.BytesIO(png)).convert("RGB"), (125, 0))
    canvas.save(THUMB, "WEBP", quality=80, method=6)
