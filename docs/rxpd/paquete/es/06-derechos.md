<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Procedimiento para atender los derechos (arts. 12 a 22 RGPD; arts. 12 a 18 LOPDGDD)

> **MODELO DE EJEMPLO — requiere revisión del DPD y de los servicios jurídicos del concello.**

## Reglas comunes

- **Plazo:** contestar **sin dilación indebida y como máximo en un mes** desde la solicitud;
  prorrogable otros dos meses si es compleja, avisando dentro del primer mes (art. 12.3).
- **Gratuito** (art. 12.5 RGPD; cita **no verificada** en el contraste del 14/11/2026).
- **Identificación:** si la persona lo hace desde su cuenta de Eira, ya está identificada. Si lo hace por
  escrito o en el mostrador, el concello puede pedir lo mínimo para identificarla (nunca más datos de los
  que ya tiene).
- **Canales:** desde la propia app (la mayoría de los derechos) o por escrito al concello o al DPD
  (‹correo del DPD›, registro electrónico).
- **Registro:** anotar la fecha de entrada, la respuesta y la fecha de respuesta. Las acciones realizadas desde
  la app quedan en el registro de auditoría (descarga de los datos propios, eliminación de la cuenta).
- **Reclamación:** siempre hay que recordar el derecho a reclamar ante la Agencia Española de
  Protección de Datos.

## Cada derecho en Eira

| Derecho | Qué puede hacer la persona sola, en la app | Qué hace el concello | Notas |
|---|---|---|---|
| **Acceso** (art. 15) | «Mi cuenta → Descargar todos mis datos (JSON)» (`/conta/os-meus-datos.json`): cuenta, salud guardada, roles, empadronamiento, reservas, incidencias, familia y consentimientos, inscripciones, avisos recibidos, procedencia y documentos aceptados. También carné, abonos, bonos, valoraciones, partidas abiertas y preferencias de avisos. «Quién custodia tus datos» explica quién ve cada dato | Si lo pide por escrito, generar la misma descarga con la persona identificada | La descarga queda en AuditLog (`account.export`) |
| **Rectificación** (art. 16) | «Mi cuenta»: nombre para mostrar, teléfono, año de nacimiento, idioma, procedencia; «Familia»: menores | Corregir en el panel lo que la persona no puede cambiar (colectivo de tarifa, empadronamiento, apellidos de los menores) | Informar a quien se hayan comunicado los datos (art. 19) |
| **Supresión** (art. 17) | «Mi cuenta → Eliminar la cuenta» (`/conta/eliminar/`): se borra la cuenta, la salud guardada, el carné, las preferencias y la procedencia; las reservas quedan **anonimizadas** (sin persona, nombres, notas ni foto) para la contabilidad | Revisar si hay algo que deba conservarse por obligación legal (pagos) y bloquearlo fuera del uso ordinario (art. 32 LOPDGDD) | `test_retention.py::test_account_deletion_also_clears_free_text_of_bookings`; `test_health.py::test_account_deletion_removes_health` |
| **Retirar un consentimiento** (art. 7.3) | «Documentos aceptados», «Privacidad» (imagen), «Mi salud» (borrar los datos), «Familia» (consentimientos de cada menor), preferencias de avisos | — | Tiene efecto al momento: imagen → se retira la autorización; salud → se borran los datos |
| **Oposición** (art. 21) | Para lo opcional: desmarcar avisos informativos, borrar la procedencia, dejar una partida abierta | Para lo que se basa en el interés público (6.1.e), valorar los motivos de la situación particular de la persona y responder; si procede, dejar de tratar ese dato | El art. 21.1 se aplica a los tratamientos basados en el 6.1.e |
| **Limitación** (art. 18) | — | Marcar en el expediente y no usar los datos mientras se resuelve (p. ej. si se discute la exactitud). Eira **no tiene un estado de limitación propio** (ver `PLAN_V2.md`): el concello puede suspender el acceso de la persona y dejar constancia | No verificado en Eira: solo procedimiento manual |
| **Portabilidad** (art. 20) | La misma descarga JSON de «Acceso» | — | Por ley solo se aplica a lo que se basa en consentimiento o contrato (art. 20.1 y 20.3); Eira lo ofrece para todo |
| **No ser objeto de decisiones automatizadas** (art. 22) | — | En el alta con padrón, si no hay coincidencia, una persona revisa la solicitud: nunca se deniega automáticamente | `test_padron.py::test_no_match_goes_to_review_with_reason` |

## Menores

- Por debajo de los 14 años, los derechos los ejercen las personas tutoras desde «Familia».
- Con 14 años o más, la persona menor puede ejercerlos por sí misma (art. 7 LOPDGDD, para el consentimiento;
  para el resto de los derechos, que lo confirme el DPD).

## Modelo de respuesta

> Estimado/a ‹nombre›:
>
> En relación con su solicitud de ‹derecho› del ‹fecha›, le comunicamos que ‹descripción de lo realizado:
> «le adjuntamos sus datos en formato JSON» / «se ha eliminado su cuenta y sus reservas quedan
> anonimizadas» / …›.
>
> Si no está conforme, puede reclamar ante la Agencia Española de Protección de Datos
> (www.aepd.es). Para cualquier duda puede contactar con nuestro delegado/a de protección de datos en
> ‹correo del DPD›.
>
> ‹Concello, fecha y firma›
