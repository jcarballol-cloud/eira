# Informe de la sesión nocturna — Eira

**Fecha:** 23/10/2026 · **Rama:** `master` (git local, sin push) · **Estado:** P0–P5 cubiertos; queda pulido y verificación humana.

## 1. Cómo arrancarlo

**Con Docker (verificado):**
```bash
docker compose up --build        # app + PostgreSQL 16 + datos de demo → http://localhost:8000
```

**Sin Docker (verificado en Windows):**
```bash
python -m venv .venv && .venv\Scripts\activate      # Linux/macOS: . .venv/bin/activate
pip install -r requirements-dev.txt
python tools/tasks.py dev       # = make dev: compila traducciones, migra, carga demo y arranca en :8000
```
Otras tareas: `python tools/tasks.py test | e2e | lint | licenses | seed | screenshots | openapi`
(el `Makefile` llama a lo mismo). Para E2E la primera vez: `python -m playwright install chromium`.

**Usuarios de demo** (botón «Entrar como…» en la portada; todo ficticio):

| Persona | Rol | Para enseñar |
|---|---|---|
| Uxía | vecina joven, móvil | reserva, código, simulador, checklist |
| Manuel | vecino mayor, texto grande | gimnasio, llave custodiada |
| Irene | no empadronada | tarifa distinta |
| Concello de Vilardeiras | admin | panel del día, alta asistida, indicadores |
| Brais | mantenimiento | órdenes, modo offline |
| Antía | monitora | tableta: asistencia, OMNI/Borg |
| Deputación das Marismas | region_admin | comparativa, alta de concello |

Herramientas simuladas: `/dev/mailbox/` (correo), `/dev/lock-simulator/` (cerradura), `/dev/tpv/…`, `/dev/clave/`, `/dev/saida/`.
Guion del pitch: [`docs/demo/guion-demo.md`](demo/guion-demo.md).

## 2. Hecho y verificado

| Qué | Cómo se verificó |
|---|---|
| 155 tests unitarios/integración + 11 E2E | `python tools/tasks.py test` → todos pasan |
| Aislamiento entre concellos (web, gestión, API, subdominio, dominio propio) | `apps/tenants/tests/test_isolation.py` |
| Permisos por rol (ciudadanía, admin, mantenimiento, monitor, diputación) | tests de aislamiento y de cada app |
| Reserva completa: grilla → normas versionadas → pago simulado → código → .ics → recibo → cancelación con reembolso | `test_full_booking_flow_through_views` + E2E `test_email_login_and_booking_with_offline_code` |
| Códigos sin conexión: bordes exactos de la ventana (±1 s), duración, otro secreto, propiedad con 300 reservas | `apps/access/tests/test_offline_codes.py` (30 casos) |
| Bloqueo exponencial (5/10/20 min) y aviso al concello tras 3 bloqueos | `test_exponential_lockout_and_alert` |
| Niveles 0–3: QR, custodio avisado por correo + entrega/devolución, apertura remota solo en ventana + luces hasta fin de franja | `test_access_levels.py` |
| Checklist «no» → incidencia → validación → orden → cierre → aviso «Arranxado» a quien informó | `test_full_cycle_notifies_reporter` + E2E `test_pitch_script` (= guion de demo) |
| Fotos: EXIF/GPS eliminados, límite de tamaño, ficheros falsos rechazados | `test_incidents.py` |
| Cola sin conexión del operario (IndexedDB) y sincronización al volver la red | E2E `test_operator_offline_queue_syncs` (Playwright offline) |
| Salud: los datos no salen del dispositivo | E2E `test_health_data_never_leaves_device` (inspecciona todas las peticiones) |
| Observatorio: umbral n≥10 (9 → oculto, 10 → visible), configurable, microdatos seudonimizados solo admin | `test_activities.py` |
| Escuelas: consentimientos de menores, edad, lista de espera y promoción, pago | `test_activities.py` |
| Tableta monitor: asistencia, RPE solo con consentimiento, carga sRPE×min | `test_monitor_tablet_flow` |
| Exportación íntegra ZIP (JSON+CSV+iCal+GeoJSON+ficheros) e importación con ida y vuelta | `test_portability.py` |
| Exportación y borrado de datos personales; consentimientos revocables con fecha | `test_accounts.py` |
| Login sin contraseña: código de un uso, HMAC, 5 intentos, rate limit, Cl@ve simulada, sin open redirect | `test_accounts.py` |
| **WCAG 2.1 A/AA: 0 violaciones axe en 53 páginas × móvil y escritorio** | E2E `test_accessibility.py` |
| Teclado: skip link, `lang`, anuncios aria-live con HTMX | E2E `test_flows.py` |
| CSP sin `unsafe-inline`, CSRF, cabeceras, sin JS/estilos en línea en plantillas | `test_security.py` |
| Gallego y castellano 100 % (1.200 cadenas), placeholders coherentes | `tests/unit/test_i18n.py` |
| OpenAPI 3.1 generado y validado | `manage.py spectacular --validate --fail-on-warn` |
| Licencias de dependencias compatibles con EUPL-1.2; SPDX en todos los ficheros | `tools/check_licenses.py`, `tools/check_spdx.py` |
| `docker compose up --build` con PostgreSQL y demo | arrancado y comprobadas 8 URLs (200) |
| 44 capturas (móvil y escritorio) | `docs/capturas/`, generadas con `tools/tasks.py screenshots` |
| ruff lint + format | sin errores |

