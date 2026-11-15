# AGENTS.md — Proxecto Eira

Plataforma libre (EUPL-1.2) de xestión, reserva e **acceso** a instalacións deportivas municipais
para concellos pequenos.

## Stack
- Python 3.12+ (venv con 3.13), **Django 5.2**, DRF + drf-spectacular (OpenAPI 3.1).
- Plantillas Django + **HTMX** (vendorizado en `static/vendor/`) + CSS propio (`static/css/eira.css`). Sen frameworks JS.
- PostgreSQL en Docker; **SQLite** en local se non hai `DATABASE_URL`.
- Tests: pytest + pytest-django; E2E con Playwright + axe-core (`tests/e2e/`).
- Lint/format: ruff.

## Comandos (Windows sen `make`: usa `python tools/tasks.py <orde>`, equivalente)
- `make dev` → migra, carga demo e arranca en http://127.0.0.1:8000
- `make seed` → datos de demostración ficticios (`manage.py seed_demo`)
- `make test` → pytest (unitarios e integración)
- `make e2e` → Playwright + axe (arranca un servidor propio)
- `make lint` → ruff
- `make licenses` → comproba que as dependencias teñen licenza compatible con EUPL-1.2
- `make i18n` → compila .po → .mo (con polib, sen gettext)
- `docker compose up` → app + Postgres con demo cargada
- Variables: ver `.env.example`. En local: `EIRA_DEBUG=1`.

## Estrutura
- `eira/` configuración, URLs (`urls.py`, `tenant_urls.py` para `/c/<slug>/`, `manage_urls.py` para `/c/<slug>/xestion/`), API (`api.py`).
- `apps/<módulo>/` tenants, accounts, facilities, bookings, access, maintenance, incidents, activities, notifications, analytics, integrations.
- Regras de negocio en `services.py` de cada app; as vistas só orquestran.
- Integracións externas SEMPRE detrás dun adaptador en `apps/integrations/` (seleccionado por `EIRA_ADAPTERS`), con implementación simulada.
- Ferramentas de demo en `/dev/…` (só con `EIRA_DEMO_TOOLS=1`): bandexa de correo, TPV, Cl@ve, simulador de pechadura.

## Convencións
- Cabeceira `# SPDX-License-Identifier: EUPL-1.2` en todo ficheiro de código.
- Código e nomes técnicos en inglés. **Cadeas da interface en galego como msgid** (galego = idioma por defecto e completo); castelán en `locale/es/`.
- Multi-concello: todo modelo de datos dun concello herda `TenantModel`; filtrar sempre por `municipality=request.tenant`. Nas vistas, `request.tenant` e `request.roles` veñen do `TenantMiddleware`.
- URLs do concello: `{% turl 'app:name' args %}` nas plantillas e `treverse(tenant, name, *args)` en Python.
- Permisos: `@role_required("admin", "region_admin")`; módulos opcionais: `@module_required("activities")`.
- CSP estrita: **nada de `<script>` nin `style=` en liña**. JS en `static/js/`, datos para JS con `json_script`.
- Accesibilidade WCAG 2.1 AA: campos con `includes/field.html`, foco visible, anuncios `aria-live` (`data-announce`) nos intercambios HTMX.
- Datos persoais mínimos. Nada de datos reais na demo; autoría «Equipo Eira».
