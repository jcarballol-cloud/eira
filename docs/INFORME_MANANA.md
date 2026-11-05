# Informe de la sesión nocturna — Eira

**Fecha:** 23/10/2026 (última actualización: 05/11/2026, v1.5) · **Rama:** `master` (git local, sin push) · **Estado:** P0–P5 cubiertos; queda pulido y verificación humana.

> **Capturas:** las rutas `docs/capturas/v…/` citadas aquí son de las capturas completas, que no están en el repositorio: se publicarán en el adjunto `capturas-v1.4.zip` de la versión **v1.4-certame** (ver [capturas/README.md](capturas/README.md)). En el repositorio quedan las 6 capturas clave del README.


## v1.5. Versión definitiva para la entrega (05/11) · etiqueta `v1.5-certame`

**Servidor:** `0.0.0.0:8000`, `EIRA_DEBUG=1`, con la demo regenerada. Última tanda de funcionalidades: a partir de aquí solo se corrigen errores.

### Cifras finales

| Comprobación | Resultado |
|---|---|
| Tests unitarios y de integración | **954 en verde** |
| E2E (Playwright) | **89 en verde**, 10 de vídeo excluidos (31 min) |
| Páginas axe, tema claro | **522 sin violaciones** (174 pantallas en móvil, tableta y escritorio) |
| Páginas axe, tema oscuro | **81 sin violaciones** |
| Recorrido automático por perfil | 72 pantallas: sin sesión y 6 perfiles (el DPD no tiene perfil en la demo; sus pantallas están en los tests) ([lista](REVISION_V1.5.md)) |
| RAM sin IA | **≈ 296 MiB** tras 100 peticiones (app 193, PostgreSQL 100, avisos 3), con `docker compose` |
| Vídeo anexo | **73 s**, con «Escoitar» y el mapa de procedencia (máximo 75 s) |
| Pitch | Sin cambios. Se regrabó aparte para comprobar el guion (pasa, 136 s) y se restauró el original |
| Lint, licencias y SPDX | ✅ |

### Qué hay y dónde

| Bloque | Dónde | Verificado |
|---|---|---|
| Paso 0 · `a460ae9` | Notas en los documentos; el README de capturas, en `Eira-release/ferramentas/` | ✅ |
| F · LEEME | `LEEME.md`, `LEEME.es.md`, README y «?» de la administración (`/axuda/leeme/`) | ✅ `test_leeme` |
| E · Acreditación con menores | Xestión → Máis ferramentas → Acreditacións (menores); ficha del grupo; `docs/rxpd/acreditacion-menores.md` | ✅ `test_accreditation` y E2E |
| B · Alerta en todos los perfiles | Cabecera de mantenimiento, limpieza, monitora y administración; aviso al personal de servicio; DESA y ubicación para el 112 | ✅ `test_alert_profiles` y E2E. ⚠️ Canales simulados |
| D · Documentos legales | Deputación → Documentos legais; Xestión → Documentos legais; app `/legal/`; «A miña conta → Documentos aceptados»; `docs/legal/modelos/` | ✅ `test_legal` y E2E |
| A · «Escoitar» | Inicio, ficha, código, avisos, consejos y protocolo; ajustes en Preferencias | ✅ con voz **simulada**. ❌ Sin probar con voz real ni con TalkBack/VoiceOver |
| C · Procedencia | Xestión → Procedencia; Deputación → Mobilidade; app → Concellos próximos; CSV y GeoJSON | ✅ `test_provenance` y E2E |
| G · Demo | `apps/tenants/demo_v15.py`: flujos sobre y bajo el umbral, documentos en varias versiones, Sabela pendiente, Xián con la revisión vencida, alertas de mantenimiento y limpieza | ✅ |

### Decisiones que conviene revisar

Están en `DECISIONS.md`. Las que más cambian el resultado:

- **Procedencia:** `n` son personas distintas, no reservas, y solo hay periodos de 30, 90 y 365 días, sin fechas libres. Es más protector que lo pedido.
- **Documentos legales:** no bloquean el uso; un aviso permanente lleva a los pendientes.
- **Acreditación vencida:** bloquea asignaciones nuevas, pero no deshace las existentes. Tampoco las anteriores a la v1.5; la ficha del grupo muestra el aviso.
- **«Sesión activa» en las alertas:** sesión abierta (monitora), orden en curso (mantenimiento y limpieza) o registro de limpieza en las últimas 2 h. El conserje es un responsable ligado a una instalación.

### Sin verificar o con límites conocidos

- **Lectores de pantalla y voz real:** «Escoitar» no se ha probado en dispositivos reales.
- **El recorrido por perfil es automático:** no sustituye el manual de una persona.
- **Comparar fechas en Procedencia:** puede dejar ver variaciones pequeñas de un flujo visible. Debe valorarlo el DPD en la EIPD.
- **Importación:** la portabilidad exporta los datos nuevos (`v15.json`), pero aún no los importa. Está en `PLAN_V2.md`.
- **Validez legal:** ningún modelo es un documento legal válido.
- **Corregido de paso:** la cabecera de gestión desbordaba en móvil y el calendario tenía poco contraste en tema oscuro, en los días de otro mes.

## v1.4. Copia limpia para publicar (sin publicar) (27/10) · etiqueta `v1.4-certame`

**Servidor:** <http://localhost:8000> y en la LAN (`0.0.0.0:8000`, `EIRA_DEBUG=1`), con las migraciones nuevas y los datos regenerados. Commits locales, **sin push** y sin crear repositorios remotos. **Este repositorio y su `origin` no se han reescrito.** Decisiones en `DECISIONS.md` (v1.4).

### Qué hay y dónde

| Bloque | Dónde | Verificado |
|---|---|---|
| A1 · Plazo de conservación del registro de auditoría | Xestión → Configuración → «Seguridade das contas e rexistro de auditoría» (`audit_retention_months`: 24 meses por defecto, 12–120). Purga en `booking_maintenance`; cada purga queda como `audit.purge`. La página del registro muestra el plazo | ✅ 9 tests (por concello, entradas sin concello, comando, límites, formulario, aviso) |
| A2 · Secreto TOTP cifrado en reposo | `apps/accounts/secretbox.py`: Fernet (`cryptography`), clave `EIRA_TOTP_KEY` o derivada de `EIRA_SECRET_KEY` con HKDF; migración `accounts/0012_v1_4` que cifra los existentes; comando `rotate_totp_key`. Documentado en `docs/seguridade-rxpd.md`, EIPD, RAT (fila 13) y matriz | ✅ 8 tests (cifrado en BD, migración de ida y vuelta, rotación a la clave propia, clave cambiada sin error, valor alterado rechazado) |
| A3 · Demo | Apellido común de la lista ficticia → «Calvo». El dominio de demo antiguo ya no aparece ni en el código ni en la documentación | ✅ `git grep` vacío |
| B · Copia pública | Carpeta `Eira-publico` (al lado de este repositorio), sin remoto. Se genera con un script en `Eira-release/ferramentas/` | ✅ ver abajo |
| B · Capturas | `Eira-release/capturas-v1.4.zip` (615 PNG + 1 README, 100 MB) para subir como adjunto de la release. En la copia: `docs/capturas/README.md` y **6 capturas clave rehechas con la demo v1.4** (19–87 KB), mostradas en el README («Como se ve») | ✅ revisadas a ojo una a una |
| B · Auditoría de la copia | `Eira-release/auditoria-copia-publica.md` | ✅ |

### Tamaño antes y después

| | Este repositorio (privado) | Copia pública |
|---|---|---|
| `.git` en disco | **385 MB** (pack de 330 MB) | **≈ 32 MB** (pack de 31 MB) |
| Commits | 69 | 70 (los mismos reescritos + 1 de publicación) |
| Objetos PNG en el historial | 1 905 | 235 (fotos, iconos, ilustraciones y las 6 capturas clave) |

