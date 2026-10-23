# SPDX-License-Identifier: EUPL-1.2
"""Vídeo do guión do pitch (docs/demo/guion-demo.md) en móbil e escritorio, con subtítulos.

    python tools/tasks.py video     → docs/demo/eira-demo-{movil,escritorio}.webm + capturas numeradas

Non forma parte da CI (marca `video`): tarda un par de minutos e xera ficheiros grandes.
"""

import re
import shutil
from pathlib import Path

import pytest
from django.conf import settings

from apps.incidents.models import Incident

from .conftest import DESKTOP, MOBILE

pytestmark = [pytest.mark.e2e, pytest.mark.video, pytest.mark.django_db(transaction=False)]
OUT = Path(settings.BASE_DIR) / "docs" / "demo"

CAPTION_JS = """(text) => {
  let bar = document.getElementById('eira-caption');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'eira-caption';
    Object.assign(bar.style, {position: 'fixed', left: '0', right: '0', bottom: '0', zIndex: '99999',
      background: 'rgba(22,37,43,.93)', color: '#F7F4EC', font: '600 17px system-ui, sans-serif',
      padding: '14px 18px', borderTop: '4px solid #E2A53A', lineHeight: '1.35'});
    document.body.appendChild(bar);
  }
  bar.textContent = text;
}"""


class Director:
    """Leva o percorrido: subtítulo, pausa para ler e captura numerada en cada paso."""

    def __init__(self, page, shots_dir, slow=1.0):
        self.page, self.dir, self.n, self.slow = page, shots_dir, 0, slow

    def say(self, text, wait=2.6):
        self.page.evaluate(CAPTION_JS, text)
        self.page.wait_for_timeout(int(wait * 1000 * self.slow))
        self.n += 1
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower())[:40].strip("-")
        self.page.screenshot(path=str(self.dir / f"{self.n:02d}-{slug}.png"))

    def go(self, url):
        self.page.goto(url)
        self.page.wait_for_load_state("networkidle")

    def login(self, base, email):
        self.go(base + "/")
        self.page.locator(f"form:has(input[value='{email}']) button").scroll_into_view_if_needed()
        self.page.wait_for_timeout(600)
        self.page.locator(f"form:has(input[value='{email}']) button").click()
        self.page.wait_for_load_state("networkidle")


