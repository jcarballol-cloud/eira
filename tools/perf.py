# SPDX-License-Identifier: EUPL-1.2
"""Medición de rendemento de páxinas clave contra un servidor con datos de demo.

Uso: python tools/perf.py <id da pista de pádel de Vilardeiras> [URL base].
Mide: tempo de resposta do HTML (servidor), DOMContentLoaded, load, nº de peticións e bytes."""

import json
import statistics
import sys

from playwright.sync_api import sync_playwright

B = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8000"
PAGES = [
    (None, "/c/vilardeiras/", "Portada do concello (lista con fotos)"),
    (None, "/c/vilardeiras/?vista=mapa", "Mapa"),
    ("uxia@demo.eira.example", "/c/vilardeiras/app/", "Inicio da app"),
    ("uxia@demo.eira.example", "FAC", "Ficha con grella semanal"),
    ("admin@vilardeiras.demo.eira.example", "/c/vilardeiras/xestion/", "Panel do día"),
    ("admin@vilardeiras.demo.eira.example", "/c/vilardeiras/xestion/indicadores/", "Indicadores"),
    ("admin@vilardeiras.demo.eira.example", "/c/vilardeiras/xestion/valoracions/", "Valoracións"),
    (
        "admin@vilardeiras.demo.eira.example",
        "/c/vilardeiras/actividades/observatorio/?semanas=12",
        "Observatorio",
    ),
    ("deputacion@demo.eira.example", "/rexion/marismas/", "Rede da deputación"),
]


def login(pg, email):
    pg.goto(B + "/")
    pg.locator(f"form:has(input[value='{email}']) button").click()
    pg.wait_for_load_state("networkidle")


rows = []
fac = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch()
    for who, url, label in PAGES:
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        pg = ctx.new_page()
        if who:
            login(pg, who)
        url = url.replace("FAC", f"/c/vilardeiras/instalacions/{fac}/")
        samples = []
        for i in range(4):
            pg.goto(B + url, wait_until="load")
            pg.wait_for_load_state("networkidle")
            t = pg.evaluate("""() => { const n = performance.getEntriesByType('navigation')[0];
              return {ttfb: n.responseStart - n.requestStart, dcl: n.domContentLoadedEventEnd, load: n.loadEventEnd,
                      html: n.transferSize || n.encodedBodySize,
                      res: performance.getEntriesByType('resource').reduce((a, r) => a + (r.transferSize || 0), 0),
                      n: performance.getEntriesByType('resource').length + 1}; }""")
            if i:  # a primeira carga quenta a caché
                samples.append(t)

        def med(k, samples=samples):
            return statistics.median(s[k] for s in samples)

        rows.append(
            {
                "label": label,
                "url": url,
                "ttfb": round(med("ttfb")),
                "dcl": round(med("dcl")),
                "load": round(med("load")),
                "kb": round((samples[0]["html"] + samples[0]["res"]) / 1024),
                "n": samples[0]["n"],
            }
        )
        ctx.close()
    # Primeira visita sen caché (portada)
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    pg = ctx.new_page()
    pg.goto(B + "/c/vilardeiras/", wait_until="load")
    pg.wait_for_load_state("networkidle")
    cold = pg.evaluate("""() => performance.getEntriesByType('resource').reduce((a, r) => a + (r.transferSize || 0), 0)
                          + performance.getEntriesByType('navigation')[0].transferSize""")
    rows.append(
        {
            "label": "Portada, primeira visita sen caché",
            "url": "/c/vilardeiras/",
            "ttfb": None,
            "dcl": None,
            "load": None,
            "kb": round(cold / 1024),
            "n": None,
        }
    )
    b.close()
print(json.dumps(rows, ensure_ascii=False, indent=1))