### Qué se eliminó del historial (solo en la copia)

- **`docs/capturas/` completo**, en todos los commits (todas las versiones de cada captura). Van en el zip de la release.
- **Binarios > 5 MB:** fuera de las capturas **no había ninguno** (el mayor, 2,4 MB, en `assets-originais/`). Se aplicó igualmente `--strip-blobs-bigger-than 5M`; no quitó nada más.
- **Sustituciones de texto** en todos los ficheros de todos los commits, en los mensajes de commit y en las anotaciones de las etiquetas:
  - el dominio de demo antiguo → `demo.eira.example`;
  - el nombre de pila de la persona que hizo las propuestas de la v1.2 → «o equipo», con la concordancia de cada frase («Aportacións do equipo», «Propuesta del equipo»…);
  - **además de lo pedido:** el apellido común de la demo → «Calvo» (si no, seguiría en las versiones antiguas de `apps/activities/demo.py`). Se puede quitar del fichero de sustituciones y regenerar.
- Los **hashes de los commits cambian**; la correspondencia antiguo → nuevo está en `Eira-release/correspondencia-commits.txt`. Los documentos que citan commits citan los de este repositorio.

### Cifras

- **Tests unitarios e integración:** **841** en verde aquí y **841** en la copia (eran 822; +19 de la v1.4).
- **E2E:** **69** en verde aquí (Playwright + axe, sobre una copia exacta del commit, 23 min). En la copia pública se repiten después de generarla: resultado en `Eira-release/auditoria-copia-publica.md`.
- **axe (WCAG 2.1 AA):** las mismas 151 páginas × 3 tamaños y 65 en tema oscuro, **0 violaciones**; la página del registro y la de configuración (con el campo nuevo) ya estaban en la lista.
- **Castellano:** 100 % (5 cadenas nuevas).
- **En la copia:** `publiccode.yml` válido (validador oficial sin red, salida 0); **0 ficheros de código sin cabecera SPDX** (`tools/check_spdx.py`); licencias de las dependencias compatibles con la EUPL-1.2, incluida `cryptography` (`tools/check_licenses.py`); `git fsck` sin errores; 0 apariciones del dominio antiguo, del nombre ni del apellido en ficheros, mensajes y etiquetas; 0 blobs > 5 MB; 69 commits con autoría «Equipo Eira».

### Comandos para publicar (NO ejecutados)

Desde la carpeta de la copia pública (`Eira-publico`, al lado de este repositorio), con Git Bash y la CLI de GitHub (`gh`) autenticada. Cambia `ORGANIZACION` por la organización donde vaya a vivir el proyecto (mejor que una cuenta personal):

```bash
cd ../Eira-publico
git status                      # limpio, rama master, sin remotos (git remote → nada)

# 1. Crear el repositorio público vacío (sin README ni licencia: ya están en la copia)
gh repo create ORGANIZACION/eira --public \
  --description "Eira · Software libre para a xestión deportiva municipal"

# 2. Subir la rama y las etiquetas
git remote add origin https://github.com/ORGANIZACION/eira.git
git push -u origin master
git push origin --tags

# 3. Crear la release v1.4-certame con las capturas como adjunto
gh release create v1.4-certame ../Eira-release/capturas-v1.4.zip \
  --repo ORGANIZACION/eira --title "Eira v1.4 (certame)" \
  --notes-file ../Eira-release/notas-v1.4.md
```

Después de publicar: poner la URL definitiva en `publiccode.yml` (`url`) y en el README, y validar **con red** (`python tools/tasks.py publiccode` sin `-no-network`). **No** añadas el `origin` antiguo a la copia ni hagas push de este repositorio al nuevo. Los mismos comandos, con rutas absolutas, están en `Eira-release/PUBLICAR.md`.

### NO verificado o con límites

- **Contenido de las 615 capturas del zip:** son las del último commit, tal cual. No se ha comprobado (no hay OCR) si alguna muestra el apellido antiguo de la lista ficticia; el dominio antiguo no debería salir (se regeneraron después del cambio de dominio), pero tampoco se ha comprobado imagen por imagen. Para tenerlas al día: regenerarlas con `tools/tasks.py screenshots` y los `test_screenshots_*.py` y rehacer el zip.
- **Visibilidad del `origin` antiguo:** no se consultó la red. Si es público, el historial anterior al 24/10 (con el dominio antiguo y el apellido) sigue visible ahí: conviene ponerlo privado (`gh repo view <cuenta>/<repo> --json visibility`).
- **El cifrado TOTP no protege** si alguien tiene a la vez la base de datos y la clave (el servidor en ejecución): protege copias de seguridad y volcados. Sin `EIRA_TOTP_KEY` la clave sale de `EIRA_SECRET_KEY`, y una copia del `.env` bastaría.
- **No se ha probado con una app TOTP real** (como en la v1.3).
- `publiccode.yml` **con red**, la URL definitiva y la página de la release: pendientes de que exista el repositorio.
- El registro de auditoría sigue **sin protección contra quien tenga acceso directo a la base de datos** (no hay encadenamiento de hashes).

## v1.3. Documentación para la adopción y preparación para publicar (27/10) · etiqueta `v1.3-certame`

**Servidor:** <http://localhost:8000> y en la LAN (`0.0.0.0:8000`, `EIRA_DEBUG=1`), con los datos regenerados. Commits locales, **sin push**. Concellos ficticios de siempre. Regla: solo se añade (decisiones en `DECISIONS.md`, sección v1.3).

### Qué hay y dónde

| Bloque | Dónde | Verificado |
|---|---|---|
| A · Modelo de ordenanza (precio público + variante de tasa), gl y es | `docs/concello/ordenanza-modelo.md`. Cada artículo con su campo de Eira entre corchetes; tabla de correspondencia; aviso de informe jurídico y de Intervención al principio | ✅ campos y menús comprobados contra el código. ❌ citas legales sin contrastar con el BOE consolidado |
| A · Descuento de baja demanda editable | Xestión → Configuración → Regras de reserva (antes solo en el admin técnico) | ✅ tests de configuración |
| B · Plantilla de EIPD | `docs/rxpd/eipd-plantilla.md` (descripción, necesidad y proporcionalidad, 12 riesgos con medidas reales y tests, riesgo residual, plan de acción, opinión del DPD) | ✅ cada medida citada existe y tiene test. ❌ la valoración del riesgo es una propuesta, sin revisar por un DPD |
| B · Enlaces | «Quen custodia os teus datos» → tarjeta «Datos con máis risco» → resumen en la app (`/privacidade/avaliacion-impacto/`); `docs/rxpd/matriz.md` → plantilla | ✅ test + E2E |
| C · Doble factor TOTP | A miña conta → Seguridade da conta (QR, clave, 10 códigos de recuperación); segundo paso al entrar; obligatorio por concello (Configuración → Seguridade das contas de xestión) y por diputación (admin técnico); restablecer desde Persoal e códigos | ✅ 15 tests + E2E completo (activar, salir, entrar con código de recuperación, auditoría) |
| C · Registro de auditoría | Xestión → Máis ferramentas → Rexistro de auditoría (también en el menú del DPD): 7 categorías, fechas, CSV | ✅ 14 tests + E2E (permisos, diputación con soporte → 403, descargas registradas) |
| C · Documentación | `docs/seguridade-rxpd.md` (qué había, qué se añadió, límites) | ✅ |
| D · Auditoría del historial | `docs/AUDITORIA_PUBLICACION.md`, primera sección | ✅ ver abajo |
| D · README, publiccode.yml, GOVERNANCE.md | README: «A demo en 5 minutos», licencia y contribuciones; `publiccode.yml` validado; `GOVERNANCE.md` (gl + es) | ✅ validador oficial |

