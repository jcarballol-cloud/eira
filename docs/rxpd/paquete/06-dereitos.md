<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Procedemento para atender os dereitos (arts. 12 a 22 RXPD; arts. 12 a 18 LOPDGDD)

> **MODELO DE EXEMPLO — require revisión do DPD e dos servizos xurídicos do concello.**

## Regras comúns

- **Prazo:** contestar **sen dilación indebida e como máximo nun mes** desde a solicitude;
  prorrogable outros dous meses se é complexa, avisando dentro do primeiro mes (art. 12.3).
- **Gratuíto** (art. 12.5 RXPD; cita **non verificada** no contraste do 14/11/2026).
- **Identificación:** se a persoa o fai desde a súa conta de Eira, xa está identificada. Se o fai por
  escrito ou no mostrador, o concello pode pedir o mínimo para identificala (nunca máis datos dos
  que xa ten).
- **Canles:** desde a propia app (a maioría dos dereitos) ou por escrito ao concello ou ao DPD
  (‹correo do DPD›, rexistro electrónico).
- **Rexistro:** anotar a data de entrada, a resposta e a data de resposta. As accións feitas desde
  a app quedan no rexistro de auditoría (descarga dos datos propios, eliminación da conta).
- **Reclamación:** sempre hai que lembrar o dereito a reclamar ante a Axencia Española de
  Protección de Datos.

## Cada dereito en Eira

| Dereito | Que pode facer a persoa soa, na app | Que fai o concello | Notas |
|---|---|---|---|
| **Acceso** (art. 15) | «A miña conta → Descargar todos os meus datos (JSON)» (`/conta/os-meus-datos.json`): conta, saúde gardada, roles, empadroamento, reservas, incidencias, familia e consentimentos, inscricións, avisos recibidos, procedencia e documentos aceptados. Tamén carné, abonos, bonos, valoracións, partidas abertas e preferencias de avisos. «Quen custodia os teus datos» explica quen ve cada dato | Se o pide por escrito, xerar a mesma descarga coa persoa identificada | A descarga queda en AuditLog (`account.export`) |
| **Rectificación** (art. 16) | «A miña conta»: nome para mostrar, teléfono, ano de nacemento, idioma, procedencia; «Familia»: menores | Corrixir no panel o que a persoa non pode cambiar (colectivo de tarifa, empadroamento, apelidos dos menores) | Informar a quen se comunicaron os datos (art. 19) |
| **Supresión** (art. 17) | «A miña conta → Eliminar a conta» (`/conta/eliminar/`): bórrase a conta, a saúde gardada, o carné, as preferencias e a procedencia; as reservas quedan **anonimizadas** (sen persoa, nomes, notas nin foto) para a contabilidade | Revisar se hai algo que deba conservarse por obriga legal (pagamentos) e bloquealo fóra do uso ordinario (art. 32 LOPDGDD) | `test_retention.py::test_account_deletion_also_clears_free_text_of_bookings`; `test_health.py::test_account_deletion_removes_health` |
| **Retirar un consentimento** (art. 7.3) | «Documentos aceptados», «Privacidade» (imaxe), «A miña saúde» (borrar os datos), «Familia» (consentimentos de cada menor), preferencias de avisos | — | Ten efecto ao momento: imaxe → retírase a autorización; saúde → bórranse os datos |
| **Oposición** (art. 21) | Para o opcional: desmarcar avisos informativos, borrar a procedencia, deixar unha partida aberta | Para o que se basea no interese público (6.1.e), valorar os motivos da situación particular da persoa e responder; se procede, deixar de tratar ese dato | O art. 21.1 aplícase aos tratamentos baseados no 6.1.e |
| **Limitación** (art. 18) | — | Marcar no expediente e non usar os datos mentres se resolve (p. ex. se se discute a exactitude). Eira **non ten un estado de limitación propio** (ver `PLAN_V2.md`): o concello pode suspender o acceso da persoa e deixar constancia | Non verificado en Eira: só procedemento manual |
| **Portabilidade** (art. 20) | A mesma descarga JSON de «Acceso» | — | Por lei só se aplica ao que se basea en consentimento ou contrato (art. 20.1 e 20.3); Eira ofréceo para todo |
| **Non ser obxecto de decisións automatizadas** (art. 22) | — | Na alta con padrón, se non hai coincidencia, unha persoa revisa a solicitude: nunca se denega automaticamente | `test_padron.py::test_no_match_goes_to_review_with_reason` |

## Menores

- Por debaixo dos 14 anos, os dereitos exércenos as persoas titoras desde «Familia».
- Con 14 anos ou máis, a persoa menor pode exercelos por si (art. 7 LOPDGDD, para o consentimento;
  para o resto dos dereitos, que o confirme o DPD).

## Modelo de resposta

> Estimado/a ‹nome›:
>
> En relación coa súa solicitude de ‹dereito› do ‹data›, comunicámoslle que ‹descrición do feito:
> «achegámoslle os seus datos en formato JSON» / «eliminouse a súa conta e as súas reservas quedan
> anonimizadas» / …›.
>
> Se non está conforme, pode reclamar ante a Axencia Española de Protección de Datos
> (www.aepd.es). Para calquera dúbida pode contactar co noso delegado/a de protección de datos en
> ‹correo do DPD›.
>
> ‹Concello, data e sinatura›