## 3. Hecho pero NO verificado

- **CI de GitHub** (`.github/workflows/ci.yml`): escrito, nunca ejecutado (sin push por norma).
- **publiccode.yml**: YAML válido, pero no pasado por `publiccode-parser` (no disponible offline).
- **Adaptadores reales** (Cl@ve SAML, Chave365 OIDC, Redsys, MeteoSIX, Telegram Bot API, Web Push VAPID, cerradura HTTP): solo esqueletos documentados; no funcionales.
- **`OpenAICompatibleAdapter`**: código escrito, no probado contra un llama.cpp/Ollama real (sí el fake y el filtro de datos personales).
- **Lectores de pantalla reales**, zoom 200/400 % y mapa Leaflet con teclado: no probados manualmente.
- **Service worker / caché de lectura** en móvil real (instalación de la PWA): no probado fuera de Chromium headless.
- **Subdominios reales con DNS/HTTPS**: probado solo con cabecera Host en tests.

## 4. Qué falta (por prioridad)

- **P1:** nada bloqueante. Mejoras: reservas recurrentes (clubes), lista de espera en franjas ocupadas.
- **P2:** cola offline guarda formularios pero no hay vista para revisar/descartar lo pendiente; firma/resincronización de hora del teclado solo documentada.
- **P3:** botón de activación de Web Push en la interfaz (solo existe el endpoint y el adaptador simulado); edición de baterías de pruebas desde la UI (hoy se crean en seed/admin).
- **P4:** exportación ODS nativa (hoy CSV); validación DCAT-AP con validador oficial.
- **P5:** vídeo/GIF del recorrido; ensayo cronometrado del pitch.

## 5. Decisiones que conviene revisar

Todas en [`docs/DECISIONS.md`](DECISIONS.md). Las más discutibles:
1. **Cadenas de la interfaz con msgid en gallego** (no en inglés).
2. **Aislamiento por clave foránea** (no esquemas PostgreSQL por concello).
3. **Empadronamiento por código de invitación** del concello (sin acceso al padrón).
4. **Esquema de códigos offline** (HOTP, bloques de 30 min, ±10 min, 6 dígitos): leer el análisis de límites en [`docs/access/offline-codes.md`](access/offline-codes.md).
5. **Cierres cancelan y reembolsan** automáticamente (en vez de reubicar).
6. **No presentadas solo en niveles 1–3** (en pistas abiertas el QR es voluntario).
7. **Nombres ficticios**: Vilardeiras, Pontedouro, Deputación das Marismas (comprobar que no chocan con nada real o de otra candidatura).

## 6. Riesgos para la entrega del 18/11

- **Fuerza bruta en nivel 2** con 6 dígitos: mitigada (bloqueo exponencial + aviso), pero conviene presentar 8 dígitos como opción para instalaciones sensibles y explicarlo bien en la memoria.
- **Ficheros subidos**: las fotos de incidencias y órdenes ya se sirven con control de acceso (solo quien informó y el personal del concello; test). En producción el proxy debe servir directamente solo `media/facilities/` y `media/tenants/` y pasar el resto a la app.
- **Rate limit en caché local**: con varios procesos gunicorn necesita caché compartida (`EIRA_CACHE_DIR` ya configurado en compose).
- **Datos de demo dependen de la hora**: el seed crea reservas alrededor de la hora actual; re-ejecutar `make seed` justo antes del pitch.
- **Tiles de OpenStreetMap**: único recurso externo; sin red, usar la vista de lista. Revisar la política de uso de OSM para producción.
- **Volumen de la memoria (10 páginas)**: hay mucha funcionalidad; priorizar el relato «de la reserva a la puerta».

## 7. Siguientes 5 pasos recomendados

1. **Revisar y ensayar la demo** con `docs/demo/guion-demo.md` (3 min) y las capturas; decidir si se enseña el modo offline en directo.
2. **Revisión humana de accesibilidad** con NVDA/TalkBack y una persona mayor real (perfil de Manuel); anotar en `docs/accesibilidade/informe-probas.md`.
3. **Publicar el repositorio** (tras revisión) para activar la CI y validar `publiccode.yml`; elegir URL definitiva.
4. **Redactar la memoria técnica** apoyándose en `docs/arquitectura/`, `offline-codes.md`, `seguridade-rxpd.md` e `interoperabilidade.md`.
5. **Implementar un adaptador real de bajo riesgo** (SMTP o MeteoSIX con clave gratuita) para demostrar que los adaptadores no son humo.
