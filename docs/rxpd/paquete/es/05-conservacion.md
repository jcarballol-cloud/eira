<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Política de conservación

> **MODELO DE EJEMPLO — requiere revisión del DPD y de los servicios jurídicos del concello.**

Los datos personales solo se conservan el tiempo necesario para la finalidad (art. 5.1.e RGPD). Eira
aplica los plazos **automáticamente**: la orden `python manage.py booking_maintenance` (programada
cada 15 minutos, ver `docs/despregamento.md`) borra o anonimiza lo que ha caducado y deja constancia
de las cifras en el registro de auditoría (`retention.purge`, `audit.purge`). El concello debe **confirmar
o cambiar** estos plazos con su DPD (punto 6 de «Protección de datos: primeros pasos»).

**Anonimizar** = quitar la persona y los textos libres y dejar el resto (fecha, instalación, importe)
para la contabilidad y las estadísticas. **Bloqueo** (art. 32 LOPDGDD): si el concello tiene que
conservar algo para atender responsabilidades legales, debe hacerlo fuera del uso ordinario; Eira no
tiene un estado de bloqueo propio (ver `docs/PLAN_V2.md`).

## Plazos que aplica Eira

| Datos | Plazo | Qué pasa | Regla (`EIRA_RETENTION`) u origen |
|---|---|---|---|
| Reservas (persona, nombres, teléfono, notas, foto del estado) | 24 meses después de finalizar | Se anonimiza; las partidas abiertas de esa reserva se borran | `bookings` |
| Eventos de acceso (puerta, códigos) | 24 meses | Se borran | `access_events` |
| Incidencias resueltas | 24 meses después de resolver | Se quitan quien avisó y la foto; queda la descripción de la avería | `incidents` |
| Comentarios de las valoraciones | 24 meses | Se borra el comentario; la nota sigue contando | `ratings` |
| Respuestas de las encuestas anuales | 24 meses | Se quitan la persona y el comentario | `surveys` |
| Registro de limpieza (personal) | 24 meses | Se borra, con la foto | `cleaning` |
| Denuncias de partidas abiertas | 12 meses | Se borran | `game_reports` |
| Altas pendientes de la tableta (nombre, año y correo de la familia) | 3 meses | Se borran | `pending_participants` |
| Códigos de empadronamiento sin usar | 1 mes después de caducar | Se borran | `invitations` |
| Correo y mensajes simulados (solo con los adaptadores de prueba) | 1 mes | Se borran | `simulated` |
| Códigos para entrar (contienen el correo) | Caducan a los 10 minutos; se borran al día siguiente | Se borran | `purge_login_codes` |
| Sesiones caducadas (14 días) | Al caducar | Se borran | `purge_sessions` |
| Solicitudes de la app | 12 meses (el DNI/NIE, la fecha y la dirección se borran al resolver) | Se borran | `purge_app_requests` |
| Avisos recibidos | 12 meses | Se borran | `notifications.notices.purge` |
| Códigos de vinculación de Telegram | 1 día (caducan a los 30 minutos) | Se borran | `notifications.notices.purge` |
| Registro de accidentes | 24 meses después de cerrado (configurable por el concello) | Se borra | `accident_retention_months` |
| Registro de auditoría | 24 meses (configurable, 12–120) | Se borra | `audit_retention_months` |
| Resúmenes del padrón (HMAC) | Hasta la siguiente carga | Se sustituyen | Carga del padrón |
| Cuenta, preferencias, salud guardada, carné y procedencia | Mientras la persona tenga la cuenta | Se borran con la cuenta; las reservas quedan anonimizadas | Supresión (art. 17) |
| Aceptaciones de documentos legales | El que fije el concello | Al eliminar la cuenta quedan sin persona | Módulo «Documentos legales» |
| Registro de brechas | 5 años (más que los 3 de prescripción de las infracciones muy graves, art. 72 LOPDGDD) | Manual | `brechas.md` |

Para cambiar un plazo en la instalación: `EIRA_RETENTION = {"bookings": 36}` en `eira/settings.py`
(o en la configuración de despliegue). Los plazos de accidentes y auditoría los cambia el concello
en «Configuración».

## Plazos sin purga automática (pendientes)

| Datos | Plazo previsto | Por qué no se purga todavía |
|---|---|---|
| Pagos | 6 años (normativa tributaria) | Depende de la contabilidad de cada concello; ver `PLAN_V2.md` |
| Asistencia, esfuerzo (RPE) y pruebas físicas | Temporada + 1 año | Las temporadas no tienen fecha de fin común; ver `PLAN_V2.md` |
| Registro de brechas | 5 años | Poco volumen; lo borra el concello |

## Cómo comprobarlo

- Tests: `apps/accounts/tests/test_retention.py` (una prueba por regla y una que comprueba que cada
  regla está en esta tabla).
- En la instalación: `python manage.py booking_maintenance` escribe «Conservación: {…}» con lo que
  ha borrado; en el registro de auditoría aparece «Datos antiguos borrados o anonimizados por conservación».
