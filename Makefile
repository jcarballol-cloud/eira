# SPDX-License-Identifier: EUPL-1.2
# Atallos de desenvolvemento. En Windows sen make: python tools/tasks.py <orde>
PY ?= python

.PHONY: dev seed test e2e e2e-pg lint licenses i18n openapi screenshots up

dev:         ## Migra, carga a demo e arranca o servidor en http://127.0.0.1:8000
	$(PY) tools/tasks.py dev
seed:        ## Datos de demostración ficticios
	$(PY) tools/tasks.py seed
test:        ## Tests unitarios e de integración
	$(PY) tools/tasks.py test
e2e:         ## Tests E2E con Playwright + axe-core
	$(PY) tools/tasks.py e2e
e2e-pg:      ## Os mesmos E2E contra PostgreSQL en Docker, coma na CI
	$(PY) tools/tasks.py e2e_pg
lint:        ## ruff
	$(PY) tools/tasks.py lint
licenses:    ## Comproba licenzas das dependencias (compatibles con EUPL-1.2)
	$(PY) tools/tasks.py licenses
i18n:        ## Compila as traducións .po → .mo
	$(PY) tools/tasks.py i18n
openapi:     ## Xera e valida docs/api/openapi.yaml
	$(PY) tools/tasks.py openapi
screenshots: ## Capturas automáticas en docs/capturas/
	$(PY) tools/tasks.py screenshots
up:          ## Todo en Docker (app + PostgreSQL)
	docker compose up --build
