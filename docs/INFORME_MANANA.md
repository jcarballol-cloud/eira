# Informe de la sesión nocturna — Eira

**Fecha:** 23/10/2026 · **Rama:** `master` (git local, sin push) · **Estado:** P0–P5 cubiertos; queda pulido y verificación humana.


## v2. De prototipo a producto (23/10, tarde y noche)

**Servidor de demo:** <http://localhost:8000> · LAN `http://<IP do equipo>:8000`.
- Corre en una ventana de PowerShell independiente, titulada «Eira demo · 0.0.0.0:8000» (PID 39944), con `runserver --noreload` y la IA simulada; no se ha cargado Ollama ni ningún modelo.
- Los datos de demo se regeneraron justo antes de arrancar.
- Para pararlo, cierra la ventana.
- El servidor de la fase 1 (PID 38220) **ya no estaba en marcha** cuando fui a sustituirlo: el puerto 8000 no escuchaba y yo no lo paré. No sé cuándo cayó.

**Commits locales**, sin push: F0 `7f0eb4b`, F1 `c9ebfd0`, F3 `92670c0`, F5 `70a8a1f`, F2 `0737eb1`, F4 `a03dd10`, F7 `5086b15`, F8 `17cd0c3`, F6 `a786550`, más el de F9.

| Fase | Qué hay | Verificado |
|---|---|---|
| F0 | `docs/APRENDIZAXES.md` (solo patrones de AFS +50 y LifeGuarPro, sin datos ni recursos) y `docs/PLAN_V2.md` | ✅ revisado |
| F1 | Cada perfil con su herramienta: app móvil del vecindario y del operario, tableta del monitor, escritorio del ayuntamiento y de la diputación (consulta de solo lectura con aviso). Permisos reales en el backend, marco de dispositivo con `?marco=` | ✅ 65 tests de la matriz rol × URL (200/403) |
| F3 | Cobros: notificación firmada servidor a servidor (un rechazo nunca confirma), estados, bloqueo de 10 min, devoluciones, cobro en mostrador, conciliación CSV/ODS, tarifas por colectivo, descuento en franjas tranquilas, recibo PDF | ✅ 17 tests de cobros, E2E del pago |
| F5 | Mapa: el 403 se debía al Referer y ahora se envía solo el origen; servidor de teselas por ayuntamiento; política de OSM documentada | ✅ E2E: teselas con 200, sin violaciones de CSP (`docs/capturas/v2/mapa-teselas.png`) |
| F2 | Alta realista: «Solicitar la app» con padrón simulado → correo con enlace y código ligado a ese correo → instalación Android/iPhone → primera apertura (código ya relleno) → «¿Tienes hijos?». Alta en mostrador con hoja QR; el monitor apunta personas y el ayuntamiento las valida | ✅ 16 tests y E2E del flujo completo |
| F4 | 16 fotos de Wikimedia Commons con la licencia comprobada una a una (CC0/BY/BY-SA/PD), sin personas reconocibles ni marcas, WebP en 3 tamaños, `CREDITS.md` y `/creditos/`. Formulario de instalación con pestañas, accesibilidad con iconos, escala de esfuerzo de una persona en una persona con caras OMNI y Borg CR-10 | ✅ 5 tests de fotos (licencias, EXIF, variantes) y capturas antes/después |
| F7 | «¿Qué tal fue?» en el checklist; «Mal» crea una incidencia. Vista de valoraciones sin nombres. Observatorio con filtros, tablas y CSV/ODS (n ≥ 10). Comparativa de la diputación con tendencia y satisfacción; alta de ayuntamiento en 6 pasos con invitación | ✅ 7 + 3 tests y el vídeo |
| F8 | `docs/rxpd/` (matriz por perfil, RAT, textos modelo); centro de privacidad; menores de 14 (art. 7 LOPDGDD); iconos de cámara y filtro «sin fotos»; solo cookies técnicas; purga de solicitudes a los 12 meses | ✅ 10 tests (cookies, roles, consentimientos y purga) |
| F6 | Recomendaciones concretas dentro de cada reserva (hora para beber, cantidades según el peso, durante, sales, hiponatremia, energía, después, tiempo, edad y semana OMS), calculadas en el dispositivo; en la cuenta solo con consentimiento del art. 9 | ✅ 6 tests de privacidad y un E2E que comprueba que ninguna petición lleva el peso |
| F9 | Nuevo guion ([guion-demo.md](demo/guion-demo.md)); vídeos regrabados (108 s en móvil y 110 s en escritorio, con subtítulos), 25 capturas de pasos por viewport en `docs/capturas/v2/pitch-*` y 99 pantallas en `docs/capturas/v2/pantallas/` (móvil, tableta y escritorio); axe en 3 viewports; rendimiento ([rendemento.md](rendemento.md)); traducción al castellano completa | ✅ ver abajo |

