<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Evaluación de impacto relativa a la protección de datos (EIPD) — revisada con la auditoría

> **MODELO DE EJEMPLO — requiere revisión del DPD y de los servicios jurídicos del concello.**
>
> Revisión del 14/11/2026 (Eira 1.5.1) con la [auditoría de la AEPD](../../auditoria-aepd.md): añade el alta
> con padrón (F), los riesgos R16–R20 y los plazos que ahora se purgan solos.

> **Para qué sirve:** el art. 35 del RGPD obliga a hacer una EIPD antes de tratar datos que puedan
> suponer un alto riesgo. Esta plantilla ya viene **cumplimentada con lo que hace Eira de verdad** (comprobado en el
> código y en los tests citados). El concello tiene que completar lo marcado con `‹ ›`, revisarla con su DPD y
> aprobarla. **No sustituye el criterio del DPD ni del responsable.**
>
> **Resumen para la vecindad en la app:** *Quién custodia tus datos → Ver la evaluación de impacto*
> (`/c/<concello>/privacidade/avaliacion-impacto/`). Ver también la [matriz de visibilidad](../../matriz.md),
> el [RAT](01-registro-actividades.md) y el [protocolo de brechas](07-brechas.md).

| | |
|---|---|
| Responsable del tratamiento | Concello de ‹nombre›, ‹NIF›, ‹dirección› |
| Encargado (si la aloja la diputación) | ‹Diputación/mancomunidad›, con contrato del art. 28 RGPD |
| DPD | ‹nombre o puesto, contacto› |
| Versión de Eira evaluada | 1.5.1 (etiqueta `v1.5.1-certame`) |
| Fecha y versión de la EIPD | ‹fecha› · ‹versión› |
| Próxima revisión | ‹fecha; como mínimo anual o cuando cambie el tratamiento› |

## 0. ¿Es obligatoria?

Los tratamientos de Eira que cumplen al menos dos criterios de la lista de la AEPD (art. 35.4: «dos o
más criterios» → EIPD en la mayoría de los casos; la lista incluye a los menores de 14 años como personas
vulnerables) son los que entran en esta EIPD:

| Tratamiento | Datos de categoría especial (art. 9) | Personas vulnerables (menores) | Datos a gran escala | Otros criterios | EIPD |
|---|---|---|---|---|---|
| A. Salud: consejos, RPE, pruebas físicas y observatorio | ✔ (salud) | ✔ (escuelas deportivas) | ‹según población› | evaluación/perfiles de condición física | **Sí** |
| B. Menores en las escuelas | — | ✔ | ‹› | imagen | **Sí** |
| C. Registro de accidentes | posible (salud, si se escribiese) | posible | — | — | **Sí (preventiva)** |
| D. Carné municipal con foto | foto (no biométrica: no se usa para identificar automáticamente) | posible | ‹› | — | **Sí (preventiva)** |
| F. Alta con padrón | — | — | ‹según población› | C2 decisión automatizada (alta y tarifa) y C8 combinación con el padrón | **Recomendable** |
| Reservas, pagos, incidencias | — | — | — | — | No (solo RAT) |

## 1. Descripción del tratamiento

### A. Salud: consejos, esfuerzo percibido (RPE), pruebas físicas y observatorio

| | |
|---|---|
| Finalidad | Dar consejos de hidratación y calor en la reserva; seguir el esfuerzo y la condición física en las escuelas deportivas; estadísticas anónimas de actividad física |
| Datos | Consejos: edad, peso, minutos semanales de actividad. Escuelas: asistencia, esfuerzo percibido (escala Borg/OMNI), resultados de pruebas ALPHA-Fitness/SFT |
| Personas | Vecindad usuaria; niños y niñas de las escuelas; personas mayores |
| Base jurídica | Consejos: **consentimiento explícito** (art. 9.2.a) solo si se guardan en la cuenta; en el dispositivo no hay tratamiento del concello. Escuelas: misión de interés público (art. 6.1.e) + **consentimiento de la familia** para esfuerzo y pruebas (`Consent.Kind.PERFORMANCE`) |
| Dónde se guarda | Consejos: **en el dispositivo** (`localStorage`); en la cuenta solo con consentimiento (`HealthProfile`). Escuelas: base de datos del concello |
| Quién accede | Persona monitora (sus grupos, si hay consentimiento); administración del concello. **Nunca** la diputación sin acceso de soporte; nunca el observatorio público con datos individuales |
| Conservación | ‹ver RAT›; el perfil de salud se borra cuando la persona lo retira |