### Resultado de la auditoría del historial (no se reescribió nada)

Se revisaron **los 65 commits de todas las referencias** (`master`, `origin/master`, las tres etiquetas), línea a línea (`git log --all -p`), los nombres de todos los archivos que existieron, los mensajes y las anotaciones de las etiquetas.

- **Sin secretos** (solo `"proba-non-real"` en un test), **sin documentos ajenos** (ningún `.docx`/`.pdf`/… en toda la historia; la carta de interés de un concello que está en la carpeta **nunca se versionó** y ahora `.gitignore` ignora `*.docx`, `*.doc`, `*.odt` y `*.pdf`), **sin rutas locales reales**, **sin correos reales**, autoría siempre «Equipo Eira», 674 PNG sin metadatos.
- **Para decidir** (propuesta de limpieza en el documento, no ejecutada):
  1. Correos ficticios del subdominio `demo` de `eira.gal` (dominio que podría ser de un tercero) en los commits `ca22205` → `41a3f1b` (`seed_demo.py`, `apps/integrations/demo.py`, `tests/e2e/test_screenshots.py`…). Propuesta: `git filter-repo --replace-text` a `demo.eira.example`.
  2. Un nombre de pila en `bf6b51d` y `db4a681` (`DECISIONS.md`, `INFORME_MANANA.md`, `PLAN_V2.md`, `PROGRESS.md`, mensaje de `db4a681` y anotación de `v1.2-certame`). Confirmar que está de acuerdo; esos commits **aún no están en `origin`**.
  3. Un apellido gallego común en la lista de apellidos ficticios de la demo (`a51fe58`, `apps/activities/demo.py`): no identifica a nadie; se señala por prudencia.
  4. Tamaño: ~330 MB de *pack* por las capturas regeneradas (616 PNG, 109 MB en el árbol actual). Propuesta: *release assets* o LFS y un historial nuevo, o aceptarlo.
- **Remoto ya configurado:** `origin` apunta a una cuenta personal de GitHub y `origin/master` está en `5181c06` (24/10): el historial hasta ahí **ya se subió** fuera de esta sesión (incluye los puntos 1 y 3). No consulté la red: **no sé si ese repositorio es público**.

### Cifras

- **Tests unitarios e integración:** 822 en verde (eran 788).
- **E2E:** 69 en verde (eran 65; +4 de la v1.3).
- **axe (WCAG 2.1 AA):** 151 páginas × 3 tamaños y 65 en tema oscuro, **0 violaciones**; además, 7 comprobaciones axe dentro del E2E del doble factor (5 en claro y 2 en oscuro: configuración, QR, códigos, segundo paso).
- **Sin scroll horizontal** (360 y 390 px, texto normal y grande), también en las pantallas nuevas.
- **Castellano:** 100 % (174 cadenas nuevas).
- **publiccode.yml:** válido con `publiccode-parser-go` 5.4.3 sin red (salida 0; control negativo con un campo inventado → salida 1).
- **Corrección encontrada por el camino:** la demo v1.2 creaba el ejemplo de «cierre sin confirmar» solo si, por azar, había una reserva usada ayer en el pabellón; hoy no la había y fallaba la prueba axe (4 E2E). Ahora la demo la crea si falta.
- **Capturas:** no se hicieron nuevas (no se pedían y engordarían el historial, ver punto 4).

### NO verificado o con límites

- **Citas legales** de la ordenanza (TRLRHL, LBRL, LGT, Ley 40/2015): revisadas de memoria, sin el BOE consolidado. El propio modelo exige informe jurídico y de Intervención.
- **EIPD:** la valoración de riesgos es una propuesta; falta la opinión del DPD.
- **Doble factor:** probado con `pyotp` (que implementa la RFC 6238) y el vector oficial de la RFC; **no con una app real** de móvil (FreeOTP, Aegis…), aunque usa los parámetros estándar.
- El **secreto TOTP** se guarda sin cifrado adicional en la base de datos (riesgo anotado en la EIPD). No hay WebAuthn.
- El **registro de auditoría** no tiene plazo de conservación ni protección contra quien tenga acceso directo a la base de datos.
- **Repositorio remoto:** visibilidad y etiquetas sin consultar. Validación de `publiccode.yml` **con red**, pendiente de la URL definitiva.
- **Traducciones al castellano:** sin revisión externa.

## v1.2. Aportaciones del equipo: uso diario, seguridad y rendimiento (27/10) · etiqueta `v1.2-certame`

**Servidor:** <http://localhost:8000> y en la LAN (`0.0.0.0:8000`, `EIRA_DEBUG=1`), con los datos regenerados justo antes de arrancar. Commits locales, sin push. Los concellos siguen siendo los ficticios (Vilardeiras, Pontedouro, Deputación das Marismas).

**Regla:** solo se añade. Nada existente se quitó ni se hizo menos visible (salud, consejos, observatorio, «Que tal foi?», tableta, avisos, Telegram, limpieza, «Incidencia ou seguridade»…). Choques en `DECISIONS.md`, sección v1.2. **Se hicieron los ocho bloques (A–H) y el cierre (I)**; nada queda a medias en la interfaz. Lo pendiente está como hoja de ruta en `docs/PLAN_V2.md`.

### Propuesta del equipo → dónde está en la app

