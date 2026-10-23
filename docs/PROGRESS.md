# Progreso (rexistro vivo)

Última actualización: 2026-10-23, fin da sesión nocturna.

## Ferramentas da máquina
- Python 3.13 (venv) ✔ · Docker 29 ✔ (arrancouse Docker Desktop durante a sesión) · Node 24 ✔ · Playwright + Chromium ✔
- **Non dispoñibles:** `make`, GNU gettext → substitutos en `tools/` (ver DECISIONS). `makemessages` execútase no contedor.

## Estado por prioridade

Lenda: ✅ feito e verificado (test ou comprobación) · 🟡 feito sen verificar · ⬜ pendente

### P0 — Esqueleto
- ✅ Repositorio, LICENSE (EUPL-1.2 oficial), README (gl), CLAUDE.md, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY
- ✅ publiccode.yml validado con publiccode-parser 5.4.3 (sen rede)
- ✅ 11 apps en `apps/`, configuración por variables de contorno, sen segredos
- ✅ `docker compose up --build` (app + PostgreSQL 16 + demo) — comprobado con peticións HTTP 200
- ✅ Makefile + `tools/tasks.py` (equivalente en Windows), `make licenses`, comprobación SPDX
- ✅ Pipeline da CI executado en local con PostgreSQL (non executado en GitHub: sen push)
- ✅ Sistema de deseño accesible (paleta, foco, texto grande, alto contraste, movemento reducido)

### P1 — Mínimos das bases — ✅ completo
Multi-concello (ruta, subdominio, dominio propio, illamento testado), consulta sen rexistro con
filtros e mapa + lista, ficha, grella semanal (libre/ocupada/recomendada), reserva en 3 pasos con
normas versionadas e pago simulado, cambio e cancelación con penalización, historial, recibos, .ics,
Google Calendar, avisos, acceso sen contrasinal + Cl@ve simulada, panel do día, alta asistida con
plantillas, horarios/peches con aviso, tarifas, normas versionadas, reserva en nome dun veciño,
indicadores con táboa e CSV, alta de concello en 3 pasos, galego e castelán completos.

### P2 — Diferencial — ✅ completo
Niveis de acceso 0–3, códigos sen conexión con documento técnico e bloqueo exponencial, simulador
de pechadura, checklist de peche → incidencia, incidencias con foto sen EXIF, mantemento preventivo,
calendario, app do operario con cola sen conexión (verificada en E2E con Playwright offline).

### P3 — Valor engadido — ✅ case completo
- ✅ Escolas: oferta, prazas, cota, lista de espera, inscrición de menores con consentimentos, pago
- ✅ Modo tableta: asistencia con nomes grandes, OMNI/Borg pictográfica, carga sRPE, probas (ALPHA-Fitness e SFT só nomes)
- ✅ Observatorio anónimo con umbral configurable (tests 9/10), seudonimización, referencia OMS
- ✅ Meteoroloxía simulada na reserva, alertas que pechan e avisan, esqueleto MeteoSIX
- ✅ Saúde no dispositivo (test E2E de rede), fontes documentadas
- ✅ Recomendación horaria
- ⬜ Push real (só adaptador simulado e endpoint de subscrición; sen botón na interface)

### P4 — Soberanía — ✅
Exportación/importación íntegra con test de ida e volta, exportación e borrado de datos persoais,
datos abertos CSV + DCAT-AP, asistente IA (fake + OpenAI-compatible local, só agregados),
declaración de accesibilidade e privacidade modelo, vista de deputación.

### P5 — Demostración — ✅
Datos ficticios (Vilardeiras, Pontedouro, Deputación das Marismas), selector de 7 perfís,
guión de 3 min verificado cun test E2E, 44 capturas automáticas en `docs/capturas/`.

## Mañá do 23/10
- ✅ Auditoría de publicación, demo pública preparada (Caddy) con RAM medida, vídeo do pitch, revisión de nomes.

## Números
- 160 tests unitarios/integración + 11 E2E (axe en 53 páxinas × 2 viewports con 0 violacións).

## Bloqueos
- Ningún bloqueo activo. Ver riscos en `INFORME_MANANA.md`.