### B. Menores en las escuelas deportivas

| | |
|---|---|
| Finalidad | Inscripción, listas de asistencia, avisos a la familia |
| Datos | Nombre, apellidos, año de nacimiento; consentimientos (datos, imagen, esfuerzo) con fecha y versión del texto |
| Base | Misión de interés público (art. 6.1.e); consentimiento de la familia para imagen y esfuerzo; art. 7 LOPDGDD (menores de 14) |
| Quién accede | Familia; persona monitora (nombre y primer apellido); administración |

### C. Registro de accidentes

| | |
|---|---|
| Finalidad | Conocer los accidentes en las instalaciones para mejorar la seguridad y responder a reclamaciones |
| Datos | Fecha y hora, instalación, tipo general, gravedad **percibida**, si se llamó al 112, papel de quien comunica |
| Base | Obligaciones legales de seguridad e interés público (art. 6.1.c y 6.1.e) |
| Quién accede | Solo administración del concello y DPD (`breach_access`); la diputación solo cifras agregadas |
| Conservación | Configurable (`accident_retention_months`, por defecto 24 meses después de cerrado) y purga automática |

### D. Carné municipal con foto

| | |
|---|---|
| Finalidad | Acreditar la condición de abonado/a y registrar la entrada |
| Datos | Número de carné, foto opcional, tipo y validez del abono |
| Base | Ejecución de la relación con el servicio (art. 6.1.b) e interés público; la foto, **opcional** |
| Quién accede | La persona; personal que lee el carné (tipo y validez); administración |

### E. Procedencia y movilidad (v1.5)

| | |
|---|---|
| Finalidad | **Estadística:** planificar transporte, horarios e instalaciones |
| Datos | Parroquia o concello de residencia, voluntarios. **Nunca GPS, ubicación del dispositivo ni dirección** |
| Base | Misión de interés público (art. 6.1.e) y fines estadísticos (art. 89); el DPD debe confirmarla |
| Quién accede | La persona a su dato. Concello y diputación: solo agregados, n ≥ 10 personas distintas después de cada filtro |

### F. Alta con padrón (añadido en la revisión)

| | |
|---|---|
| Finalidad | Dar la app y la tarifa de vecindad a quien está empadronado |
| Datos | Nombre, apellidos, correo, DNI/NIE, fecha de nacimiento y dirección opcional (solo hasta resolver); del padrón, solo HMAC y parroquia |
| Base | Misión de interés público (art. 6.1.e): servicio de deportes y ordenanza fiscal |
| Decisión automatizada | Si hay coincidencia, alta automática. Si no la hay, **no se deniega**: pasa a revisión manual con el motivo |
| Quién accede | Administración del concello (cola de revisión) |

## 2. Necesidad y proporcionalidad

| Pregunta | Respuesta (Eira 1.5.1) | Dónde se comprueba |
|---|---|---|
| ¿Hay una forma menos intrusiva de lograr lo mismo? | Los consejos de salud funcionan **sin enviar datos al servidor**; guardarlos en la cuenta es opcional | `tests/e2e/test_flows.py::test_health_data_never_leaves_device` |
| ¿Se piden solo los datos necesarios? | Sin DNI, dirección ni apellidos de menores en la tableta; de la edad solo el año | `docs/rxpd/matriz.md` |
| ¿Los datos de salud llegan al personal? | No: ni al personal ni a las exportaciones del concello | `apps/accounts/tests/test_health.py` |
| ¿Las estadísticas permiten identificar? | Solo se publican grupos con **n ≥ 10** (`EIRA_MIN_AGGREGATION`); microdatos con seudónimo HMAC y banda de edad | `apps/activities/tests/test_activities.py::test_observatory_threshold` |
| ¿El padrón queda copiado en Eira? | No: se carga como **HMAC** de «concello\|DNI\|fecha» y el DNI de una solicitud se borra al decidir | `apps/accounts/padron.py`, `apps/accounts/tests/test_padron.py` |
| ¿El registro de accidentes puede contener diagnósticos? | No: **no hay texto libre** | `apps/safety/tests/test_safety.py::test_accident_register_minimal_data_and_access` |
| ¿Consentimientos revocables? | Sí, en un clic y con fecha | `apps/accounts/tests/test_privacy.py` |
| Información a las personas | «Quién custodia tus datos», política de privacidad, resumen de la EIPD | `/c/<concello>/privacidade/…` |
| Derechos | Acceso/portabilidad (JSON), rectificación, supresión con anonimización de las reservas | `docs/seguridade-rxpd.md` |

