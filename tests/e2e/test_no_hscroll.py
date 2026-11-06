# SPDX-License-Identifier: EUPL-1.2
"""v4: ningunha pantalla de veciñanza, operario nin tableta ten scroll horizontal, nin con texto
normal nin con texto grande, a 360 e 390 px (e dentro do marco de teléfono no escritorio)."""

import pytest
from django.utils import timezone

from apps.activities.models import Group
from apps.activities.services import sessions_for_day
from apps.bookings.models import Booking
from apps.facilities.models import Facility
from apps.maintenance.models import WorkOrder

from .conftest import uxia_waitlist_entry

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=False)]

# Páxina enteira e panel con scroll propio (.shell-main) sen desbordar; e ningún elemento visible
# fóra do ancho do seu panel (as táboas con scroll propio tampouco se admiten nestes perfís).
OVERFLOW_JS = """() => {
  const out = [];
  const de = document.documentElement;
  if (de.scrollWidth > de.clientWidth + 1) out.push(`html ${de.scrollWidth}>${de.clientWidth}`);
  const main = document.querySelector('.shell-main') || document.body;
  if (main.scrollWidth > main.clientWidth + 1) out.push(`main ${main.scrollWidth}>${main.clientWidth}`);
  const box = main.getBoundingClientRect();
  for (const el of main.querySelectorAll('*')) {
    if (el.closest('.visually-hidden, [hidden], noscript, .leaflet-container, .skip-link')) continue;
    const cs = getComputedStyle(el);
    if (cs.position === 'fixed' || cs.display === 'none' || cs.visibility === 'hidden') continue;
    if (cs.overflowX === 'auto' || cs.overflowX === 'scroll') {
      if (el.scrollWidth > el.clientWidth + 1) out.push(`scroll ${el.tagName}.${el.className} ${el.scrollWidth}>${el.clientWidth}`);
    }
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.right > box.right + 1 || r.left < box.left - 1) out.push(`fóra ${el.tagName}.${String(el.className).slice(0,40)} ${Math.round(r.left)}–${Math.round(r.right)} / ${Math.round(box.left)}–${Math.round(box.right)}`);
    // texto que desborda a súa propia caixa (p. ex. o importe ou os díxitos do código de acceso)
    if (cs.display !== 'inline' && el.textContent.trim() && el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 1 && cs.textOverflow !== 'ellipsis' && cs.overflowX !== 'auto' && cs.overflowX !== 'scroll') {
      const er = el.getBoundingClientRect();
      const kid = [...el.querySelectorAll('*')].filter(k => k.getBoundingClientRect().right > er.right + 1).map(k => `${k.tagName}.${String(k.className).slice(0,25)}`).pop() || '';
      out.push(`desborda ${el.tagName}.${String(el.className).slice(0,30)} «${el.textContent.trim().slice(0,20)}» ${el.scrollWidth}>${el.clientWidth} ${kid}`);
    }
  }
  return [...new Set(out)].slice(0, 6);
}"""