**Números al cierre:** 298 tests unitarios y de integración, y 16 E2E (más los 2 de vídeo), todo en verde. axe 0 violaciones en **68 páginas × 3 viewports** (390, 820 y 1280 px). El castellano tiene 0 cadenas sin traducir ni dudosas.

**Hecho pero NO verificado o con límites:**
- **Rendimiento**: medido con `runserver` y SQLite en local, no en producción ni con red móvil. La comparativa de la diputación tardaba 218 ms y ahora tiene caché de 5 min.
- **Traducción al castellano**: se hizo con dos subagentes y se verificaron automáticamente los marcadores, el HTML y los plurales. Solo revisé a mano algunas cadenas, no las 571.
- **Instalación PWA**: el botón «Instalar ahora» depende de `beforeinstallprompt`, que no se ha probado en un Android real. En iPhone solo hay instrucciones, porque no existe una API para instalar.
- **Padrón y Redsys**: los adaptadores reales son esqueletos.
- **Fotos**: la licencia se verificó con los metadatos de la API de Commons. Antes de publicar, conviene que una persona revise visualmente las 16 fichas.
- La «diputación ve lo mismo que el ayuntamiento en solo lectura» queda **reflejado tal cual** en la matriz RGPD. Es una decisión que conviene revisar con el DPD.

**Decisiones para revisar:** todas están en `docs/DECISIONS.md`, secciones «v2 F*». Las más importantes:
- el motor de salud solo en JavaScript;
- las cantidades por peso solo para adultos;
- el filtro de fotos de la tableta, que es solo visual para no marcar ausencias.


## 0. Novedades de la sesión de mañana (23/10, tarde)