## 3. Riesgos y medidas

Escala: probabilidad e impacto **B**ajo · **M**edio · **A**lto. El riesgo inherente es antes de las
medidas; el residual, después. Valores propuestos: el DPD debe revisarlos.

| # | Riesgo | Trat. | Inherente (P/I) | Medidas que ya tiene Eira | Residual (P/I) |
|---|---|---|---|---|---|
| R1 | Acceso indebido del personal a datos de salud | A | M/A | El personal no ve los datos de salud; salud en el dispositivo por defecto; ni en el admin técnico (`HealthProfile` excluido) | B/A → **Bajo** |
| R2 | Reidentificación en el observatorio | A | M/A | n ≥ 10; bandas de edad; seudónimo HMAC con el secreto del servidor; IA opcional solo con agregados (el adaptador rechaza campos personales) | B/M → **Bajo** |
| R3 | Registro de esfuerzo de menores sin consentimiento | A, B | M/A | Consentimiento `performance` de la familia, por menor, con fecha y revocable; la tableta no permite registrar sin él | B/M → **Bajo** |
| R4 | Exposición de la imagen de menores | B | M/A | Consentimiento `image` separado; icono de cámara verde o tachada en la tableta | B/M → **Bajo** |
| R5 | Datos clínicos en el registro de accidentes | C | M/A | Sin texto libre; gravedad percibida en categorías; ni la diputación ni con el acceso de soporte; purga automática | B/M → **Bajo** |
| R6 | Policía o terceros reciben datos automáticamente | C | B/A | **No hay ningún envío automático**; solo queda constancia de quién decidió contactar | B/B → **Bajo** |
| R7 | Uso de la foto del carné para otros fines o suplantación | D | M/M | Foto opcional, sin EXIF/GPS; QR sin datos personales, dinámico (caduca en minutos); impreso revocable por versión | B/M → **Bajo** |
| R8 | Cuenta de administración comprometida (robo del correo) | todos | M/A | Código al correo con caducidad e intentos limitados; **doble factor TOTP** (obligatorio si el concello lo configura); **registro de auditoría** consultable por administración y DPD | B/A (con 2FA obligatorio) · M/A (sin él) |
| R9 | La diputación (encargada) accede a datos personales | todos | M/A | Solo agregados; acceso de soporte autorizado por el concello, 24 h, solo lectura, cada página vista registrada y avisada | B/M → **Bajo** |
| R10 | Exportaciones masivas de datos sin control | todos | M/A | Toda descarga del personal queda en `AuditLog` (`export.download`); las exportaciones del concello no incluyen salud | B/M → **Bajo** |
| R11 | Brecha de seguridad no gestionada en plazo | todos | M/A | Registro de brechas con plazo de 72 h y texto de comunicación | B/M → **Bajo** |
| R12 | Copia del padrón o del DNI | padrón | M/A | HMAC por concello; DNI de la solicitud borrado al decidir | B/M → **Bajo** |
| R13 | Reidentificar a una persona cruzando filtros de procedencia | E | M/A | n = personas distintas; umbral **después de cada filtro**; «otras procedencias» sin cifra si n < 10; sin totales; periodos cerrados; solo concello para quien viene de fuera; exportaciones registradas. Queda el riesgo de comparar fechas distintas en un flujo visible | B/M → **Bajo (el DPD debe revisarlo)** |
| R14 | Asignar a menores una persona sin la comprobación de la contratación, o guardar datos penales | B | M/A | Eira **no guarda el certificado**; solo quién marcó y cuándo; asignación bloqueada y revisión periódica. La marca es una declaración del concello, no una comprobación de Eira | B/A → **Medio-bajo (depende del concello)** |
| R15 | Aceptar un modelo de ejemplo como si fuese un texto legal revisado | todos | M/M | Aviso visible en la app y en los ficheros; solo desaparece si el concello adapta el texto y declara que lo ha revisado | B/M → **Bajo** |
| R16 | En un dispositivo compartido (tableta, ordenador del mostrador), la siguiente persona ve sin red páginas guardadas de la anterior (lista de menores, reservas) | B, todos | M/A | **Nuevo:** al salir, `Clear-Site-Data: "cache"`; la caché de páginas se borra si cambia la persona o no hay sesión (`test_rgpd_device.py`, E2E `test_rgpd.py`) | B/M → **Bajo** |
| R17 | Datos de salud escritos en textos libres (notas, comentarios) | A, todos | M/M | **Nuevo:** aviso en todos los campos de texto libre; el registro de accidentes sigue sin texto libre. No hay detección automática | M/B → **Bajo-medio** |
| R18 | Conservación más larga de lo necesario | todos | A/M | **Nuevo:** purga automática de todos los plazos documentados salvo pagos y asistencia (ver [05-conservacion.md](05-conservacion.md)) | B/M → **Bajo** |
| R19 | Transferencias fuera de la UE: Telegram (voluntario) e IP al servidor de teselas del mapa | todos | M/B | Telegram solo si la persona lo vincula; teselas configurables por el concello | B/B → **Bajo** (si el concello usa teselas propias) |
| R20 | Alta denegada por un error del contraste automático con el padrón | F | M/M | Sin coincidencia → revisión humana con el motivo; nunca se empareja por el nombre (`test_padron.py`) | B/B → **Bajo** |

