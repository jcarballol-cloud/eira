# Progreso (rexistro vivo)

Última actualización: 2026-10-23 (sesión nocturna).

## Ferramentas da máquina
- Python 3.13 (venv) ✔ · Docker 29 ✔ (Docker Desktop arrancado durante a sesión) · Node 24 ✔ · Playwright + Chromium ✔
- **Non dispoñible:** `make`, GNU gettext → substitutos en `tools/` (ver DECISIONS).

## P0 — Esqueleto
- [x] Repositorio git, LICENSE (texto oficial EUPL-1.2), README (gl), CLAUDE.md, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, publiccode.yml (YAML válido; **non validado** con publiccode-parser, que non está dispoñible sen rede/Go)
- [x] Django modular con 11 apps en `apps/`
- [x] Docker Compose (app + PostgreSQL 16) — **verificado**: `docker compose up --build` carga a demo e serve as páxinas (200)
- [x] Makefile + `tools/tasks.py`, `.env.example`, CI (`.github/workflows/ci.yml`, só o ficheiro: **non executado** en GitHub)
- [x] Comprobación de licenzas (`make licenses`) — **verificado**: todas compatibles
- [x] Comprobación de cabeceiras SPDX (`tools/check_spdx.py`) — verificado
- [x] Sistema de deseño (paleta, foco visible, texto grande, alto contraste, movemento reducido)

## P1 — Mínimos das bases
- [x] Multi-concello por ruta, subdominio e dominio propio; illamento con tests
- [x] Consulta sen rexistro, filtros, mapa Leaflet + lista accesible, ficha, grella semanal
- [x] Reserva en 3 pasos con normas versionadas e pagamento simulado
- [x] Modificación e cancelación con regras e penalización
- [x] Historial, recibo, .ics, Google Calendar, avisos na aplicación
- [x] Acceso sen contrasinal (código ao correo, bandexa /dev/mailbox) e Cl@ve simulada
- [x] Concello: panel do día, alta asistida con plantillas (3 pasos), horarios, peches con aviso, tarifas, normas versionadas, reserva en nome dun veciño, indicadores con táboa e CSV
- [x] Alta de concello en 3 pasos desde a deputación
- [ ] i18n castelán completo (en curso)
- [ ] E2E Playwright + axe (pendente)

## P2 — Diferencial
- [x] Niveis de acceso 0–3, simulador de pechadura `/dev/lock-simulator`, tests de bordos
- [x] Checklist de peche → incidencia automática
- [x] Incidencias con foto (EXIF eliminado, límite de tamaño), validación → orde → resolución → aviso
- [x] Mantemento preventivo, xeración de ordes, calendario compartido
- [x] App do operario con cola sen conexión en IndexedDB (lóxica de servidor testada; **cola no navegador pendente de verificar con E2E**)
- [ ] docs/access/offline-codes.md

## P3–P5
- Pendente (ver INFORME_MANANA.md ao final da sesión).

## Bloqueos
- Ningún de momento.
