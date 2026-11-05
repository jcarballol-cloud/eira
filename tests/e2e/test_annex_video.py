# SPDX-License-Identifier: EUPL-1.2
"""v5 (+ v1.2 e v1.5) · Vídeo anexo (≤ 75 s): «Eira para o concello e a saúde».

    python tools/tasks.py annex   → docs/demo/eira-anexo-saude.{mp4,webm,vtt} (ignorados polo git)

Percorre os consellos de saúde co tempo, as valoracións, o observatorio co índice de vida activa,
o cartel da porta, a revisión de seguridade e o rexistro de brechas. Mesma técnica ca o pitch
(captura CDP, subtítulos queimados). Non forma parte da CI (marca `video`)."""

import shutil

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import DataBreach
from apps.bookings.models import Booking
from apps.facilities.models import Facility
from apps.maintenance.models import WorkOrder

from .test_pitch_video import VIEW, Director, Recorder, encode

pytestmark = [pytest.mark.e2e, pytest.mark.video, pytest.mark.django_db(transaction=False)]


def run_annex(page, base, d):
    c = base + "/c/vilardeiras"
    # 1. Consellos de saúde co tempo da franxa (calculados no dispositivo)
    d.login(base, "uxia@demo.eira.example")
    page.evaluate(
        "localStorage.setItem('eira-health-v1', JSON.stringify({age: '27', weight: '61.5', minutes: '60'}))"
    )
    upcoming = (
        Booking.objects.filter(
            user__email="uxia@demo.eira.example", status="confirmed", start__gt=timezone.now()
        )
        .order_by("start")
        .first()
    )
    d.go(f"{c}/reservas/{upcoming.pk}/")
    page.locator("main [data-health-booking] .tip").first.wait_for()
    d.show("main [data-health-booking]")
    d.say(
        "Saúde: consellos co tempo real da franxa, calculados no móbil. O peso non sae do teléfono."
    )
    # v1.5 · «Escoitar»
    d.go(f"{c}/app/")
    d.show(".listen-btn")
    d.say("Novo: «Escoitar». O móbil le a pantalla en voz alta, sen enviar o texto a ninguén.")
    # 2. Valoracións
    d.hide()
    d.login(base, "admin@vilardeiras.demo.eira.example")
    d.go(f"{c}/xestion/valoracions/")
    d.say("«Que tal foi?»: o concello ve as valoracións por instalación, sen nomes.")
    # 3. Observatorio e índice de vida activa
    d.go(f"{c}/actividades/observatorio/?semanas=12")
    d.say("O observatorio segue igual: esforzo, asistencia e probas físicas, só agregados.")
    # v1.5 · Mapa de procedencia
    d.go(f"{c}/xestion/procedencia/")
    d.show(".flow-map svg")
    d.say("Novo: mapa de procedencia, sempre agregado: só grupos de dez persoas ou máis, sen GPS.")
    d.hide()
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    d.go(f"{c}/instalacions/{padel.pk}/")
    d.show(".facility-trust")
    d.say(
        "Novo: índice de vida activa de 0 a 100, con uso real, idades, satisfacción, accesibilidade e mantemento."
    )
    # 4. Cartel da porta e ficha de seguridade
    d.show(".safety-card")
    d.say("Ficha de seguridade: material, protocolo de accidentes, DEA e 112.")
    d.go(f"{c}/xestion/instalacions/{padel.pk}/qr/")
    d.say("Cartel para a porta: QR, normas, accidentes, DEA e 112. Tamén en PDF accesible.")
    # 5. Revisión de seguridade
    review = WorkOrder.objects.filter(kind="safety_review", facility=padel).latest("closed_at")
    d.go(f"{c}/xestion/ordes/{review.pk}/")
    d.say(
        "Revisión de seguridade inicial Eira: trece puntos. Ao pechala, a ficha mostra «Revisada»."
    )
    # 6. Rexistro de brechas
    breach = DataBreach.objects.filter(municipality__slug="vilardeiras").first()
    d.go(f"{c}/xestion/privacidade/brechas/")
    d.say("Rexistro de brechas: prazo de 72 horas para a AEPD, só para o concello e o DPD.")
    d.go(f"{c}/xestion/privacidade/brechas/{breach.pk}/comunicacion/")
    d.say("E a comunicación ás persoas afectadas, en linguaxe clara.")
    # 7. v1.2 · Panel de rendemento (consumo estimado)
    hall = Facility.objects.get(name="Pavillón municipal de Vilardeiras")
    d.go(f"{c}/xestion/instalacions/{hall.pk}/rendemento/")
    d.say(
        "Novo: rendemento de cada instalación. Ocupación, uso real e consumo estimado en kWh, € e CO₂."
    )
    # 8. v1.2 · NPS anual
    from apps.surveys.models import Survey

    survey = Survey.objects.filter(municipality__slug="vilardeiras").order_by("year").first()
    d.go(f"{c}/xestion/enquisas/{survey.pk}/")
    d.say("E a enquisa anual de satisfacción: NPS e sete aspectos, só con dez respostas ou máis.")
    d.say("Eira · para o concello e a saúde · software libre EUPL.")


def test_record_annex(browser, base, tmp_path, settings):
    settings.EIRA_AI_ENABLED = False
    call_command("seed_demo", verbosity=0)
    assert shutil.which("ffmpeg"), "Fai falla ffmpeg no PATH"
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
    run_annex(page, base, d)
    page.wait_for_timeout(800)
    rec.stop()
    ctx.close()
    total = encode(rec, d, tmp_path, "eira-anexo-saude")
    print(f"\nAnexo: {total:.1f} s, {len(rec.frames)} frames")
