# SPDX-License-Identifier: EUPL-1.2
"""Vídeo final do pitch (≈ 2 min, 1920×1080, subtítulos en galego) seguindo docs/demo/guion-demo.md.

    python tools/tasks.py pitch   → docs/demo/eira-pitch.{mp4,webm,vtt} (ignorados polo git)

Grava con capturas de pantalla do navegador (CDP) en vez do gravador de Playwright, que
comprime moito a 1080p, e monta o vídeo con ffmpeg (H.264 para o MP4, VP9 para o WebM).
Os subtítulos van queimados na imaxe e, ademais, nun .vtt aparte (v5: o MP4 xa non leva
pista de subtítulos activable).
Non forma parte da CI (marca `video`).
"""

import base64
import re
import shutil
import subprocess
import time
from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from apps.incidents.models import Incident

from .conftest import demo_url

pytestmark = [pytest.mark.e2e, pytest.mark.video, pytest.mark.django_db(transaction=False)]

OUT = Path(settings.BASE_DIR) / "docs" / "demo"
SIZE = {"width": 1920, "height": 1080}  # píxeles do vídeo
VIEW = {"width": 1280, "height": 720}  # píxeles CSS: con escala 1,5 o marco do teléfono lese ben
FPS = 30

CAPTION_JS = """(text) => {
  let bar = document.getElementById('eira-caption');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'eira-caption';
    Object.assign(bar.style, {position: 'fixed', left: '0', right: '0', bottom: '0', zIndex: '99999',
      background: 'rgba(22,37,43,.94)', color: '#F7F4EC', font: '600 21px system-ui, sans-serif',
      padding: '14px 32px 16px', borderTop: '4px solid #E2A53A', lineHeight: '1.35',
      textAlign: 'center'});
    document.body.appendChild(bar);
  }
  bar.textContent = text;
}"""


class Recorder:
    """Frames do screencast de Chromium (só chegan cando a imaxe cambia) coa súa hora."""

    def __init__(self, page, frames_dir):
        self.dir, self.frames = frames_dir, []
        self.cdp = page.context.new_cdp_session(page)
        self.cdp.on("Page.screencastFrame", self._frame)
        self.cdp.send(
            "Page.startScreencast",
            {
                "format": "jpeg",
                "quality": 92,
                "maxWidth": SIZE["width"],
                "maxHeight": SIZE["height"],
            },
        )

    def _frame(self, ev):
        path = self.dir / f"{len(self.frames):05d}.jpg"
        path.write_bytes(base64.b64decode(ev["data"]))
        self.frames.append((ev["metadata"]["timestamp"], path))
        self.cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})

    def stop(self):
        self.cdp.send("Page.stopScreencast")


class Director:
    """Subtítulo, pausa para lelo (segundo o número de palabras) e marca de tempo para o .vtt."""

    def __init__(self, page):
        self.page, self.cues = page, []

    def say(self, text, extra=0.0):
        self.page.evaluate(CAPTION_JS, text)
        start = time.time()
        wait = max(2.2, 0.6 + 0.28 * len(text.split())) + extra
        self.page.wait_for_timeout(int(wait * 1000))
        self.cues.append([start, time.time(), text])

    def hide(self):
        self.page.evaluate("() => document.getElementById('eira-caption')?.remove()")

    def go(self, url):
        self.page.goto(url)
        self.page.wait_for_load_state("networkidle")

    def click(self, selector):
        self.page.click(selector)
        self.page.wait_for_load_state("networkidle")

    def show(self, selector):
        loc = self.page.locator(selector).first
        loc.scroll_into_view_if_needed()
        self.page.wait_for_timeout(300)

    def login(self, base, email):
        self.go(demo_url(base, email))
        btn = self.page.locator(f"form:has(input[value='{email}']) button")
        btn.scroll_into_view_if_needed()
        self.page.wait_for_timeout(500)
        btn.click()
        self.page.wait_for_load_state("networkidle")


def alert_window_start():
    """Inicio da franxa do aviso: a próxima reserva nunha instalación descuberta (de Uxía se pode
    ser), para que a vista previa chegue a alguén aínda que se grave de noite."""
    from apps.bookings.models import Booking

    qs = (
        Booking.objects.filter(municipality__slug="vilardeiras", facility__indoor=False)
        .holding()
        .filter(start__gt=timezone.now())
        .order_by("start")
    )
    b = qs.filter(user__email="uxia@demo.eira.example").first() or qs.first()
    return timezone.localtime(b.start - timedelta(hours=1))