| Propuesta | Dónde está | Verificado |
|---|---|---|
| A · Dos botones grandes «Aviso» y «Alerta» | App → escudo «Incidencia ou seguridade» (`/seguridade/`): arriba los dos botones (cuadrado amarillo con llave / octógono rojo con «!», y texto). Debajo sigue todo lo anterior | ✅ tests + E2E (formas distintas, no solo color) |
| A · Alerta → accidente deportivo | `/seguridade/alerta/` → «Accidente deportivo» → protocolo paso a paso de la instalación (proteger, 112 con botón, DESA, aviso automático, registro) | ✅ tests + E2E |
| A · Alerta → emergencia de seguridad | Mismo sitio → 112 en grande (`tel:112`) y aviso inmediato al concello | ✅ tests + E2E |
| A · Botones durante la reserva en curso | Pantalla de la reserva mientras está en curso | ✅ test |
| A · Protocolo configurable | Xestión → Alertas e peches → Protocolo de accidente (concello y por instalación; plantilla por defecto) | ✅ test |
| A · Registro de accidentes mínimo (admin + DPD, conservación) | Xestión → Máis ferramentas → Rexistro de accidentes. Configuración → Seguridade e peche (meses) | ✅ tests (sin texto libre, permisos, purga) |
| A · Incidencia de prioridad máxima | Se crea sola con cada alerta (prioridad «Máxima»), aviso a mantenimiento | ✅ test |
| A · Alerta en la tableta | Tableta → lista de asistencia y modo registro → botón rojo «Alerta» | ✅ test |
| B · Recordatorios y aviso al responsable | Automático (`booking_maintenance`): push → app + correo/Telegram → persona responsable por orden y horario (Xestión → Alertas e peches → Persoas responsables) | ✅ tests con tiempos configurables |
| B · Policía Local solo por decisión de una persona | Página del aviso al responsable (`/seguridade/peche/‹token›/`): botón «Contactar coa Policía Local», queda registrado | ✅ test (nunca automático; registro) |
| B · Nivel 3 con estado de la puerta | Simulador de cerradura (`/dev/lock-simulator/`) → «Pechaduras conectadas: estado da porta» | ✅ tests (cerrada no escala; abierta sí) |
| B · Cierre sin confirmar en la reserva / incumplimiento opcional | Ficha de la reserva (gestión); Configuración → Seguridade e peche (desactivado por defecto) | ✅ test |
| C · Accesibilidad detallada (sí/parcial/no + nota) | Xestión → Instalación → pestaña Accesibilidade; ficha pública «Accesibilidade detallada». La lista básica se rellena sola | ✅ tests + E2E |
| C · Sostenibilidad y DESA | Pestañas Sostibilidade y Seguridade; ficha pública «Mobilidade sostible» y «DESA». Botón «Buscar o DESA máis próximo» (adaptador `defibrillators`, CSV ficticio) | ✅ tests |
| C · Filtros «accesible», «con aparcabicis», «con DESA» | Buscador → Filtros | ✅ tests + E2E |
| C · Revisión de seguridad e índice de vida activa | Plantilla con 3 puntos más; índice con la accesibilidad detallada (`docs/indice-vida-activa.md`) | ✅ tests |
| D · Inventario de equipos, consumo estimado, KPI | Xestión → Instalación → pestaña **Rendemento** y Xestión → Máis ferramentas → Rendemento. Siempre «estimación orientativa» | ✅ 8 tests con cuentas a mano |
| D · Lecturas reales | Mismo panel → «Lecturas reais (facturas) fronte á estimación» | ✅ test |
| D · Comparativa de la diputación | Rede da deputación → «Rendemento (últimos 30 días)», solo agregados | ✅ test |
| E · Encuesta anual con NPS | App → aviso en el inicio y `/enquisa/`; Xestión → Máis ferramentas → Enquisas (NPS); panel del día; comparativa de la diputación | ✅ 10 tests (fórmula, n ≥ 10, una respuesta, aviso por canales) + E2E |
| E · NPS tras cada uso (desactivado por defecto) | Configuración → Satisfacción (NPS); aparece bajo «Que tal foi?» | ✅ tests |
| F · Paso a paso y «que tes que facer e cando» | Ficha de la instalación (Elixe → Paga → Confirma) y cada reserva | ✅ tests + E2E |
| F · Recordatorios con «Confirmo» / «Cancelo» | Avisos a las 24 h y 2 h → pantalla de la reserva | ✅ tests |
| F · Lista de espera en reservas | Franja ocupada → «Avísame»; Reservas → «Listas de espera»; ciclo en la reserva original | ✅ tests del ciclo completo (incluida la devolución) + E2E |
| G · Partidas abiertas | Reserva → «Busco xente»; App → atajo «Partidas abertas» | ✅ 10 tests (privacidad, menores, solicitudes, mensajes, denuncias) + E2E |
| H · Carné municipal y abonos | App → atajo «O meu carné» (QR dinámico, PDF); Xestión → Abonos e carné (tipos, venta en oficina, lector) ; tableta → «Ler carné» | ✅ 9 tests + E2E |
| H · Adaptador `municipal_card` | Solo adaptador simulado + `docs/carne-municipal.md` | ✅ test del simulado |

### Cifras finales
- **Tests unitarios e integración:** 788 en verde (eran 683 en la v1.1).
- **E2E:** 65 en verde (sin contar vídeo y capturas, marca `video`).
- **axe (WCAG 2.1 AA):** 145 páginas × 3 tamaños y 63 en tema oscuro, **0 violaciones**. Están todas las pantallas nuevas de A–H.
- **Sin scroll horizontal** (360 y 390 px, texto normal y grande): también las pantallas nuevas.
- **Castellano:** 100 % (677 cadenas nuevas, traducidas en esta tanda).
- **Capturas:** 65 (29 pantallas en móvil y escritorio y 7 en oscuro) en `docs/capturas/v1.2/` (bloques A–H en móvil y escritorio; A, D y H también en oscuro).
- **RAM sin IA** (`docker compose`, PostgreSQL, proyecto aparte `eira-v12` con volúmenes nuevos): en reposo app 170 MiB (2 workers), PostgreSQL 87 MiB, bucle de avisos 3 MiB → **≈ 260 MiB**; tras ~150 peticiones anónimas y 56 vistas con sesión (incluidas las páginas nuevas de rendimiento, NPS, carné y alertas): app 228 MiB, PostgreSQL 98 MiB → **≈ 330 MiB**. Sigue valiendo un VPS de 1 GB. Ningún error 5xx en PostgreSQL con las migraciones nuevas.

### Correcciones encontradas por el camino
- **Regeneración de la demo:** `SportsPass.type` con `PROTECT` impedía borrar un concello con abonos (la regeneración nocturna habría fallado). Ahora `CASCADE`, con test.
- **«Que tes que facer e cando»** mostraba «Confirma» y «Cancelación gratuita hasta…» en reservas ya empezadas o fuera de plazo. Corregido (se vio en las capturas).
- **`tools/tasks.py annex`** no estaba registrada desde la v5. Corregido.
- **Desbordamiento horizontal** con texto grande a 360 px en el selector de franjas del pabellón («+luz») y en la tabla de tarifas de la ficha: ya existía, salió al añadir esas pantallas a la prueba. Corregido.
- La revisión de seguridad inicial tiene ahora **13 puntos**; el anexo decía «dez puntos» y se corrigió al regrabarlo.

### NO verificado o con límites
- **DESA:** no sabemos si hay un registro oficial gallego con datos abiertos ni su licencia; el CSV de la demo es ficticio. No se integró ninguna app (p. ej. ARIANA RCP).
- **Avisos reales** (push, correo, Telegram) a la persona responsable: probados con los adaptadores simulados.
- **Estado de la puerta (nivel 3):** solo con el simulador; ninguna cerradura real probada.
- **Consumo estimado:** depende del inventario que meta el concello; las lecturas «reales» de la demo son ficticias. En la demo solo hay ~8 semanas de reservas, así que el «kWh por hora de uso» anual sale muy alto (la calefacción cuenta todo el año de apertura y el uso solo 8 semanas).
- **`tools/perf.py`** no consigue iniciar sesión con la portada de la demo en dos pasos (ya pasaba antes); la RAM se midió con un script propio de Playwright.
- **Lectores de QR físicos** y **PDF del carné** (sin validar con PAC/veraPDF, fuentes sin incrustar).
- **Purga** de las denuncias de partidas (1 año): documentada, no programada.
- **Tema oscuro del escritorio:** solo en el panel Rendemento (decisión en DECISIONS).
- **Traducciones al castellano:** sin revisión externa.

### Vídeos
- **Pitch:** no se regrabó (el guion actual sigue funcionando: Uxía reserva en Pontedouro, donde no tiene abono).
- **Anexo «Eira para o concello e a saúde»:** regrabado con dos pasos nuevos (panel de Rendemento y NPS anual): **65 s** (máximo pedido: 75 s), en `docs/demo/` (fuera del git).

### Cómo enseñarlo en 1 minuto
Portada → Vilardeiras → **Uxía** → escudo «Incidencia ou seguridade» → **Alerta → Accidente deportivo** (protocolo con 112 y DESA) → atajo **«O meu carné»** (QR que se renueva) → **Partidas abertas**. Después el concello: **Panel** (alertas, NPS) → instalación del pabellón → **Rendemento** → **Enquisas (NPS)**.


## v1.1. Registro de limpieza (26/10) · etiqueta `v1.1-certame`

**Servidor:** <http://localhost:8000> y en la LAN (`0.0.0.0:8000`, `EIRA_DEBUG=1`), con los datos regenerados justo antes de arrancar. Commits locales, sin push. Los vídeos **no** se han vuelto a grabar (siguen siendo los de la v5).

