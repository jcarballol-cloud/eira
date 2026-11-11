# SPDX-License-Identifier: EUPL-1.2
"""Vídeo do guión do pitch (docs/demo/guion-demo.md) en móbil e escritorio, con subtítulos.

    python tools/tasks.py video     → release-assets/eira-demo-{movil,escritorio}.webm + capturas numeradas

Non forma parte da CI (marca `video`): tarda un par de minutos e xera ficheiros grandes.
"""

import re
import shutil
from pathlib import Path

import pytest
from django.conf import settings
from django.utils import timezone

from apps.incidents.models import Incident

from .conftest import DESKTOP, MOBILE, demo_url, tours_seen_script

pytestmark = [pytest.mark.e2e, pytest.mark.video, pytest.mark.django_db(transaction=False)]
# Os vídeos (> 10 MB) non van ao git: gárdanse en release-assets/ para adxuntalos a unha release
OUT = Path(settings.BASE_DIR) / "release-assets"
SHOTS = Path(settings.BASE_DIR) / "docs" / "capturas" / "v3"

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
        self.go(demo_url(base, email))
        self.page.locator(f"form:has(input[value='{email}']) button").scroll_into_view_if_needed()
        self.page.wait_for_timeout(600)
        self.page.locator(f"form:has(input[value='{email}']) button").click()
        self.page.wait_for_load_state("networkidle")