def pages():
    c = "/c/vilardeiras"
    padel = Facility.objects.get(municipality__slug="vilardeiras", kind="padel")
    upcoming = (
        Booking.objects.filter(
            user__email="uxia@demo.eira.example", status="confirmed", end__gt=timezone.now()
        )
        .order_by("start")
        .first()
    )
    order = (
        WorkOrder.objects.filter(
            municipality__slug="vilardeiras", assigned_to__email="brais@demo.eira.example"
        )
        .exclude(status="done")
        .first()
    )
    big = sessions_for_day([Group.objects.get(name="Grupo grande (40)")], timezone.localdate())[0]
    kids = Group.objects.filter(municipality__slug="vilardeiras", rpe_scale="omni").first()
    kids_session = sessions_for_day([kids], timezone.localdate())
    manuel = (
        Booking.objects.filter(
            user__email="manuel@demo.eira.example", status="confirmed", end__gt=timezone.now()
        )
        .order_by("start")
        .first()
    )
    start = timezone.localtime(upcoming.start).isoformat()
    from apps.bookings.models import OpenGame

    hall = Facility.objects.get(name="Pavillón municipal de Vilardeiras")
    game = OpenGame.objects.filter(municipality__slug="vilardeiras", joins__isnull=False).first()
    wait = uxia_waitlist_entry()
    neighbour = [
        f"{c}/app/",
        f"{c}/",
        f"{c}/instalacions/{padel.pk}/",
        f"{c}/reservas/",
        f"{c}/reservas/{upcoming.pk}/",
        f"{c}/instalacions/{padel.pk}/reservar/?inicio=" + start.replace("+", "%2B"),
        f"{c}/incidencias/nova/",
        f"{c}/avisos/",
        "/conta/",
        "/conta/familia/",
        "/conta/privacidade/",
        "/saude/",
        f"{c}/actividades/",
        f"{c}/app/benvida/?paso=familia",
        f"{c}/avisos/preferencias/",
        # v1.2
        f"{c}/seguridade/",
        f"{c}/seguridade/alerta/?instalacion={hall.pk}",
        f"{c}/seguridade/accidente/{hall.pk}/",
        f"{c}/seguridade/emerxencia/",
        f"{c}/enquisa/",
        f"{c}/reservas/partidas/",
        f"{c}/reservas/partidas/{game.pk}/",
        f"{c}/carne/",
        f"{c}/reservas/lista-de-espera/{wait.pk}/",
        f"{c}/instalacions/{hall.pk}/",
        # v1.3
        "/conta/seguridade/",
        f"{c}/privacidade/avaliacion-impacto/",
    ]
    operator = [f"{c}/operario/", f"{c}/operario/orde/{order.pk}/", f"{c}/operario/calendario/"]
    tablet = [
        f"{c}/monitor/",
        f"{c}/monitor/estatisticas/",
        f"{c}/monitor/sesion/{big.pk}/rexistro/",
        f"{c}/monitor/sesion/{big.pk}/asistencia/",
    ]
    if kids_session:
        tablet.append(f"{c}/monitor/sesion/{kids_session[0].pk}/esforzo/")
    return {
        "uxia@demo.eira.example": neighbour,
        "manuel@demo.eira.example": [f"{c}/app/", f"{c}/reservas/", f"{c}/instalacions/{padel.pk}/"]
        + ([f"{c}/reservas/{manuel.pk}/"] if manuel else []),
        "brais@demo.eira.example": operator,
        "antia@demo.eira.example": tablet,
    }


# A fonte do sistema cambia o ancho do texto: en Linux (CI) é DejaVu Sans, máis ancha ca Segoe UI.
# Fórzase DejaVu Sans ou Verdana (mesmas métricas en Windows) para que o resultado non dependa da
# máquina e se mida o caso máis ancho.
WIDE_FONT = """document.addEventListener('DOMContentLoaded', () => {
  const s = document.createElement('style');
  s.textContent = '*:not(code):not(kbd):not(.mono) { font-family: "DejaVu Sans", Verdana, sans-serif !important; }';
  document.head.appendChild(s);
});"""


def wide_page(new_page, **kw):
    page = new_page(bypass_csp=True, **kw)
    page.context.add_init_script(WIDE_FONT)
    return page


@pytest.mark.parametrize("width", [360, 390])
@pytest.mark.parametrize("large", [False, True], ids=["texto-normal", "texto-grande"])
def test_no_horizontal_scroll(new_page, base, width, large):
    failures = []
    for persona, paths in pages().items():
        page = wide_page(new_page, viewport={"width": width, "height": 800}, persona=persona)
        page.context.add_cookies(
            [{"name": "eira_prefs", "value": "large_text" if large else "", "url": base}]
        )
        for path in paths:
            page.goto(base + path)
            page.wait_for_load_state("networkidle")
            problems = page.evaluate(OVERFLOW_JS)
            if problems:
                failures.append(f"{persona} {path}: {problems}")
    assert not failures, "\n".join(failures)


def test_no_horizontal_scroll_inside_phone_frame(new_page, base):
    failures = []
    for persona in (
        "uxia@demo.eira.example",
        "manuel@demo.eira.example",
        "brais@demo.eira.example",
    ):
        page = wide_page(new_page, viewport={"width": 1280, "height": 900}, persona=persona)
        for path in pages()[persona]:
            page.goto(base + path + ("&" if "?" in path else "?") + "marco=1")
            page.wait_for_load_state("networkidle")
            problems = page.evaluate(OVERFLOW_JS)
            if problems:
                failures.append(f"{persona} {path}: {problems}")
    assert not failures, "\n".join(failures)
