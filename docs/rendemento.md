<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Rendemento (comprobación v2, 23/10/2026)

**Como se mediu:** Playwright (Chromium) cun viewport de móbil de 390 × 844, contra o servidor de desenvolvemento (`runserver`, `DEBUG`, SQLite e datos de demo: 2 concellos e ~7.800 reservas) na mesma máquina, sen latencia de rede. Mediana de 3 cargas despois dunha de quentamento. Script: `tools/perf.py`.

**Isto non é produción.** Con gunicorn e PostgreSQL o servidor adoita ir máis rápido, pero unha rede móbil real engade latencia. Os valores serven para comparar páxinas entre si e para detectar regresións.

| Páxina | Resposta do servidor (ms) | DOMContentLoaded (ms) | load (ms) | Peticións | Transferido con caché (KB) |
|---|---:|---:|---:|---:|---:|
| Portada do concello (lista con fotos) | 12 | 24 | 30 | 13 | 15 |
| Mapa | 13 | 35 | 39 | 22 | 17 |
| Inicio da app | 18 | 27 | 30 | 7 | 7 |
| Ficha con grella semanal | 38 | 50 | 55 | 8 | 40 |
| Panel do día (concello) | 35 | 48 | 56 | 7 | 28 |
| Indicadores | 46 | 58 | 64 | 7 | 24 |
| Valoracións | 34 | 46 | 52 | 7 | 19 |
| Observatorio (12 semanas) | 43 | 54 | 59 | 7 | 17 |
| Rede da deputación | 218 → **16** con caché de 5 min | — | — | 6 | 12 |

**Primeira visita sen caché (portada):** 256 KB en total, contando CSS, JS, iconas, logotipo e as fotos WebP de 960 px que entran na pantalla. As demais fotos cárganse con `loading="lazy"`.

## Medidas
- Fotos WebP con `srcset` (480/960/1440 px) e `loading="lazy"`.
- Leaflet só se carga na vista de mapa. HTMX e `eira.js` son os únicos scripts globais, e a saúde só se carga onde fai falta.
- Sen fontes web: úsase a tipografía do sistema.
- Ficheiros estáticos comprimidos e con hash (WhiteNoise), con caché longa.
- A comparativa da deputación gárdase 5 minutos en caché (`eira:region-compare:*`): calcula dous períodos por concello e, sen caché, crecería co tamaño da rede.

## Pendente / riscos
- Os indicadores calcúlanse ao voo. Para deputacións con moitos concellos convén unha táboa agregada diaria (pendente).
- Non se mediu con PostgreSQL nin con rede móbil simulada.

## Reproducir
`python tools/perf.py <id da pista de pádel> http://127.0.0.1:8000` cun servidor con datos de demo. Percorre estas páxinas cos perfís da demo e le `performance.getEntriesByType("navigation")`.
