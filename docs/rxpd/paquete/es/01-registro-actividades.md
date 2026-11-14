<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Registro de actividades de tratamiento (art. 30 RGPD)

> **MODELO DE EJEMPLO — requiere revisión del DPD y de los servicios jurídicos del concello.**

Cumplimentado con lo que hace Eira 1.5.1 (ver la [auditoría](../../auditoria-aepd.md)). El concello completa lo
marcado con `‹ ›`. Como administración pública, además debe **publicar el inventario** de estas
actividades con su base legal, por medios electrónicos (art. 31.2 LOPDGDD).

## Datos comunes a todas las actividades (art. 30.1.a)

| | |
|---|---|
| Responsable | Concello de ‹nombre›, ‹NIF›, ‹dirección›, ‹correo› |
| Delegado/a de protección de datos | ‹nombre o puesto, correo› (obligatorio para los concellos: art. 37.1.a RGPD) |
| Encargado, si lo hay | ‹diputación, empresa o quien aloje Eira›, con contrato del art. 28 ([04-contrato-encargado.md](04-contrato-encargado.md)) |
| Transferencias internacionales | **Ninguna** con los datos de las cuentas. Excepciones: Telegram (voluntario, fuera del EEE) y el servidor de teselas del mapa, si es externo (dirección IP del navegador) |
| Medidas de seguridad (art. 32) | ENS (RD 311/2022) según la disposición adicional 1.ª LOPDGDD; en Eira: HTTPS, CSP estricta, sesiones de 14 días, acceso sin contraseña con código de un solo uso, doble factor para la gestión, registro de auditoría, aislamiento por concello, fotos sin metadatos, purga automática |

## Actividades

