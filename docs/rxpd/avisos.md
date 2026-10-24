# Avisos do concello: base xurídica por tipo

Documento de traballo para o delegado/a de protección de datos (DPD) do concello. Acompaña á actividade 12 do [rexistro de actividades de tratamento](rat.md).
Non é asesoramento xurídico: cada concello debe revisalo co seu DPD.

## Resumo

| Categoría | Exemplos | Base xurídica | Quen o recibe | Precisa consentimento? |
|---|---|---|---|---|
| **Peches** | Peche do pavillón por obras, piscina pechada pola mañá | Art. 6.1.e RXPD (servizo público deportivo, Lei 7/1985 art. 25.2.l). Se cancela unha reserva, tamén 6.1.b (relación co servizo) | Quen ten reserva afectada; ou toda a veciñanza se é xeral | **Non**. Chega sempre na app a quen lle afecta; correo e Telegram segundo as súas preferencias |
| **Alertas** | Alerta amarela por vento con cancelación das pistas exteriores | 6.1.e e, se hai cancelación, 6.1.b. Interese vital (6.1.d) só en emerxencias reais | Quen ten reserva afectada (exteriores, unha instalación ou unha parroquia) | **Non** |
| **Horarios** | Horario de Nadal, horario de outono | Consentimento, 6.1.a | Quen aceptou as comunicacións informativas | **Si** |
| **Actividades e inscricións** | Abertas as inscricións de multideporte; cambio de sala | Consentimento, 6.1.a. Se só van ás persoas inscritas e son da súa actividade (cambio de sala), poden entenderse como servizo (6.1.e); en Eira tratámolas como informativas por prudencia | Quen aceptou e, se se segmenta, as persoas inscritas | **Si** |
| **Festas e eventos** | Festas patronais, carreira popular | Consentimento, 6.1.a | Quen aceptou | **Si** |
| **Novidades** | Nova pista de pádel | Consentimento, 6.1.a | Quen aceptou | **Si** |

## Regras que aplica o código (`apps/notifications/notices.py`)

1. **Sen consentimento, ningún informativo.** Se a persoa non aceptou as comunicacións informativas, non se lle envía nada destas categorías: nin na app, nin correo, nin Telegram, nin push.
   - Pode velos ela mesma no **Taboleiro do concello** da pantalla Avisos. Consultar non é un envío.
   - Test: `test_informative_notice_is_not_sent_without_consent`.
2. **Os de servizo chegan sempre á app de quen lle afecta**, aínda que silenciase a categoría.
   - As outras canles seguen as súas preferencias.
   - Tests: `test_service_notice_reaches_affected_people_without_consent` e `test_service_notice_keeps_app_even_if_muted`.
3. **Matriz categoría × canle.** A persoa escolle por onde recibe cada categoría (app, correo, Telegram, push).
4. **Segmentación só con datos que o servizo xa ten:**
   - reservas nunha franxa e instalación;
   - instalacións descubertas;
   - inscricións nunha actividade;
   - parroquia da instalación reservada.

   Non se crean perfís nin se cruzan datos doutras fontes.
5. **Cancelacións:** un peche ou alerta pode cancelar as reservas afectadas. Créase o peche correspondente e devólvese o importe íntegro (mesmo fluxo ca en «Peches»).
6. **Programados:** gárdanse e envíaos a orde `manage.py send_notices` (cron ou temporizador de systemd) cando chega a hora. Un aviso enviado non se volve enviar.

## Telegram

- **Canle pública** do concello (p. ex. `@eira_demo_vilardeiras` na demo, nome ficticio): vai sen datos persoais. Calquera pode seguila sen conta en Eira.
- **Bot persoal:**
  - A persoa vincúlao voluntariamente cun código dun só uso que caduca en 30 minutos (ligazón `t.me/<bot>?start=<código>`).
  - Só se garda o identificador do chat. `/stop` desvincula.
  - Telegram é un provedor de fóra do EEE. Ofrécese como opción e a app e o correo seguen dispoñibles.
- **Token do bot:** só na variable de contorno `EIRA_TELEGRAM_TOKEN` do servidor. Nunca no repositorio, na documentación nin na base de datos.
  - O webhook (`/telegram/webhook/<segredo>/`) só existe se se define `EIRA_TELEGRAM_WEBHOOK_SECRET`.

## Texto informativo (resumo para a app)

> **Avisos do concello.** Responsable: o concello. Os peches e alertas que afectan ás túas reservas envíanse para prestar o servizo (art. 6.1.e RXPD). Os horarios, actividades, festas e novidades só se che envían se o aceptas (art. 6.1.a), e podes retiralo cando queiras en Avisos › Preferencias.
> Gardamos as túas preferencias e, se vinculas Telegram, o identificador do chat. Os avisos recibidos consérvanse 12 meses.
> Dereitos: acceso, rectificación, supresión, oposición e limitación ante o concello; reclamación ante a AEPD.