| Qué | Estado | Cómo se verificó |
|---|---|---|
| Servidor de demo en la LAN (`0.0.0.0:8000`, proceso independiente, IA fake) | ✅ verificado | HTTP 200 en `/` (perfiles) y en `/c/vilardeiras/` por `localhost` y por la IP LAN; entrar como Uxía por la IP LAN |
| Auditoría de publicación ([AUDITORIA_PUBLICACION.md](AUDITORIA_PUBLICACION.md)) | ✅ verificado | `git grep` + `git log --all -p -S` sin rutas, usuarios, IPs ni secretos; PNG sin metadatos; dominio de demo cambiado a `demo.eira.example`; cabeceras `.po` limpias. **No hace falta reescribir el historial** |
| `publiccode.yml` con el validador oficial | ✅ verificado (sin red) | `publiccode-parser` 5.4.3 en Docker: 0 errores y 0 avisos tras corregir versión, categoría y `repoOwner` obsoleto. Con red se validará la URL al publicar |
| Pipeline de la CI en local con PostgreSQL 16 | ✅ verificado | lint, licencias, SPDX, OpenAPI sin diferencias, 160 tests y 11 E2E con axe (0 violaciones) |
| Fallos reales que encontró la CI local | ✅ corregidos | El OpenAPI cambiaba con PostgreSQL (la CI habría fallado); se podían reservar franjas ya empezadas; `role="status"` rompía la lista de mensajes (axe) |
| Demo pública preparada (Caddy HTTPS, DEBUG off, regeneración nocturna) | ✅ verificado en local / ⬜ sin desplegar | [despregamento-demo.md](despregamento-demo.md): HTTPS con el certificado interno de Caddy, 308 de HTTP a HTTPS, HSTS, 33 páginas con 200, regeneración forzada a la hora actual y cargas simultáneas serializadas |
| RAM sin IA | ✅ medido | app 139 MiB (2 workers), PostgreSQL 52–59 MiB, Caddy 12–15 MiB → **≈ 210 MiB en reposo, ≈ 300 MiB en el pico nocturno**. VPS de 1 GB recomendado |
| Vídeo del guion del pitch | ✅ verificado | `docs/demo/eira-demo-movil.webm` y `eira-demo-escritorio.webm` (~88 s, subtítulos, pausas de 2,6–3,4 s), más capturas numeradas en `docs/demo/pasos-movil/` y `pasos-escritorio/` (22 cada una). Se revisaron fotogramas con ffmpeg. `python tools/tasks.py video` |
| Nombres ficticios | ✅ revisado | Ninguna coincidencia real en Vilardeiras, Pontedouro ni Deputación das Marismas (búsquedas web); las parroquias son topónimos genéricos (ver DECISIONS). No se consultó el Nomenclátor del IGE |

**Importante para el servidor de la fase 1:** arrancó con el código de antes de estos cambios y sin
recarga automática. Si se reinicia, hay que ejecutar antes `python tools/tasks.py seed`, porque los
perfiles de demo cambiaron de dominio. Para pararlo: `Stop-Process -Id 38220`.

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
| 160 tests unitarios/integración + 11 E2E | `python tools/tasks.py test` → todos pasan |
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
| IA autoalojada real: resumen semanal en gallego con **Ollama + qwen3:8b** (pesos abiertos) local, solo agregados | `manage.py ai_weekly_summary -v 2` con `EIRA_AI_ADAPTER=…OpenAICompatibleAdapter` (≈1 min en esta máquina); fallo del modelo no rompe el panel (test) |
| Exportación ODS de indicadores; fotos de incidencias privadas | `test_ods_export_is_valid_opendocument`, `test_incident_photos_are_private` |

## 3. Hecho pero NO verificado

- **CI de GitHub**: no se ha ejecutado en GitHub, pero su mismo pipeline pasa en local con PostgreSQL.
- **publiccode.yml**: validado sin red; queda la validación de la URL cuando el repositorio sea público.
- **Adaptadores reales** (Cl@ve SAML, Chave365 OIDC, Redsys, MeteoSIX, Telegram Bot API, Web Push VAPID, cerradura HTTP): solo esqueletos documentados; no funcionales.
- **Lectores de pantalla reales**, zoom 200/400 % y mapa Leaflet con teclado: no probados manualmente.
- **Service worker / caché de lectura** en móvil real (instalación de la PWA): no probado fuera de Chromium headless.
- **Subdominios reales con DNS/HTTPS**: probado solo con cabecera Host en tests.

## 4. Qué falta (por prioridad)

- **P1:** nada bloqueante. Mejoras: reservas recurrentes (clubes), lista de espera en franjas ocupadas.
- **P2:** cola offline guarda formularios pero no hay vista para revisar/descartar lo pendiente; firma/resincronización de hora del teclado solo documentada.
- **P3:** botón de activación de Web Push en la interfaz (solo existe el endpoint y el adaptador simulado); edición de baterías de pruebas desde la UI (hoy se crean en seed/admin).
- **P4:** validación DCAT-AP con validador oficial; ODS también en datos abiertos y exportación (hoy solo en indicadores).
- **P5:** ensayo cronometrado del pitch (el vídeo ya está hecho).

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