| # | Actividad | Finalidad (30.1.b) | Base jurídica | Interesados y categorías de datos (30.1.c) | Destinatarios (30.1.d) | Plazo de supresión (30.1.f) |
|---|---|---|---|---|---|---|
| 1 | Cuentas y acceso | Identificar a quien reserva o se inscribe | 6.1.e (Ley 7/1985, art. 25.2.l) | Vecindad: correo, nombre para mostrar; teléfono y año de nacimiento opcionales; idioma y preferencias | Ninguno | Mientras la cuenta esté activa; códigos de entrada al día siguiente; sesiones al caducar |
| 2 | Alta con padrón y tarifas | Dar la app y la tarifa de vecindad o reducida | 6.1.e y ordenanza fiscal | Solicitantes: nombre, apellidos, correo, DNI/NIE, fecha de nacimiento, dirección opcional; del padrón solo HMAC y parroquia; colectivo de tarifa reducida | Ninguno | DNI, fecha y dirección: al resolver. Solicitud: 12 meses. HMAC: hasta la siguiente carga. Códigos sin usar: 1 mes después de caducar |
| 3 | Reservas | Gestionar el uso de las instalaciones | 6.1.e; 6.1.b si hay pago | Vecindad y personas de otros concellos de la red: reserva, participantes opcionales, checklist, estado al entrar (texto y foto opcional) | Mantenimiento (solo instalación y hora); concello de destino en las reservas de la red (nombre para mostrar y concello de origen) | 24 meses después de finalizar; después anonimizada |
| 4 | Control de acceso | Abrir la puerta y saber que se usó la reserva | 6.1.e | Eventos de acceso y entrega de llaves | Ninguno | 24 meses |
| 5 | Cobros y devoluciones | Cobrar tasas y precios públicos | 6.1.c y 6.1.e | Referencia, importe, estado y forma de pago; sin datos de tarjeta | Entidad financiera (pasarela) e Intervención | 6 años (normativa tributaria) |
| 6 | Incidencias y alertas | Reparar averías y avisar ante un peligro | 6.1.e | Quien avisa, descripción, foto sin metadatos; en la alerta, el puesto de quien la recibe | Mantenimiento y limpieza (sin datos de contacto); persona responsable de la instalación | Incidencias resueltas: a los 24 meses sin persona ni foto. Alertas: con la incidencia |
| 7 | Registro de accidentes | Mejorar la seguridad y responder a reclamaciones | 6.1.c y 6.1.e | Fecha, instalación, tipo general, gravedad percibida, 112 sí/no, papel de quien comunica. **Sin diagnósticos ni texto libre** | Ninguno (ni la diputación) | 24 meses después de cerrado (configurable) |
| 8 | Salud: consejos personales | Recomendaciones de agua y energía | **9.2.a** (consentimiento explícito), solo si se guarda en la cuenta | Peso, edad, minutos semanales | Ninguno, ni el personal | Hasta retirar el consentimiento o eliminar la cuenta |
| 9 | Escuelas deportivas: asistencia, esfuerzo y pruebas | Inscripción, seguimiento y observatorio anónimo | 6.1.e; consentimiento de la familia para esfuerzo y pruebas | Menores y adultos: nombre, año, apellidos (los aporta el concello), asistencia, esfuerzo (RPE), pruebas físicas; seudónimo HMAC | Monitora (sus grupos: nombre y primer apellido); observatorio solo agregado (n ≥ 10) | Temporada + 1 año (sin purga automática) |
| 10 | Menores y personas tutoras | Inscribir menores y recoger los consentimientos | 6.1.e; art. 7 LOPDGDD | Persona tutora; menores: nombre y año; consentimientos con fecha y versión; altas pendientes en la tableta (nombre, año, correo de la familia) | Monitora (nombre y primer apellido) | Mientras tenga la cuenta; altas pendientes, 3 meses |
| 11 | Imagen | Fotos en actividades y comunicaciones | 6.1.a, revocable | Personas inscritas y adultas que lo autorizan | Comunicación municipal | Hasta la retirada |
| 12 | Carné municipal y abonos | Acreditar el abono y registrar la entrada | 6.1.e; foto opcional | Número de carné, foto sin metadatos, abono, número de otro carné municipal (opcional) | Personal que lee el carné (tipo y validez) | Mientras tenga la cuenta; abonos, 6 años (cobros) |
| 13 | Partidas abiertas | Encontrar gente para jugar | 6.1.a | Nombre de pila e inicial, nivel, mensaje corto, solicitudes y mensajes predefinidos, denuncias | Otras personas de la app (solo nombre de pila e inicial) | Con la reserva (24 meses); denuncias, 12 meses |
| 14 | Procedencia | Estadística para planificar transporte e instalaciones | 6.1.e y art. 89 | Parroquia o concello de residencia, voluntarios. Nunca GPS | Concello y diputación, solo agregados (n ≥ 10) | Mientras tenga la cuenta o hasta que la borre |
| 15 | Valoraciones y encuestas (NPS) | Mejorar el servicio | 6.1.e | Valoración, etiquetas, comentario; encuesta anual | Concello, sin nombre; diputación, solo NPS agregado | Comentarios: 24 meses. Encuesta: persona y comentario, 24 meses |
| 16 | Avisos del concello | Informar de cierres, alertas y actividades | Servicio: 6.1.e (y 6.1.b si afecta a una reserva). Informativos: 6.1.a | Preferencias por categoría y canal, consentimiento, chat de Telegram, suscripción push, avisos recibidos | Proveedor de correo del concello; **Telegram** si la persona lo vincula (fuera del EEE) | Avisos: 12 meses. Códigos de Telegram: 1 día |
| 17 | Registro de auditoría y doble factor | Seguridad y trazabilidad (ENS) | 6.1.c (art. 32 RGPD) | Personal de gestión: correo, acciones, fechas, descargas; secreto TOTP cifrado | Administración y DPD del concello | 24 meses (12–120, configurable) |
| 18 | Acceso de soporte de la diputación | Asistencia técnica al concello | 6.1.e y contrato art. 28 | Los datos que consulte durante el acceso | Personal autorizado de la diputación | Acceso: 24 h. Registro: el de la auditoría |
| 19 | Documentos legales y aceptaciones | Informar y justificar aceptaciones y consentimientos | 6.1.c y 6.1.a | Persona, documento, versión, fecha, canal, retirada | Administración y DPD | El que fije el concello; al eliminar la cuenta queda sin persona |
| 20 | Acreditación con menores | Constancia de la comprobación en la contratación | 6.1.c (LOPIVI, art. 57) | Personal monitor: solo quién marcó y cuándo. **Sin certificado ni datos penales** | Administración del concello | Hasta retirar la marca o eliminar la cuenta |
| 21 | Registro de limpieza | Control del contrato y de la higiene | 6.1.b y 6.1.c | Personal de limpieza: nombre, empresa, fecha y hora, tareas, observaciones, foto | Concello; vecindad solo «última limpieza» sin nombre | 24 meses |
| 22 | Registro de brechas | Cumplir los arts. 33 y 34 | 6.1.c | Descripción de la brecha, datos y personas afectadas, medidas | Administración y DPD; AEPD si se notifica | 5 años |

## Registro del encargado (art. 30.2)

Si Eira la aloja la diputación, una empresa o engram, esa entidad lleva su propio registro como
encargada: nombre y contacto del encargado y de cada responsable (los concellos), categorías de
tratamiento (las 22 de arriba), transferencias (ninguna) y medidas de seguridad. El modelo de
contrato está en [04-contrato-encargado.md](04-contrato-encargado.md).

## Cómo mantener este registro

- Revisarlo cuando se active un módulo nuevo (escuelas, partidas abiertas, carné…) o se cambie un plazo.
- El origen de cada dato está en la [auditoría](../../auditoria-aepd.md) y en la [matriz](../../matriz.md).
- En Eira: «Protección de datos: primeros pasos» → «Registro de actividades descargado y
  revisado» deja constancia de quién lo revisó y cuándo.