## 4. Riesgo residual y conclusión

- **Riesgo residual global propuesto: bajo**, con la condición de que el concello **active el doble
  factor obligatorio** para la administración y el DPD (*Configuración → Seguridad de las cuentas y
  registro de auditoría*). Sin él, el riesgo R8 queda en **medio**.
- No se propone consulta previa a la AEPD (art. 36) ‹si el DPD está de acuerdo›.
- **Medidas pendientes o fuera de Eira** (responsabilidad del concello o de la entidad que lo aloja):
  - cifrado de la base de datos y de las copias de seguridad; control de acceso al servidor;
  - contrato de encargo (art. 28) con la diputación/mancomunidad y con la empresa de limpieza, si la hay;
  - formación del personal;
  - borrado automático: desde la 1.5.1 están programados todos los plazos salvo pagos (6 años) y
    asistencia/esfuerzo (temporada + 1 año), que dependen de la contabilidad y de las temporadas de cada concello;
  - desde la v1.4 el secreto TOTP se guarda cifrado; para que las copias de la base de datos no basten,
    definir `EIRA_TOTP_KEY` fuera de la base de datos (ver `docs/seguridade-rxpd.md`).
  - el registro de auditoría se conserva 2 años por defecto (configurable) y se borra solo (v1.4).

## 5. Plan de acción

| Medida | Responsable | Plazo | Estado |
|---|---|---|---|
| Activar el doble factor obligatorio para administración y DPD | ‹› | ‹› | ‹› |
| Revisar el registro de auditoría ‹mensualmente› | DPD | ‹› | ‹› |
| Firmar el contrato de encargo con la entidad que aloja Eira | ‹› | ‹› | ‹› |
| Revisar textos legales (privacidad, consentimientos) | ‹› | ‹› | ‹› |

## 6. Opinión del DPD

> ‹La persona delegada de protección de datos, tras revisar esta evaluación, emite la siguiente opinión
> (art. 35.2 RGPD):›
>
> ‹Conforme / conforme con condiciones / no conforme›
>
> ‹Observaciones y condiciones:›
>
> ‹Fecha y firma›

## 7. Aprobación del responsable

> ‹Órgano que aprueba (alcaldía, concejalía delegada…), fecha y firma.›
> ‹Si se aparta de la opinión del DPD, motivo.›

---

**Nota de verificación (equipo Eira):** las medidas de esta plantilla están en el código de la 1.5.1 y tienen los
tests citados. La **valoración del riesgo** (probabilidad, impacto y residual) es una **propuesta**: no
está verificada por ningún DPD.