**Regla:** solo se añade. Choques en `DECISIONS.md` (sección v1.1, palabra «Choque»): el plan preventivo de las plantillas no se toca (la limpieza va en un plan aparte), las órdenes de limpieza no cuentan como «Última supervisión» y, si el concello no tiene personal de limpieza, todo sigue como antes.

### Qué hay y cómo se verificó

| # | Qué | Verificado |
|---|---|---|
| 1 | Rol «Persoal de limpeza» (`cleaning`) por concello, propio o de una **empresa contratada** (campo opcional «Empresa» al asignar el rol). Usa la misma app móvil del operario (`/operario/`), pestaña «Tarefas», y **solo ve tareas de limpieza** | ✅ matriz de roles ampliada (cleaning en todas las URL: 200 en su app, 403 en el resto) + 8 tests de 403 + E2E |
| 2 | Planes de limpieza con el motor del mantenimiento preventivo: tipo de tarea «limpeza»/«mantemento», zonas (vestuarios, aseos, pista, gradas, almacén, vaso…), frecuencia nueva «Varias veces ao día» (una orden por ronda), diaria o semanal, y checklist. Modelos por tipo de instalación en las plantillas (y botón «Aplicar modelo» para las existentes) | ✅ tests (modelo, idempotencia, 3 rondas/día) |
| 3 | QR por zona imprimible (sustituye la hoja de papel). Al escanearlo con el rol de limpieza se abre el checklist: registra quién, empresa, fecha y hora, tareas hechas, observaciones y foto opcional (sin EXIF). Cierra la ronda pendiente. **Sin conexión:** misma cola que el operario; la hora es la de cuando se guardó, no la de la sincronización | ✅ tests + **E2E con el navegador sin red**: la página de la zona abre desde la caché, se guarda en la cola y al volver la red queda con la hora original |
| 4 | Ficha pública: «Última limpeza: hoxe 10:40» junto a la última supervisión. Zona con más tiempo del previsto sin limpiar → aviso al concello (y a limpieza), una vez por retraso, en el panel del día y en «Limpeza» | ✅ tests (aviso único, se rearma tras limpiar, zona nueva no avisa antes de tiempo) + E2E |
| 5 | Enrutado por tipo: incidencias de limpieza, estado al entrar con el nuevo tic «é de limpeza», tic «fai falta limpeza» al salir y valoraciones «Mal» con «Sucia» → tarea y aviso al personal de limpieza; las averías avisan a mantenimiento; el concello ve todo | ✅ 6 tests (incluido «Sucia» + luz rota: avería a mantenimiento y tarea aparte a limpieza) |
| 6 | Registro exportable por instalación y período en **CSV, ODS y PDF** (varias páginas). En el índice de vida activa: −10 en «Mantemento ao día» si hay alguna zona atrasada (era fácil) | ✅ tests (3 formatos, PDF de ≥ 3 páginas, fechas al revés) + E2E de descarga |
| 7 | Demo: **Noela**, limpieza de Vilardeiras de la empresa ficticia «Limpezas Brillo do Val, S. L.»; planes en el pabellón (pista, vestuarios 1 y 2, aseos, gradas, almacén) y en los vestuarios del campo de Outeiro; ≈ 200 registros de 3 semanas (algunos checklists incompletos, observaciones y 3 fotos; los domingos los vestuarios los cubre Brais); **los aseos del pabellón llevan 20 h sin limpiar (máx. 16 h) con el aviso**; una valoración «Mal · Sucia» que generó una tarea. Perfil nuevo en la portada de la demo con su miniatura | ✅ revisado en la demo regenerada |
| 8 | Capturas, informe, etiqueta, servidor | ver abajo |

### Cifras finales
- **Tests unitarios e integración:** 683 en verde (eran 616 en la v5).
- **E2E:** 58 en verde (sin contar los de vídeo y capturas, marca `video`). En la última pasada completa salieron 57 + 1 fallo ajeno a la v1.1: la captura v3 necesita una reserva futura de Uxía en el gimnasio y la suya terminaba a las 20:00, en mitad de la pasada; repetida sola con la demo recién generada, en verde.
- **axe (WCAG 2.1 AA):** 115 páginas × 3 tamaños y 47 en tema oscuro, **0 violaciones**. Las páginas nuevas (app de limpieza, QR de zona para personal y para vecindad, página «Limpeza», QR imprimible, ficha con última limpeza) están en ambos conjuntos.
- **Castellano:** 100 % (154 cadenas nuevas, traducidas a mano en esta tanda).
- **Capturas:** 22 en `docs/capturas/v1.1/` (11 pantallas en móvil y escritorio).

### Correcciones encontradas por el camino
- **Tema oscuro:** la etiqueta «Atrasada» (`badge-alert`) no tenía versión oscura; no se veía porque en la demo no había nada atrasado en las pantallas con tema oscuro. Corregido.
- **Umbral por defecto:** con 8–12 h, las zonas que se limpian varias veces al día habrían avisado todas las mañanas (la noche dura 13 h). Por defecto 16 h; diaria 30 h; semanal 8 días.

### NO verificado o con límites
- **QR sin conexión en un móvil real:** probado en Chromium (Playwright) cortando la red; no en un teléfono con iOS/Android ni escaneando un QR impreso. La página de la zona solo abre sin red si antes se abrió la lista de tareas con conexión (allí se precargan las zonas).
- **La hora sin conexión** es la del reloj del móvil: si está mal, el registro también (se rechazan horas futuras y de más de 7 días).
- **El QR no prueba presencia:** cualquiera con la URL y el rol puede registrar; no se guarda la ubicación (decisión de privacidad).
- **PDF del registro:** texto en Helvetica sin incrustar y sin etiquetar; no es un PDF accesible (el cartel sí lo está).
- **Borrado a los 2 años** de los registros de limpieza: documentado en la matriz RGPD, no programado.
- **Traducciones al castellano:** sin revisión externa.
- **Vídeos:** no regrabados; no muestran la limpieza.
- **Prueba frágil existente:** la captura v3 (`test_screenshots.py`) depende de la hora a la que se genera la demo (ver cifras). No se ha tocado.

### Cómo enseñarlo en 1 minuto
Portada → Vilardeiras → **Noela** → zonas arriba con los **Aseos «Atrasada»** → «Vestiario 2» (lo que abre el QR) → checklist → «Rexistrar limpeza». Después, el concello: **Panel** («Limpeza atrasada») → **Máis ferramentas → Limpeza** (quién y cuándo, empresa, QR para imprimir, **Exportar** en PDF). Y la ficha pública del pabellón: «Última limpeza: hoxe…».

## v5. Versión definitiva (26/10) · etiqueta `v1.0-certame`

**Servidor:** <http://localhost:8000> y en la LAN (`0.0.0.0:8000`, `EIRA_DEBUG=1`), con los datos regenerados justo antes de arrancar. Commits locales, sin push. Desde aquí, solo correcciones.

**Regla de la tanda:** solo se añade. Nada existente se quitó ni se hizo menos visible (salud, consejos, observatorio con esfuerzo y pruebas físicas, valoraciones, tableta, avisos, Telegram). Los choques están en `DECISIONS.md` con la palabra «Choque».

### Qué hay y cómo se verificó