def run_script(page, base, d):
    # 1. Portada
    d.go(base + "/")
    d.say("Eira · Reservar é o fácil. O difícil é abrir a porta.", 3.2)
    # 2. Veciña: buscar e reservar
    d.login(base, "uxia@demo.eira.example")
    d.say("Uxía, veciña de Vilardeiras, busca unha instalación. Lista accesible ou mapa.")
    page.click("text=Pista de pádel da Pereira")
    page.wait_for_load_state("networkidle")
    d.say("Grella semanal: libre, ocupada ou ★ recomendada (pouca demanda).", 3)
    slot = (
        page.locator(".day-list details[open] a.slot")
        if page.viewport_size["width"] < 700
        else page.locator("table.week a.slot")
    )
    slot.first.scroll_into_view_if_needed()
    slot.first.click()
    page.wait_for_load_state("networkidle")
    d.say("Normas versionadas: queda gardado que versión aceptou e cando. E o tempo previsto.", 3.2)
    page.check("#id_accept_rules")
    page.click("main button.btn-lg")
    page.wait_for_load_state("networkidle")
    d.say("Pagamento no TPV do concello (simulado).")
    page.click("button[value=ok]")
    page.wait_for_load_state("networkidle")
    page.locator(".access-code").scroll_into_view_if_needed()
    d.say("Reserva confirmada: código de 6 díxitos válido só na súa franxa (±10 min).", 3.4)
    code = page.locator(".access-code").inner_text().strip()
    # 3. Simulador de pechadura
    page.click("text=Probalo no simulador de pechadura")
    page.wait_for_load_state("networkidle")
    d.say("A pechadura non ten internet: só o segredo compartido e o seu reloxo.")
    page.fill("#code", code)
    page.click("text=Probar código")
    page.wait_for_load_state("networkidle")
    page.locator(".lock-screen").scroll_into_view_if_needed()
    d.say("Á hora da reserva: ABERTO.", 3)
    page.click("button[value='60']")
    page.wait_for_load_state("networkidle")
    page.click("button[value='60']")
    page.wait_for_load_state("networkidle")
    page.fill("#code", code)
    page.click("text=Probar código")
    page.wait_for_load_state("networkidle")
    page.locator(".lock-screen").scroll_into_view_if_needed()
    d.say("Dúas horas despois, o mesmo código: DENEGADO.", 3)
    # 4. Checklist de peche
    d.go(base + "/c/vilardeiras/reservas/")
    d.say("Ao rematar, Eira pide confirmar que todo queda pechado.")
    page.click("text=Checklist de peche")
    page.wait_for_load_state("networkidle")
    page.check("#id_door_ok_1")
    page.check("#id_all_ok_0")
    d.say("A porta non pechou ben: Uxía marca «Non».")
    page.click("main button[type=submit]")
    page.wait_for_load_state("networkidle")
    d.say("Créase unha incidencia automaticamente.")
    inc = Incident.objects.filter(
        source="checklist", reporter__email="uxia@demo.eira.example"
    ).latest("created_at")
    # 5. Concello
    d.login(base, "admin@vilardeiras.demo.eira.example")
    d.go(base + "/c/vilardeiras/xestion/")
    d.say("O concello: panel do día con reservas, chaves e incidencias por validar.", 3.2)
    d.go(f"{base}/c/vilardeiras/xestion/incidencias/{inc.pk}/")
    d.say("Valida a incidencia (a veciña recibe un aviso).")
    page.click("button:has-text('Validar')")
    page.wait_for_load_state("networkidle")
    page.select_option("#id_assigned_to", label="Brais (mantemento)")
    d.say("Crea unha orde de traballo para Brais.")
    page.click("button:has-text('Crear orde')")
    page.wait_for_load_state("networkidle")
    # 6. Operario
    d.login(base, "brais@demo.eira.example")
    d.go(base + "/c/vilardeiras/operario/")
    d.say("Brais, de mantemento, ve as súas ordes. Funciona sen cobertura.")
    page.click(f"text=Incidencia #{inc.pk}")
    page.wait_for_load_state("networkidle")
    page.locator("input[name=done]").first.check()
    page.fill("#id_closing_notes", "Fechadura axustada.")
    d.say("Checklist, foto opcional e peche.")
    page.click("button[value=close]")
    page.wait_for_load_state("networkidle")
    d.say("Orde pechada: a incidencia queda resolta e Uxía recibe «Arranxado!».")
    # 7. Indicadores e deputación
    d.login(base, "admin@vilardeiras.demo.eira.example")
    d.go(base + "/c/vilardeiras/xestion/indicadores/")
    d.say(
        "Indicadores: ocupación, non presentadas, infrauso, incidencias, ingresos. Con táboa e CSV/ODS.",
        3.4,
    )
    page.mouse.wheel(0, 900)
    d.say("Mapa de calor por franxa horaria: datos para decidir horarios.", 3)
    d.login(base, "deputacion@demo.eira.example")
    d.say("A deputación compara concellos e dá de alta novos en tres pasos.", 3)
    d.say("Eira · software libre EUPL · da reserva á porta, e da porta aos datos.", 3.4)


@pytest.mark.parametrize("viewport, name", [(MOBILE, "movil"), (DESKTOP, "escritorio")])
def test_record_pitch_video(browser, base, viewport, name, tmp_path):
    shots = OUT / f"pasos-{name}"
    shutil.rmtree(shots, ignore_errors=True)
    shots.mkdir(parents=True)
    ctx = browser.new_context(
        viewport=viewport,
        locale="gl-ES",
        bypass_csp=True,
        record_video_dir=str(tmp_path),
        record_video_size=viewport,
    )
    page = ctx.new_page()
    run_script(page, base, Director(page, shots))
    video = page.video
    ctx.close()
    target = OUT / f"eira-demo-{name}.webm"
    video.save_as(str(target))
    assert target.stat().st_size > 100_000