def run_script(page, base, d):
    """Guión v2 (docs/demo/guion-demo.md): alta por correo → reserva con desconto → pagamento
    rexeitado e reintento → saúde → código e pechadura → peche con valoración → incidencia →
    orde do operario → observatorio → comparativa da deputación."""
    c = base + "/c/vilardeiras"
    email = "pitch.vecina@example.org"
    # 1. Alta: solicitar a app
    d.go(c + "/")
    d.say("Eira · Software libre para a xestión deportiva municipal.", 3)
    page.click("text=Solicita a app de deportes")
    page.wait_for_load_state("networkidle")
    page.fill("#id_name", "Sabela Proba")
    page.fill("#id_email", email)
    page.fill("#id_surnames", "Proba Exemplo")
    page.fill("#id_id_number", "12345678Z")
    page.fill("#id_birth_date", "1990-05-14")
    page.check("#id_resident")
    d.say(
        "Sabela pide a app co DNI e a data: coinciden co padrón do concello e a alta é automática.",
        3.4,
    )
    page.click("main button[type=submit]")
    page.wait_for_load_state("networkidle")
    d.go(base + f"/dev/mailbox/?para={email}")
    d.say("Recibe un correo coa ligazón de instalación e o seu código de empadroamento.", 3)
    body = page.locator(".mail__body").first.inner_text()
    link = re.search(r"(http\S+/app/instalar/\?codigo=\S+)", body).group(1)
    d.go(link)
    d.say("Instrucións para Android e iPhone. A app instálase desde o navegador.", 2.8)
    page.get_by_role("link", name="Abrir a app").click()
    page.wait_for_load_state("networkidle")
    page.fill("#id_email", email)
    page.click("main button[type=submit]")
    page.wait_for_load_state("networkidle")
    page.goto(base + f"/dev/mailbox/?para={email}")
    otp = re.search(r"\b(\d{6})\b", page.locator(".mail__body").first.inner_text()).group(1)
    d.go(base + "/acceso/codigo/")
    page.fill("#id_code", otp)
    page.click("main button[type=submit]")
    page.wait_for_load_state("networkidle")
    d.say("Primeira apertura: entra co correo, sen contrasinal, e o código xa vén cuberto.", 3)
    page.click("main button[type=submit]")
    page.wait_for_load_state("networkidle")
    d.say("«Tes fillos ou persoas ao teu cargo?» A familia, desde o primeiro minuto.", 2.8)
    page.click("text=Non, ir á app")
    page.wait_for_load_state("networkidle")
    # 2. Saúde no dispositivo
    d.go(base + "/saude/")
    page.fill("#h-age", "36")
    page.fill("#h-weight", "64")
    page.fill("#h-minutes", "80")
    page.click("text=Gardar e ver consellos")
    page.wait_for_timeout(400)
    d.say("Peso e idade quedan no teléfono. Non se envían a ningures.", 2.8)
    # 3. Reserva cunha franxa con desconto
    d.go(c + "/")
    page.click("main a:has-text('Pista de pádel da Pereira')")
    page.wait_for_load_state("networkidle")
    rec_day = page.locator(".daychip:has(.daychip__dot.is-rec)").first
    if rec_day.count():
        rec_day.click()
    slot = page.locator(".daypanel:not([hidden]) a.pill-recommended")
    slot = slot if slot.count() else page.locator(".daypanel:not([hidden]) a.pill[data-pick]")
    slot.first.scroll_into_view_if_needed()
    slot.first.click()
    d.say("★ Franxas tranquilas: máis baratas, para repartir mellor o uso.", 3)
    page.click("[data-picksum-go]")
    page.wait_for_load_state("networkidle")
    d.say("Prezo de veciñanza co desconto á vista. Normas versionadas e tempo previsto.", 3.2)
    page.check("#id_accept_rules")
    page.click("main button.btn-lg")
    page.wait_for_load_state("networkidle")
    d.say("TPV do concello (simulado). Primeiro intento: a tarxeta é rexeitada.", 2.8)
    page.click("button[value=ko]")
    page.wait_for_load_state("networkidle")
    d.say("Rexeitado: a reserva NON se confirma e a franxa queda libre ao momento.", 3.2)
    page.click("text=Tentalo de novo")
    page.wait_for_load_state("networkidle")
    page.check("#id_accept_rules")
    page.click("main button.btn-lg")
    page.wait_for_load_state("networkidle")
    page.click("button[value=ok]")
    page.wait_for_load_state("networkidle")
    d.say("Só a notificación asinada da pasarela confirma o pagamento.", 2.8)
    page.click("text=Ver o acceso e a reserva")
    page.wait_for_load_state("networkidle")
    code = page.locator(".access-code__digits").first.text_content().replace(" ", "")
    page.locator("main [data-health-booking] .tip").first.wait_for()
    page.locator("main [data-health-booking]").first.scroll_into_view_if_needed()
    d.say(
        "Consellos para esta sesión: a que hora beber, canto para o seu peso, e a previsión.", 3.4
    )
    # 4. Pechadura sen conexión
    page.locator(".access-code").first.scroll_into_view_if_needed()
    d.say("Código de 6 díxitos válido só na súa franxa.", 2.6)
    page.click("text=Probalo no simulador de pechadura")
    page.wait_for_load_state("networkidle")
    page.fill("#code", code)
    page.click("text=Probar código")
    page.wait_for_load_state("networkidle")
    page.locator(".lock-screen").scroll_into_view_if_needed()
    d.say("A pechadura non ten internet: só o segredo compartido e o seu reloxo. ABERTO.", 3.2)
    # 5. Peche con valoración «Mal» → incidencia
    d.login(base, "uxia@demo.eira.example")
    d.go(c + "/reservas/")
    page.click("text=Checklist de peche")
    page.wait_for_load_state("networkidle")
    page.check("#id_door_ok_0")
    page.check("#id_all_ok_0")
    page.locator("label[for=sc-bad]").click()
    page.locator("label[for=tg-lights_broken]").click()
    page.fill("#id_v-comment", "Dúas lámpadas non acenden.")
    page.locator("label[for=sc-bad]").scroll_into_view_if_needed()
    d.say("Ao marchar: checklist de peche e «Que tal foi?». Mal: as luces non acenden.", 3.2)
    page.click("main button[type=submit]")
    page.wait_for_load_state("networkidle")
    d.say("Créase unha incidencia de iluminación automaticamente.", 2.6)
    inc = Incident.objects.filter(reporter__email="uxia@demo.eira.example").latest("created_at")
    # 6. Concello: valida e crea a orde
    d.login(base, "admin@vilardeiras.demo.eira.example")
    d.go(c + "/xestion/")
    d.say("O concello: panel do día, cobros, incidencias e valoracións.", 2.8)
    d.go(f"{c}/xestion/incidencias/{inc.pk}/")
    page.click("button:has-text('Validar')")
    page.wait_for_load_state("networkidle")
    page.select_option("#id_assigned_to", label="Brais (mantemento)")
    d.say("Valida a incidencia e crea unha orde de traballo para Brais.", 2.8)
    page.click("button:has-text('Crear orde')")
    page.wait_for_load_state("networkidle")
    # 7. Operario
    d.login(base, "brais@demo.eira.example")
    d.go(c + "/operario/")
    d.say("Brais ve só as súas ordes no móbil. Funciona sen cobertura.", 2.8)
    page.click(f"text=Incidencia #{inc.pk}")
    page.wait_for_load_state("networkidle")
    page.locator("input[name=done]").first.check()
    page.fill("#id_closing_notes", "Lámpadas substituídas.")
    page.click("button[value=close]")
    page.wait_for_load_state("networkidle")
    d.say("Orde pechada: Uxía recibe «Arranxado!».", 2.6)
    # 7b. Tableta da monitora: grupo de 40, abecedario do primeiro apelido
    from apps.activities.models import Group
    from apps.activities.services import sessions_for_day

    kiosk = sessions_for_day([Group.objects.get(name="Grupo grande (40)")], timezone.localdate())[0]
    d.login(base, "antia@demo.eira.example")
    d.go(f"{c}/monitor/sesion/{kiosk.pk}/rexistro/")
    d.say("Tableta da monitora: cada persoa toca a inicial do seu primeiro apelido.", 3)
    page.click("[data-mode=out]")
    page.locator(".kiosk__letter.has-people").nth(3).click()
    d.say("Ao saír: o seu nome, coa icona de se pode saír en fotos.", 2.6)
    page.locator(".kiosk__name").first.click()
    d.say("Escala de esforzo Borg CR-10, de verde a vermello. Un toque e listo.", 3)
    page.locator(".kiosk__rpebtn[data-rpe='5']").click()
    page.wait_for_selector(".kiosk__thanks")
    d.say("«Grazas!» e volve soa ao abecedario. Funciona sen conexión.", 2.8)
    # 8. Observatorio e valoracións
    d.login(base, "admin@vilardeiras.demo.eira.example")
    d.go(c + "/xestion/valoracions/")
    d.say("Valoracións: índice por instalación e comentarios, sen nomes.", 3)
    d.go(c + "/actividades/observatorio/?semanas=12")
    d.say(
        "Observatorio da actividade física: anónimo, con grupos de 10 ou máis, fronte á OMS.", 3.2
    )
    # 9. Deputación
    d.login(base, "deputacion@demo.eira.example")
    d.say("A deputación compara concellos: uso por habitante, satisfacción, tendencia.", 3.2)
    d.say("Eira · software libre EUPL · da reserva á porta, e da porta aos datos.", 3.4)


@pytest.mark.parametrize("viewport, name", [(MOBILE, "movil"), (DESKTOP, "escritorio")])
def test_record_pitch_video(browser, base, viewport, name, tmp_path):
    shots = SHOTS / f"pitch-{name}"
    shutil.rmtree(shots, ignore_errors=True)
    shots.mkdir(parents=True)
    ctx = browser.new_context(
        viewport=viewport,
        locale="gl-ES",
        bypass_csp=True,
        record_video_dir=str(tmp_path),
        record_video_size=viewport,
    )
    ctx.add_init_script(tours_seen_script())  # v1.5.1: sen guía nos vídeos
    page = ctx.new_page()
    run_script(page, base, Director(page, shots))
    video = page.video
    ctx.close()
    OUT.mkdir(exist_ok=True)
    target = OUT / f"eira-demo-{name}.webm"
    video.save_as(str(target))
    assert target.stat().st_size > 100_000