| Bloque | Qué | Verificado |
|---|---|---|
| C | Participantes (obligatorio, máximo por instalación), formas de pago por concello e instalación (TPV, oficina con plazo, gratuita, bono, aplazado desactivado por defecto), conciliación por forma de pago, aprobación del gestor (aviso, aprobar/rechazar con motivo, devolución automática si estaba pagada, cambios pendientes), suplemento de luz (puesta de sol NOAA u horario fijo, «necesito luz», desglose antes de pagar, en la reserva y en el recibo HTML/PDF; nivel 3 solo enciende con suplemento) | ✅ 18 tests + 1 E2E (pago en oficina y aprobación desde el panel) |
| A | Reservar en concellos de la red con la misma cuenta: selector en «Reservar», página «Concellos próximos», aviso de tarifa, tarifa de no empadronada del destino, cobro en el TPV del destino (el TPV simulado muestra el comercio), casilla + cupo + antelación por concello, actividades y eventos de concellos próximos opcionales y filtrables en «Avisos». RGPD en `docs/rxpd/matriz.md` | ✅ 7 tests (tarifa, TPV correcto, opción cerrada, cupo, antelación, el destino no ve correo ni teléfono, el origen no ve la reserva, feed opcional) + E2E de Uxía reservando en Pontedouro con luz |
| B | Ficha: material con cantidades, protocolo de accidente, DEA, 112 (`tel:112`) y última supervisión calculada. Cartel A4 en **PDF etiquetado** (estructura, idioma, texto alternativo del QR, artefactos) y plantilla con el escudo; el cartel HTML también lleva normas, protocolo, DEA y 112 | ✅ 4 tests (contenido del PDF, marcas de etiquetado, permisos) |
| D | Estado al entrar («todo ben» / «hai un problema» + foto sin EXIF); con problema, incidencia **atribuida a antes de la reserva**; entrada y salida juntas en la ficha (vecina, operario y gestor) | ✅ cubierto en tests de C y en la demo; ⚠️ sin E2E propio |
| E | Botón «?» en las cuatro herramientas con ayuda de la pantalla, guía completa y contacto; botón «Incidencia ou seguridade» (avería, riesgo con prioridad alta y aviso inmediato, 112); guía de lenguaje inclusivo y revisión de cadenas gl/es; modo básico (por defecto) / avanzado del menú | ✅ E2E del «?» y de seguridad; test de lenguaje inclusivo sobre el catálogo y las plantillas; E2E del menú |
| F | «Quen custodia os teus datos» (app y web pública) generada desde la matriz; protocolo de brechas; registro de brechas con plazo de 72 h y plantilla de comunicación; rol DPD | ✅ 9 tests de permisos (admin y DPD sí; vecindad, mantenimiento, monitora, diputación con acceso de soporte, otro concello y anónimo no) |
| G | Índice de vida activa 0–100 (ocupación real, diversidad de edades, satisfacción, accesibilidad, mantenimiento), pesos configurables, n ≥ 10, «sen datos suficientes». En la ficha, el panel y la comparativa. **El observatorio no cambia** | ✅ 4 tests |
| H | Plantilla «Revisión de seguridade inicial Eira» (10 puntos) y «Revisada o ‹data›»; `docs/servizos.md` | ✅ test |
| I | Demo, guion, vídeos, capturas, informe, etiqueta, servidor | ver abajo |

### Cifras finales
- **Tests unitarios e integración:** 616 en verde (eran 425 al empezar la tanda).
- **E2E:** 54 en verde (sin contar los de vídeo y capturas, marca `video`).
- **axe (WCAG 2.1 AA):** 105 páginas × 3 tamaños (móvil, tableta, escritorio) y 41 en tema oscuro, **0 violaciones**. Las páginas nuevas de la v5 están en ambos conjuntos.
- **Castellano:** 100 % (503 cadenas nuevas o cambiadas, traducidas y revisadas por muestreo).
- **RAM sin IA** (`docker compose up`, sin modelo cargado): app 200–204 MiB (2 workers), PostgreSQL 47–49 MiB, bucle de avisos 17 MiB → **≈ 270 MiB** en reposo y tras 150 peticiones. Sigue valiendo un VPS de 1 GB.
- **Vídeos** (fuera del git, `docs/demo/`): pitch 1920×1080 de **2:14** con el paso nuevo (reserva de Uxía en Pontedouro con tarifa de no empadronada y luz) y **sin pista de subtítulos activable** en el MP4 (comprobado con ffprobe: un solo flujo de vídeo); anexo «Eira para o concello e a saúde» de **54 s**.
- **Capturas:** 42 en `docs/capturas/v5/` (21 pantallas de A–H en móvil y escritorio).

### Correcciones encontradas por el camino
- **Docker no construía desde la v4.1:** `collectstatic` en el `Dockerfile` fallaba porque `EIRA_PADRON_SECRET` es obligatorio en producción. Ahora la construcción usa un valor solo para construir, como ya hacía con la clave secreta. Verificado: imagen construida y `docker compose up` sirviendo las páginas v5.
- **La demo no se podía regenerar con bonos** (FK protegida): corregido y con test.
- **Tema oscuro:** el día elegido, las franjas tranquilas, las ocupadas y «A túa» del selector no tenían contraste en oscuro (dependía del día y la hora; salió al pasar axe por Pontedouro). Corregido y comprobado con axe en las 13 fichas.

### NO verificado o con límites
- **PDF accesible:** está etiquetado (estructura, idioma, alternativo del QR), pero **no se validó con PAC ni veraPDF** y usa Helvetica sin incrustar, así que no se puede declarar PDF/UA.
- **Puesta de sol:** fórmula NOAA con precisión de ±2 minutos; no se contrastó con una fuente oficial día a día.
- **TPV real:** cada concello cobra en su TPV solo en el adaptador simulado (el comercio aparece en la pasarela). El adaptador Redsys sigue siendo un esqueleto.
- **Índice de vida activa:** los umbrales (60 % de ocupación = 100, ventanas de 30–180 días) son una propuesta razonable, no un estándar; están documentados y son configurables solo en los pesos.
- **Estado al entrar:** sin E2E propio; probado en tests de servicio, en la ficha y en la demo.
- **Traducciones al castellano:** hechas con apoyo automático y revisadas por muestreo, sin revisión externa.
- **Lenguaje inclusivo:** el test busca las formas típicas; no garantiza que no quede ningún masculino genérico en textos largos.
- **Aprobación + cambio de hora:** la franja nueva no se reserva mientras el cambio espera la aprobación (se vuelve a comprobar al aprobar).
- **Vídeos:** revisados por fotogramas (paso nuevo y anexo), no vistos enteros en tiempo real.
- **Commits:** el código de A–H va en un commit; los tests y E2E se pasaron sobre el árbol final de cada grupo, no sobre cada bloque por separado.

### Cómo enseñarlo en 1 minuto
Uxía (Vilardeiras) → Reservar → selector **Pontedouro** → Pista de pádel 1 → franja de noche con «+luz» → desglose y TPV de Pontedouro. Después, el concello: **Panel** («Para aprobar», «Índice de vida activa») → **Cobros** («Por forma de pagamento») → **Máis ferramentas → Rexistro de brechas**. Y la ficha pública de cualquier instalación: seguridad, 112, «Revisada o…».

## v4.1. Ajustes visuales rápidos (24/10)

**Servidor:** <http://localhost:8000> (también en la LAN, `0.0.0.0:8000`) con `EIRA_DEBUG=1`, datos regenerados. Commit local, sin push.