def run_pitch(page, base, d):
    c = base + "/c/vilardeiras"
    email = "pitch.vecina@example.org"
    # 1. Alta por padrón
    d.go(c + "/")
    d.say("Eira · Software libre para a xestión deportiva municipal.")
    d.click("text=Solicita a app de deportes")
    page.fill("#id_name", "Sabela")
    page.fill("#id_surnames", "Proba Exemplo")
    page.fill("#id_email", email)
    page.fill("#id_id_number", "12345678Z")
    page.fill("#id_birth_date", "1990-05-14")
    page.check("#id_resident")
    d.show("#id_id_number")
    d.say(
        "Sabela pide a app co DNI e a data de nacemento: coinciden co padrón e a alta é automática."
    )
    d.click("main button[type=submit]")
    d.go(base + f"/dev/mailbox/?para={email}")
    d.say("Chégalle un correo coa ligazón da app e o seu código de empadroamento.")
    body = page.locator(".mail__body").first.inner_text()
    link = re.search(r"(http\S+/app/instalar/\?codigo=\S+)", body).group(1)
    d.go(link)
    page.get_by_role("link", name="Abrir a app").click()
    page.wait_for_load_state("networkidle")
    page.fill("#id_email", email)
    d.click("main button[type=submit]")
    page.goto(base + f"/dev/mailbox/?para={email}")
    otp = re.search(r"\b(\d{6})\b", page.locator(".mail__body").first.inner_text()).group(1)
    d.go(base + "/acceso/codigo/")
    page.fill("#id_code", otp)
    d.click("main button[type=submit]")
    d.say("Entra co correo, sen contrasinal nin tenda de aplicacións.")
    d.click("main button[type=submit]")
    d.click("text=Non, ir á app")
    # 2. Reserva nunha franxa tranquila
    d.go(c + "/")
    d.click("main a:has-text('Pista de pádel da Pereira')")
    rec_day = page.locator(".daychip:has(.daychip__dot.is-rec)").first
    if rec_day.count():
        rec_day.click()
    slot = page.locator(".daypanel:not([hidden]) a.pill-recommended")
    slot = slot if slot.count() else page.locator(".daypanel:not([hidden]) a.pill[data-pick]")
    slot.first.scroll_into_view_if_needed()
    slot.first.click()
    d.say("★ Franxa tranquila: máis barata, para repartir mellor o uso das instalacións.")
    d.click("[data-picksum-go]")
    d.show("main dl")
    d.say("Prezo de veciñanza co desconto á vista.")
    # 3. Pagamento: primeiro rexeitado
    page.check("#id_accept_rules")
    d.click("main button.btn-lg")
    d.say("Pasarela de pagamento simulada. Primeiro intento: tarxeta rexeitada.")
    d.click("button[value=ko]")
    d.say("Un rexeitamento nunca confirma a reserva: a franxa queda libre.")
    d.click("text=Tentalo de novo")
    page.check("#id_accept_rules")
    d.click("main button.btn-lg")
    d.click("button[value=ok]")
    d.say("Segundo intento: só a pasarela asinada confirma o pagamento.")
    # 4. Código e pechadura
    d.click("text=Ver o acceso e a reserva")
    code = page.locator(".access-code__digits").first.text_content().replace(" ", "")
    d.show(".access-code")
    d.say("Código de acceso de 6 díxitos, válido só na súa franxa.")
    d.click("text=Probalo no simulador de pechadura")
    page.fill("#code", code)
    d.click("text=Probar código")
    d.show(".lock-screen")
    d.say("A pechadura non ten internet: segredo compartido e reloxo. ABERTO.", extra=0.4)
    # 5. (v5) Uxía reserva en Pontedouro coa mesma app: tarifa de non empadroada e luz
    d.hide()
    d.login(base, "uxia@demo.eira.example")
    d.go(c + "/")
    page.select_option("#town-select", "pontedouro")
    d.click("form.town-switch button[type=submit]")
    d.click("main a:has-text('Pista de pádel 1 da Ribeira')")
    for chip in page.locator(".daychip").all():
        chip.click()
        lit = page.locator(".daypanel:not([hidden]) a.pill:has(.pill__light)")
        if lit.count():
            break
    lit.first.scroll_into_view_if_needed()
    lit.first.click()
    d.click("[data-picksum-go]")
    d.show("#price-summary")
    d.say("Uxía reserva en Pontedouro coa mesma app: tarifa de non empadroada e luz.")
    page.check("#id_accept_rules")
    d.click("main button.btn-lg")
    d.say("O cobro vai ao TPV de Pontedouro.")
    d.click("button[value=ok]")
    # 6. Peche: «Que tal foi?» e incidencia
    d.hide()
    d.go(c + "/reservas/")
    d.click("text=Checklist de peche")
    page.check("#id_door_ok_0")
    page.check("#id_all_ok_0")
    page.locator("label[for=sc-bad]").click()
    page.locator("label[for=tg-lights_broken]").click()
    page.fill("#id_v-comment", "Dúas lámpadas non acenden.")
    d.show("label[for=sc-bad]")
    d.say("Ao marchar, Uxía responde o peche e «Que tal foi?»: Mal, as luces non acenden.")
    d.click("main button[type=submit]")
    d.say("Créase unha incidencia para o concello automaticamente.")
    inc = Incident.objects.filter(reporter__email="uxia@demo.eira.example").latest("created_at")
    d.hide()
    d.login(base, "admin@vilardeiras.demo.eira.example")
    d.go(f"{c}/xestion/incidencias/{inc.pk}/")
    d.click("button:has-text('Validar')")
    page.select_option("#id_assigned_to", label="Brais (mantemento)")
    d.say("O concello valida a incidencia e crea unha orde de traballo para Brais.")
    d.click("button:has-text('Crear orde')")
    # 7. Orde no móbil do operario
    d.hide()
    d.login(base, "brais@demo.eira.example")
    d.go(c + "/operario/")
    d.say("Brais ve só as súas ordes no móbil. Funciona sen cobertura.")
    d.click(f"text=Incidencia #{inc.pk}")
    page.locator("input[name=done]").first.check()
    page.fill("#id_closing_notes", "Lámpadas substituídas.")
    d.click("button[value=close]")
    d.say("Orde pechada: Uxía recibe «Arranxado!».")
    # 8. Tableta da monitora: abecedario → saída → RPE
    from apps.activities.models import Group
    from apps.activities.services import sessions_for_day

    kiosk = sessions_for_day([Group.objects.get(name="Grupo grande (40)")], timezone.localdate())[0]
    d.hide()
    d.login(base, "antia@demo.eira.example")
    d.go(f"{c}/monitor/sesion/{kiosk.pk}/rexistro/")
    d.say("Tableta da monitora: cada persoa toca a inicial do seu primeiro apelido.")
    page.click("[data-mode=out]")
    page.locator(".kiosk__letter.has-people").nth(3).click()
    d.say("Á saída, toca o seu nome.")
    page.locator(".kiosk__name").first.click()
    d.say("E o esforzo, na escala Borg de 0 a 10. Un toque e listo.")
    page.locator(".kiosk__rpebtn[data-rpe='5']").click()
    page.wait_for_selector(".kiosk__thanks")
    d.say("«Grazas!» e volve soa ao abecedario.")
    # 9. Avisos con vista previa e Telegram
    d.hide()
    d.login(base, "admin@vilardeiras.demo.eira.example")
    d.go(c + "/xestion/avisos/novo/")
    start = alert_window_start()
    page.select_option("#id_category", "alert")
    page.fill("#id_title", "Alerta por vento forte")
    page.fill(
        "#id_body", "Pechamos as instalacións descubertas nesta franxa. Devolvémosche o importe."
    )
    page.select_option("#id_audience", "outdoor")
    page.fill("#id_window_start", start.strftime("%Y-%m-%dT%H:%M"))
    page.fill("#id_window_end", (start + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M"))
    page.check("#id_cancel_bookings")
    for ch in ("app", "email", "telegram", "channel"):
        box = page.locator(f"input[name=channels][value={ch}]")
        if box.count():
            box.check()
    d.say("Un aviso por vento para quen ten reserva nas instalacións descubertas.")
    page.get_by_role("button", name="Vista previa").click()
    page.wait_for_load_state("networkidle")
    d.show("aside[aria-labelledby=pv-title]")
    d.say("Vista previa en app, push, correo e Telegram, e a cantas persoas chega.")
    page.get_by_role("button", name="Enviar ou programar").click()
    page.wait_for_load_state("networkidle")
    from apps.notifications.demo import UXIA_CHAT

    d.go(base + f"/dev/telegram/?chat={UXIA_CHAT}")
    page.locator(".tg-bubble").last.scroll_into_view_if_needed()
    d.say(
        "Telegram: o bot persoal avisa a Uxía, e a canle pública do concello, sen datos persoais."
    )
    # 10. Comparativa da deputación
    d.hide()
    d.login(base, "deputacion@demo.eira.example")
    d.say("A deputación compara os concellos: uso por habitante, ocupación e satisfacción.")
    d.show("table.data")
    d.say("Eira · software libre EUPL · da reserva á porta, e da porta aos datos.", extra=0.8)


def vtt_time(s):
    return f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{s % 60:06.3f}"


def test_record_final_pitch(browser, base, tmp_path, settings):
    settings.EIRA_AI_ENABLED = False  # sen IA cargada: o panel móstrase sen resumo xerado
    call_command("seed_demo", verbosity=0)  # datos rexenerados xusto antes de gravar
    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg, "Fai falla ffmpeg no PATH"
    frames = tmp_path / "frames"
    frames.mkdir()
    ctx = browser.new_context(
        viewport=VIEW,
        device_scale_factor=1.5,
        locale="gl-ES",
        bypass_csp=True,
        color_scheme="light",
    )
    page = ctx.new_page()
    page.goto(base + "/")
    rec = Recorder(page, frames)
    d = Director(page)
    run_pitch(page, base, d)
    page.wait_for_timeout(800)
    rec.stop()
    ctx.close()

    total = encode(rec, d, tmp_path, "eira-pitch")
    print(f"\nPitch: {total:.1f} s, {len(rec.frames)} frames")


def encode(rec, d, tmp_path, stem):
    """Monta MP4 (H.264) e WebM (VP9) cos subtítulos queimados e escribe o .vtt aparte.
    Devolve a duración en segundos."""
    ffmpeg = shutil.which("ffmpeg")
    # Lista para o demuxer concat: cada frame ocupa da súa marca ata a seguinte, sobre unha
    # grella de 1/FPS para que a duración total (e os subtítulos) non derive
    t0 = rec.frames[0][0]
    ticks = [(round((t - t0) * FPS), path) for t, path in rec.frames]
    ticks.append((ticks[-1][0] + FPS, None))
    lines = []
    for (tick, path), (tick_next, _) in zip(ticks, ticks[1:], strict=False):
        if tick_next > tick:
            lines += [f"file '{path.as_posix()}'", f"duration {(tick_next - tick) / FPS:.5f}"]
    lines.append(f"file '{rec.frames[-1][1].as_posix()}'")
    concat = tmp_path / "frames.txt"
    concat.write_text("\n".join(lines), encoding="utf-8")
    total = rec.frames[-1][0] + 1 - t0

    OUT.mkdir(exist_ok=True)
    vtt = OUT / f"{stem}.vtt"
    cues = ["WEBVTT", "Language: gl", ""]
    for i, (start, end, text) in enumerate(d.cues, 1):
        cues += [str(i), f"{vtt_time(max(start - t0, 0))} --> {vtt_time(end - t0)}", text, ""]
    vtt.write_text("\n".join(cues), encoding="utf-8")

    src = ["-f", "concat", "-safe", "0", "-i", str(concat)]
    scale = ["-vf", f"scale={SIZE['width']}:{SIZE['height']},fps={FPS},format=yuv420p"]
    mp4, webm = OUT / f"{stem}.mp4", OUT / f"{stem}.webm"
    subprocess.run(
        # v5: só os subtítulos queimados na imaxe, sen pista de subtítulos activable no MP4
        [ffmpeg, "-y", "-loglevel", "error", *src, *scale,
         "-map", "0:v", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
         "-movflags", "+faststart", str(mp4)],
        check=True,
    )  # fmt: skip
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", *src, *scale, "-c:v", "libvpx-vp9", "-crf", "32",
         "-b:v", "0", "-row-mt", "1", "-deadline", "good", "-cpu-used", "4", str(webm)],
        check=True,
    )  # fmt: skip
    assert mp4.stat().st_size > 500_000 and webm.stat().st_size > 500_000
    return total