| Qué | Detalle | Verificado |
|---|---|---|
| Configuración | Módulos en una columna fija de 280 px, sticky; por debajo de 1200 px pasan bajo el formulario, sin un segundo «Gardar». Secciones emparejadas por altura (Identidade + Padrón, Contacto + Regras) y Mapa y Textos legais a dos columnas: sin huecos. Rejilla y no masonry, para conservar el orden de lectura y de foco (ver DECISIONS). La nota del padrón sale una vez. Correo y DPD sin cortes (el DPD es un `textarea`) | ✅ tests y capturas `v41-configuracion-1280/1100.png` |
| Botón «Día / Noite» | En la barra de demo y encima del marco del móvil o la tableta. `data-theme` en `<html>`, guardado en la sesión; si no se toca, sigue al sistema. La cabecera hace crossfade día → noche (sin animación con movimiento reducido) | ✅ E2E: alterna, comprueba que la imagen visible pasa a `cabecera-eira-noite`, que persiste al recargar y que vuelve al día; otro E2E con el sistema en oscuro y movimiento reducido |
| Tema oscuro AA | App de vecindario, operario y tableta (el escritorio del concello sigue claro) | ✅ axe sin violaciones en 31 pantallas en oscuro (`test_dark_theme.py`) |
| Estados vacíos | Perfil «Brais · veciño novo» en Vilardeiras, sin reservas, avisos ni inscripciones. El operario tiene filtro «Hoxe / Mañá» y «Mañá» está «todo ao día». Catálogo `/dev/ilustracions/` con las 6 ilustraciones, dónde sale cada una y «Ir á pantalla» con el perfil adecuado | ✅ tests y capturas `v41-baleiro-*.png`, `v41-ilustracions-catalogo.png` |

**Pruebas:** tests unitarios y de integración, y 48 E2E (axe en claro × 3 viewports y en oscuro), todo en verde. Ruff limpio. Las 11 capturas están en `docs/capturas/v4/v41-*.png`.

**NO verificado o con límites:**
- **Escritorio del concello en oscuro:** no tiene tema oscuro y sigue claro aunque el sistema esté en oscuro.
- **Contraste en oscuro:** solo lo comprueba axe, que no mide bordes, iconos ni foco sobre fondo oscuro. Lo revisé visualmente en capturas de las pantallas principales, pero no una a una.
- **Dos Brais:** el veciño novo se llama Brais, como el operario; los distingue el rol en la barra y en la portada. Si molesta, basta con cambiar el nombre en `apps/integrations/demo.py` y en la seed.
- **Cambio en el operario:** la lista por defecto ya no incluye las órdenes de mañana, que ahora van en su propio filtro.
- **Traducciones nuevas al castellano:** unas 25 cadenas, sin revisión externa.

## v4. Ajustes tras la revisión (24/10)

**Servidor de demo:** <http://localhost:8000> · LAN `http://<IP do equipo>:8000`, en una ventana de PowerShell aparte («Eira demo · 0.0.0.0:8000», PID 43956), con los datos regenerados justo antes de arrancar. Sin ningún modelo de IA cargado.

**Commits locales**, sin push: `5fb33a9` (1, 2, 3, 4, 6, 7, 9 y 10) y `8fc4c0d` (5 y 8). Antes de corregir, reproduje cada problema con un test o una captura.

| # | Qué | Causa / detalle | Verificado |
|---|---|---|---|
| 1 | Cero scroll horizontal en vecindario, operario y tableta | Desbordaban la tabla del historial, los `.kv` con insignias `nowrap` (confirmar, detalle, privacidad), las tarjetas de instalación (insignias largas en una columna `auto`) y la tableta estrecha | ✅ E2E nuevo a 360 y 390 px, texto normal y grande, y dentro del marco (≈ 25 pantallas). Mide: página, panel, elementos fuera y texto que desborda |
| 1 | Historial en tarjetas compactas en el móvil (fecha · instalación · estado · importe); tabla en escritorio | — | ✅ captura y E2E |
| 1 | Código de acceso con `clamp()`, siempre en 3+3 («842 261»), lectura dígito a dígito | Un `aria-label` en `<p>` lo marca axe como prohibido, así que va como texto oculto | ✅ captura de Manuel con texto grande a 360 px y axe |
| 3 | «Cerrada» en la sesión de hoy | Guardar el esfuerzo (formulario al que lleva «Lista rápida») ponía `closed_at` aunque la sesión no hubiera empezado. Además, la seed cerraba las sesiones a las 00:49 de ese mismo día | ✅ tests de estado por hora: Por empezar → Abierta → Terminada → Cerrada |
| 3 | Salida: tocar el nombre abre el RPE; si no tenía entrada, se marca sola y la monitora ve un aviso discreto (línea gris, chip «marcadas en la salida» y nota en la lista rápida) | — | ✅ tests de la API y del aviso |
| 3 | Estadísticas de la monitora (solo sus grupos, 8 semanas): asistencia por sesión y media, 3+ faltas seguidas, RPE medio, carga semanal sRPE y pruebas físicas agregadas; cada gráfica con su tabla | — | ✅ 5 tests y axe |
| 6 | Barras: porcentajes de 0 a 100, satisfacción de 0 a 100, absolutos al máximo con aviso visible; «▼ −42» con signo menos tipográfico, también en el resumen | Todo escalaba al máximo de la serie: 23 % llenaba la barra | ✅ 10 tests de ancho y formato; capturas `docs/capturas/v4/graficas-antes/despois-*` |
| 7 | Cabecera «Ferramentas da demo» con concello y perfil, «← Volver á demo» a la última página vista y sin «Acceder» | — | ✅ 2 E2E |
| 10 | Avisos del concello: redacción con vista previa por canal (app, push, correo, Telegram) y estimación; segmentación por toda la vecindad, instalación, descubiertas, actividad o parroquia; programación; cancelación de reservas afectadas | — | ✅ 19 tests (segmentación, preferencias, programación, vinculación del bot, nada sin consentimiento, conservación) y 2 E2E |
| 10 | Telegram: canal público, bot personal con código de un solo uso, adaptador real (Bot API) con el token **solo en el entorno** y simulador tipo chat | — | ✅ test del adaptador con `urlopen` simulado. **No probado contra Telegram real** |
| 10 | App: Avisos con chips de categoría y tablón; preferencias con interruptor de consentimiento y canales por categoría; correo de la demo como bandeja real | — | ✅ E2E y axe |
| 10 | Seed: 18 avisos enviados y 1 programado (Navidad); alerta de viento que cancela 6 reservas exteriores; correos y Telegram coherentes con las reservas | — | ✅ bandeja y Telegram nunca vacíos tras regenerar |
| 2 | Búsqueda compacta: una línea, «Filtros (n)» desplegable, características como chips, filtros activos quitables, Lista/Mapa segmentado | — | ✅ test y E2E sin scroll |
| 4 | Padrón semiautomático: CSV → solo HMAC-SHA256 con secreto de instancia; alta automática por DNI/NIE + fecha; cola con el motivo; registro de cargas; plantilla; `PadronAdapter` (CSV por defecto, API futura) | El nombre nunca se usa (la interfaz ni lo recibe) | ✅ 25 tests: coincidencia, sin coincidencia, minúsculas y espacios, formatos de fecha, recarga, CSV no guardado y borrado al resolver |
| 9 | Apellidos obligatorios al inscribir a un menor en una escuela | — | ✅ test |
| 5 | Configuración en secciones (Identidade, Contacto, Regras de reserva, Padrón, Mapa, Textos legais) en rejilla, con los módulos en la columna lateral | — | ✅ captura `configuracion-seccions.png` y axe |
| 8 | Espaciado: familia con interruptores de consentimiento y formulario «Engadir menor» compacto | — | ✅ capturas `espazado-antes/despois-*` |

**Números:** 406 tests unitarios y de integración, y 44 E2E (más los 2 de vídeo, que no se regrabaron), en verde. axe sin violaciones en ≈ 85 páginas × 3 viewports.

**NO verificado o con límites:**
- **Telegram real:** no se usó ningún bot ni token reales. El adaptador `BotApiTelegramAdapter` sigue la documentación de `sendMessage` y el webhook, pero solo está probado con una respuesta simulada.
- **Padrón real:** no probé el CSV de ningún padrón real; solo ficticios con distintos separadores y formatos. Un padrón grande (más de 200.000 filas) se corta.
- **Envío de avisos programados:** depende de que el despliegue llame a `manage.py send_notices` (cron o temporizador de systemd); en la demo no hay cron.
- **Vídeos de la demo:** no se regrabaron. Las capturas de `docs/capturas/v3/pantallas` sí se regeneraron con la interfaz actual.
- **Traducciones v4:** las escribí a mano (≈ 190 cadenas) sin revisión externa.

**Decisiones que conviene revisar** (detalle en `docs/DECISIONS.md`, secciones «v4 ·»):
- **Actividades e inscripciones como «informativos».** Requieren consentimiento aunque vayan solo a las personas inscritas. Es la opción prudente; podrían considerarse de servicio.
- **Tablón del concello.** En la pantalla Avisos se ven los avisos generales aunque no haya consentimiento, porque consultar no es un envío.
- **Canales de la demo.** Se llaman `@eira_demo_*`, para no coincidir con canales reales de Telegram.
- **Secreto del HMAC.** Si no se define `EIRA_PADRON_SECRET`, se deriva de `SECRET_KEY`. Cambiar cualquiera de los dos obliga a recargar el padrón.


## v3. Pulido fino (23–24/10)

**Servidor de demo:** <http://localhost:8000> · LAN `http://<IP do equipo>:8000`.
- Corre en una ventana de PowerShell aparte, titulada «Eira demo · 0.0.0.0:8000» (PID 41660), con `runserver --noreload` y la IA simulada; no se ha cargado ningún modelo.
- Los datos de demo se regeneraron justo antes de arrancar. Para pararlo, cierra la ventana.
- Comprobado por la IP LAN: portada, correo, cerradura y cuatro perfiles (Uxía, Antía, Concello de Vilardeiras y Rosa de Pontedouro).

**Commits locales**, sin push: `49921e1` (5), `134b8ab` (2), `a87d788` (1), `641a4d4` (6), `50313a8` (4 y lema), `e6c4a91` (8), `56b8626` (3), `b58b8cd` (7) y `33dbe2d` (9).

Antes de corregir, reproduje cada problema con capturas o tests.

| # | Qué | Causa encontrada | Verificado |
|---|---|---|---|
| 5 | Herramientas de demo independientes: correo, cerradura, TPV y Cl@ve con diseño neutro, nunca dentro del marco del perfil; desde la barra de demo se abren en pestaña nueva | Heredaban `base.html` con el marco del perfil activo | ✅ 10 E2E (con y sin sesión, móvil y escritorio): sin `framed`, sin scroll horizontal, correo con salto de línea y enlaces, columnas sin solaparse, ABIERTO |
| 5 | «Cosas raras» de la cerradura | El bloqueo por intentos usaba el reloj **simulado**: con 5 fallos a una hora futura el teclado quedaba bloqueado horas reales para todo el mundo. Además, sin parámetros abría el primer dispositivo de la base de datos, y el código de la persona daba DENEGADO | ✅ test que reproducía el fallo; ahora el bloqueo va con el tiempo real, preselecciona la próxima reserva de la persona y hay botón «Restablecer» |
| 5 | Cl@ve | Con otra sesión abierta, `login()` vacía la sesión y se perdía el destino, así que acababa en Pontedouro. Al reutilizar la identificación (volver atrás) no se explicaba nada | ✅ 3 tests y E2E de principio a fin |
| 2 | Selector de franjas: tira de días, pastillas con hora y precio (★ y precio tachado), leyenda única y resumen fijo «Reservar»; accesible y con texto grande | — | ✅ 5 E2E: teclado, etiquetas accesibles, nada desborda, texto grande a 2 columnas y funciona sin JavaScript |
| 1 | Densidad compacta (base de 15 px y botones de 38 px). «Texto grande» y la tableta conservan los tamaños grandes | Además apareció un fallo previo: la barra de pestanas quedaba fuera de la pantalla en la app sin marco | ✅ capturas antes/después en `docs/capturas/v3/densidade/` |
| 6 | Tableta como el quiosco de AFS +50 (se tomó la versión más reciente, `src/modules/asistencia/kiosko`; solo la lógica): abecedario del primer apellido con contadores y Ñ, buscador, Entrada/Salida, RPE OMNI/Borg con colores, «¡Gracias!» con vuelta a los 3 s, quién falta y cola sin conexión | — | ✅ 12 tests unitarios y 3 E2E: las 40 personas entran, salidas con RPE, búsqueda sin acentos, Ñ y cola sin conexión que se sincroniza |
| 4 | Portada de la demo en dos pasos (concello → perfil, con «qué verás» y miniatura) y barra con el concello y el perfil activos | — | ✅ axe en ambos pasos y tests |
| 8 | Lema sustituido en portada, README, guion, vídeo, meta descripción, `publiccode.yml` y `CLAUDE.md` | — | ✅ test |
| 8 | Pie siempre abajo | — | ✅ medido: termina en el px 900 de 900 |
| 8 | Menú lateral | Solo fallaba el Observatorio (la vista no pasaba `sub`) | ✅ test sobre las 16 entradas |
| 8 | «Devuelto» | La seed cancelaba el 9 % de las reservas con reembolso total y sin motivo, y «Devolta» también se usaba para la llave | ✅ seed coherente (≈4 %, con motivo), etiquetas «Cancelada · importe devolto» y «Chave devolta», y tests |
| 3 | Consejos de salud: de 2 a 4 de una línea con cifra y «Ver más», con la previsión de la instalación para la franja (sensación térmica, humedad, UV, viento y lluvia); también en la tarjeta de la próxima reserva | Antes eran 8 consejos largos, sin sensación ni humedad | ✅ E2E: una línea en móvil y el peso no sale del teléfono; tests de sensación térmica y de coherencia con la estación |
| 7 | Agenda del concello en semana y mes, con filtros, colores por estado y `.ics` | — | ✅ 5 tests y axe |
| 9 | Guion v3, vídeos regrabados (≈ 2 min, ahora con la tableta), capturas en `docs/capturas/v3/` (pitch, 99 pantallas en 3 tamaños y antes/después por punto) y castellano completo (173 cadenas nuevas) | — | ✅ |

**Números:** 332 tests unitarios y de integración, y 35 E2E (más los 2 de vídeo), todo en verde. axe 0 violaciones en 72 páginas × 3 viewports.

**NO verificado o con límites:**
- **MeteoSIX**: el lector se probó con una respuesta de ejemplo según la documentación, no con la API real (necesita clave). El UV se estima.
- **Tableta sin conexión**: probada con Playwright (modo sin red), no en una tableta física durante una sesión real.
- **Traducción v3**: 173 cadenas traducidas por un subagente con verificación automática de marcadores; solo revisé algunas a mano.
- **Miniaturas de la portada**: son capturas de la demo y no se actualizan solas si cambia el diseño.

**Decisiones que conviene revisar** (detalle en `docs/DECISIONS.md`, secciones «v3 ·»):
- **Apellidos opcionales.** Antes no se pedían a los menores; ahora son opcionales para todos, porque el abecedario de la tableta los necesita.
- **Pontedouro sin escuelas.** Tiene perfiles propios en la demo, pero no tiene escuelas.
- **Primera hora.** En las sesiones tempranas, la regla de las 2 h sustituye a la de las 4 h.


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
| Vídeo del guion del pitch | ✅ verificado | `eira-demo-movil.webm` y `eira-demo-escritorio.webm` (adjuntos de la release; ver `docs/demo/VIDEOS.md`) (~88 s, subtítulos, pausas de 2,6–3,4 s), más capturas numeradas en `docs/demo/pasos-movil/` y `pasos-escritorio/` (22 cada una). Se revisaron fotogramas con ffmpeg. `python tools/tasks.py video` |
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
