<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Auditoría RXPD de Eira coa metodoloxía da AEPD

> **MODELO DE EXEMPLO — require revisión do DPD e dos servizos xurídicos do concello.**
> Esta auditoría describe o que fai o **código** de Eira (14/11/2026, versión 1.5.1). O responsable
> do tratamento é o concello; Eira achega a privacidade desde o deseño e a documentación.

## Como se fixo

**Referencias da AEPD** (títulos e versións comprobados en aepd.es o 14/11/2026, ver
[citas-verificadas.md](citas-verificadas.md)):

| Documento | Versión | Para que se usa aquí |
|---|---|---|
| «Gestión del riesgo y evaluación de impacto en tratamientos de datos personales» | xuño 2021 | Factores de risco (cap. VI.C) e medidas (cap. VIII) |
| «Listas de tipos de tratamientos de datos que requieren evaluación de impacto relativa a protección de datos (art 35.4)» | sen data no PDF | Se cada tratamento require EIPD (dous ou máis criterios) |
| «Guía de Privacidad desde el Diseño» | outubro 2019 | Estratexias: minimizar, ocultar, separar, abstraer, informar, controlar, cumprir, demostrar |
| Gestiona RGPD (ferramenta web, manual de abril 2024) | 2024 | Orde da análise: rexistro → factores de risco → medidas → EIPD |

**Do código, non da documentación:**
1. Un script percorreu os **84 modelos** de `apps/` e listou cada campo cun reconto das veces que
   se usa fóra do propio modelo (para atopar campos que non se usan).
2. Revisáronse a man as vistas, as purgas (`booking_maintenance`, `send_notices`), a
   configuración de rexistros (`LOGGING`, gunicorn, Caddy), os parámetros GET que le a app, as
   descargas (`Content-Disposition`), o service worker e o `localStorage`.
3. Cada medida liga co test que a comproba (`ficheiro::test`), se existe.

**Factores de risco da AEPD** (guía de 2021, cap. VI.C). Nas táboas úsanse estas siglas:
F1 operacións relacionadas cos fins · F2 tipos de datos · F3 extensión e alcance · F4 categorías de
interesados · F5 factores técnicos · F6 recollida e xeración de datos · F7 efectos colaterais ·
F8 categoría do responsable ou encargado · F9 comunicacións de datos.

**Criterios da lista de EIPD da AEPD** (art. 35.4): C1 perfís · C2 decisións automatizadas ·
C3 observación sistemática ou xeolocalización · C4 categorías especiais, penais, financeiros ou que
permitan inferilas · C5 biométricos · C6 xenéticos · C7 gran escala · C8 combinar bases de datos ·
C9 persoas vulnerables (inclúe **menores de 14 anos**) · C10 tecnoloxías novas · C11 impide
exercer un dereito ou acceder a un servizo. **Dous ou máis criterios → EIPD na maioría dos casos.**

## Resumo

| # | Tratamento | Base (art. 6 e 9 RXPD) | Onde | Conservación | Fóra da UE | Criterios AEPD | EIPD |
|---|---|---|---|---|---|---|---|
| 1 | Reservas | 6.1.e; 6.1.b se hai pagamento | Servidor | 24 meses, despois anonimizada | Ningunha | — | Non |
| 2 | Alta con padrón | 6.1.e | Servidor (só HMAC do padrón) | DNI/data: ata resolver; solicitude 12 meses | Ningunha | C2, C8 | **Recomendable** |
| 3 | Pagamentos | 6.1.c e 6.1.e | Servidor (sen datos de tarxeta) | 6 anos (non verificado: sen purga) | Ningunha | C4 (só importe) | Non |
| 4 | Control de acceso | 6.1.e | Servidor | 24 meses | Ningunha | C3 (débil) | Non |
| 5 | Incidencias e alertas | 6.1.e | Servidor | Pechadas: 24 meses, despois sen persoa nin foto | Ningunha | — | Non |
| 6 | Accidentes | 6.1.c e 6.1.e | Servidor | 24 meses despois de pechado (configurable) | Ningunha | C4 (inferencia), C9 | **Si** (xa hai plantilla) |
| 7 | Saúde: consellos | 9.2.a (consentimento explícito) | **Dispositivo**; servidor só se a persoa o pide | Ata retirar o consentimento | Ningunha | C4 | **Si** |
| 8 | Saúde: RPE, probas e observatorio | 6.1.e; menores: consentimento da familia | Servidor; observatorio só agregado | Tempada + 1 ano (non verificado: sen purga) | Ningunha | C4, C9 | **Si** |
| 9 | Menores e persoas titoras | 6.1.e; consentimento (art. 7 LOPDGDD) | Servidor | Mentres teña a conta | Ningunha | C9 | **Si** (con 8) |
| 10 | Carné con foto | 6.1.e; foto: consentimento | Servidor | Mentres teña a conta | Ningunha | — | Non |
| 11 | Partidas abertas | 6.1.a | Servidor | Coa reserva (24 meses); denuncias 12 meses | Ningunha | — | Non |
| 12 | Procedencia | 6.1.e e art. 89 | Servidor; só agregado | Mentres teña a conta | Ningunha | C8 (débil) | Non (revisar na EIPD) |
| 13 | NPS e valoracións | 6.1.e | Servidor | Comentario 24 meses; enquisa: persoa e comentario 24 meses | Ningunha | — | Non |
| 14 | Avisos (correo, Telegram, push) | 6.1.e / 6.1.b; informativos 6.1.a | Servidor | 12 meses | **Telegram, se a persoa o vincula** | — | Non |
| 15 | Dobre factor e auditoría | 6.1.c (art. 32 RXPD, ENS) | Servidor | 24 meses (12–120) | Ningunha | — | Non |
| 16 | Acceso de soporte da deputación | 6.1.e + contrato art. 28 | Servidor | 24 h; rexistro 24 meses | Ningunha | — | Non |
| 17 | Textos legais e consentimentos | 6.1.c e 6.1.a | Servidor | O que fixe o concello | Ningunha | — | Non |
| 18 | Acreditación de monitoras | 6.1.c (LOPIVI, art. 57) | Servidor: **só quen e cando** | Ata retirar a marca | Ningunha | — (sen datos penais) | Non |

**Transferencias fóra da UE:** **ningunha cos datos das contas**. Hai tres excepcións que debe
coñecer o concello: (a) **Telegram**, provedor de fóra do EEE, só se a persoa vincula o bot
(voluntario; sempre hai app e correo); (b) **as teselas do mapa**, que por defecto veñen de
`tile.openstreetmap.org` (Fundación OpenStreetMap, Reino Unido): o navegador envía o seu enderezo IP
ao ver o mapa; o concello pode poñer o seu servidor de teselas en «Configuración → Mapa»; (c)
**push real**: o adaptador incluído é simulado; un adaptador real enviaría a mensaxe cifrada
(RFC 8291) ao servizo de push do navegador (Google, Mozilla ou Apple). Ver «Ocos».

## Ocos atopados e que se fixo

| # | Oco | Onde | Arranxo | Test |
|---|---|---|---|---|
| O1 | **Prazos sen purga automática.** A documentación prometía 2 anos (reservas, acceso, incidencias, valoracións, limpeza) e 1 ano (denuncias de partidas), pero ningún código os aplicaba. Tampouco había prazo para os códigos de entrada (levan o correo), as sesións caducadas, as invitacións de empadroamento, as altas pendentes da tableta (correo da familia) nin as respostas das enquisas | `apps/*/models.py` | **Corrixido:** `apps/accounts/retention.py`, executado por `booking_maintenance`. O que serve para contabilidade ou estatística queda anonimizado; o resto bórrase. Prazos configurables (`EIRA_RETENTION`) e constancia en AuditLog (`retention.purge`, só cifras) | `apps/accounts/tests/test_retention.py` (9 tests) |
| O2 | **O service worker gardaba páxinas con datos persoais** (as miñas reservas, a lista do grupo na tableta, coa xente menor) e **non as borraba ao saír**. Nun dispositivo compartido, a seguinte persoa podía velas sen rede | `templates/core/sw.js` | **Corrixido:** ao saír, `Clear-Site-Data: "cache"`; e `eira.js` borra a caché de páxinas se cambia a persoa ou non hai sesión (`data-cache-owner`) | `test_rgpd_device.py` e E2E `test_rgpd.py::test_cached_pages_are_forgotten_on_logout` |
| O3 | **Ao eliminar a conta quedaban textos libres nas reservas:** nomes doutras persoas (`participant_names`), notas e a foto do estado ao entrar | `apps/accounts/views.py::delete_user` | **Corrixido:** bórranse tamén eses campos e a foto | `test_retention.py::test_account_deletion_also_clears_free_text_of_bookings` |
| O4 | **Texto libre onde se pode colar un dato de saúde** («mancou o nocello») sen ningún aviso: 8 formularios e 3 campos escritos a man | notas de peche e de entrada, valoración, partida, incidencia, peche de orde, limpeza, enquisa, nota á persoa | **Corrixido:** aviso «Non escribas datos de saúde nin datos persoais doutras persoas» ao pé de cada campo (`apps/accounts/freetext.py`). As notas de peche quedan limitadas a 500 caracteres | `test_retention.py::test_free_text_fields_warn_against_health_data` (8) e `test_hand_written_textareas_carry_the_warning` |
| O5 | **Cita legal derrogada:** a acreditación citaba o art. 13.5 da LO 1/1996, suprimido pola LOPIVI en 2021 | interface, LEEME, `rat.md`, `acreditacion-menores.md` | **Corrixido:** «LO 8/2021, LOPIVI, art. 57» | `test_accreditation.py` (pantalla) |
| O6 | **Os rexistros dos contedores** (levan enderezos IP no log de acceso de gunicorn) non tiñan límite no `docker-compose.yml` local | `docker-compose.yml` | **Corrixido:** rotación 3 × 10 MB. Na demo en liña, Caddy (`deploy/demo/sitio.caddy`) rexistra o acceso coa IP, gunicorn só ve o proxy, e os rexistros de todos os contedores rotan en 3 × 10 MB (comprobado no servidor o 14/11/2026) | — (configuración) |
| O7 | Campos que non se usan: `GameReport.reviewed_at` (nunca se escribe) e `User.last_login` (Django actualízao, Eira non o le) | modelos | **Pendente** (PLAN_V2): decidir se se usan (revisión de denuncias; aviso de contas inactivas) ou se deixan de gardar | — |
| O8 | Pagamentos (6 anos) e asistencia/RPE (tempada + 1 ano) seguen sen purga | `bookings.Payment`, `activities.Attendance` | **Pendente** (PLAN_V2): as dúas dependen da contabilidade e das tempadas de cada concello; borrar sen regra clara sería peor | — |
| O9 | Teselas do mapa por defecto en OpenStreetMap (IP ao Reino Unido) | `EIRA_TILE_URL` | **Pendente** (PLAN_V2): mapa que se carga ao tocalo ou teselas da deputación por defecto | `test_security.py::test_tile_provider_per_municipality_goes_to_csp` (configurable) |
| O11 | **A descarga dos datos propios (art. 15) estaba incompleta:** non levaba carné e abonos, bonos, valoracións, partidas abertas nin preferencias de avisos | `apps/accounts/views.py::export_user_data` | **Corrixido:** engadidos | `test_rgpd_export.py` (2 tests) |
| O10 | Os textos libres só levan aviso: non se detecta automaticamente un dato de saúde | formularios | **Pendente** (PLAN_V2, baixa) | — |

**Revisado sen ocos:**
- **Rexistros da aplicación:** non hai ningún `logger` nin `print` con datos persoais en `apps/`
  (busca no código); `django.db.backends` está en WARNING (as consultas non se rexistran).
- **Datos nos URL:** os parámetros GET que le a app son filtros (datas, instalación, formato,
  páxina). Os tokens dos URL (`entrada/<token>`, `limpeza/<token>`, `peche/<token>`) son aleatorios
  e non levan datos persoais. A única excepción é a bandexa de correo simulada (`/dev/correo/?para=`),
  que só existe coa demo activada (`test_security.py::test_dev_tools_disabled_in_production_settings`).
- **Exportacións:** toda descarga do persoal (`attachment`) queda en AuditLog (`export.download`)
  polo middleware `ExportAuditMiddleware` (`test_auditlog.py::test_staff_downloads_are_audited`).
  As de datos persoais da deputación precisan acceso de soporte
  (`test_support_access.py::test_personal_export_needs_support`).
- **Cookies:** só técnicas (`test_privacy.py::test_only_technical_cookies`).

## Tratamentos

Formato de cada un, coma en Gestiona RGPD: **1. Rexistro** (finalidade, base, datos e campos) →
**2. Factores de risco e medidas** → **3. EIPD**.

### 1. Reservas
**Finalidade:** xestionar o uso das instalacións municipais. **Base:** art. 6.1.e RXPD (competencia
municipal en deporte, Lei 7/1985, art. 25.2.l) e 6.1.b se hai pagamento. **Interesados:** veciñanza
e persoas doutros concellos da rede. **Destinatarios:** persoal de mantemento (só instalación e
hora); concello de destino nas reservas da rede (só o imprescindible). **Onde:** servidor.

| Campo (`bookings.Booking`) | Por que fai falta |
|---|---|
| `user` | Saber de quen é a reserva e mandarlle os avisos |
| `facility`, `start`, `end`, `status`, `reference` | A reserva en si |
| `holder_name`, `holder_phone` | Só nas reservas feitas no mostrador para alguén sen conta |
| `participants`, `participant_names` (opcional) | Aforo; os nomes só se a persoa os escribe |
| `price_cents`, `paid_cents`, `refunded_cents`, `base_price_cents`, `discount_pct`, `lighting_cents`, `tariff_audience`, `payment_method`, `payment_reference`, `voucher` | Cobro e conciliación |
| `rules_version`, `rules_accepted_at` | Proba de que aceptou as normas vixentes |
| `checked_in_at`, `closed_at`, `close_*_ok`, `close_notes`, `close_unconfirmed` | Checklist de peche e seguridade da instalación |
| `start_state_*` (texto e foto opcional sen EXIF) | Estado ao entrar, para non culpar a quen chega |
| `network_origin` | Tarifa de non empadroada nas reservas da rede |
| `approved_at`, `decided_by`, `decision_reason`, `requested_start` | Reservas que require aprobación |
| `reminder_24_at`, `reminder_2_at`, `attendance_confirmed_at`, `hold_expires_at` | Recordatorios e liberar prazas sen pagar |

**Conservación:** 24 meses despois de rematar; despois **anonimizada** (sen persoa, nomes, notas nin
foto; quedan data, instalación e importe para a contabilidade e as estatísticas) — **novo**
(`retention.purge_bookings`).

| Factor | Risco | Medida de Eira | Test |
|---|---|---|---|
| F4, F9 | O concello de destino da rede ve datos de máis | Só nome para mostrar e concello de orixe | `test_v5_network.py::test_destination_staff_sees_only_what_is_needed` |
| F7 | O persoal de mantemento coñece hábitos | A orde de traballo só leva instalación e hora | `test_privacy.py::test_operator_never_sees_reporter_contact` |
| F3 | Conservación indefinida | Anonimización aos 24 meses | `test_retention.py::test_old_bookings_are_anonymised_and_recent_ones_kept` |
| F6 | Texto libre con datos de saúde | Aviso no campo; 500 caracteres | `test_retention.py::test_free_text_fields_warn_against_health_data` |

**EIPD:** non (ningún criterio).

### 2. Alta con padrón
**Finalidade:** dar a app e a tarifa de veciñanza a quen está empadroado. **Base:** 6.1.e (ordenanza
fiscal e servizo de deportes). **Onde:** servidor; **o padrón non se garda**.

| Campo | Por que | Canto tempo |
|---|---|---|
| `AppRequest.name`, `surnames`, `email`, `birth_year`, `postcode`, `channel` | Contestar a solicitude | 12 meses (purga xa existente) |
| `AppRequest.id_number`, `birth_date`, `address` | Contrastar co padrón | **Ata resolver** (bórranse ao momento) |
| `PadronEntry.digest` | HMAC-SHA256 de «concello · DNI/NIE · data» co segredo da instancia: permite casar sen gardar o padrón | Ata a seguinte carga |
| `PadronEntry.parish` | Parroquia (opcional) para a procedencia agregada | Ata a seguinte carga |
| `Residency.method`, `validated_at`, `revoked_at` | Proba do empadroamento (si/non) | Mentres teña a conta |
| `ResidencyInvitation.code`, `email`, `note` | Código de empadroamento dado no mostrador | Sen usar: 1 mes despois de caducar (**novo**) |

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F2, F9 | Copia do padrón fóra do concello | Só HMAC; o CSV procésase en memoria | `test_padron.py::test_import_keeps_only_hmac_and_logs`, `test_original_csv_is_not_kept` |
| F1 | Casar pola persoa equivocada | Nunca polo nome; DNI/NIE + data | `test_padron.py::test_name_is_never_used_for_matching` |
| F7 | Decisión automática que deixa fóra | Sen coincidencia → revisión manual co motivo, non denegación | `test_padron.py::test_no_match_goes_to_review_with_reason` |
| F3 | DNI gardado de máis | Bórrase ao resolver | `test_padron.py::test_resolution_forgets_identity` |

**EIPD: recomendable.** Cumpre C2 (a alta e a tarifa decídense automaticamente se hai coincidencia)
e C8 (combina o padrón co rexistro da app). Mitigado pola revisión humana cando non hai coincidencia.

### 3. Pagamentos
**Base:** 6.1.c (normativa tributaria) e 6.1.e. **Onde:** servidor; **a tarxeta só a ve a pasarela da
entidade financeira**.

Campos (`bookings.Payment`): `concept`, `amount_cents`, `refunded_cents`, `status`, `method`,
`reference`, `provider_code`, `signature_ok`, `recorded_by`, `created_at`, `resolved_at` e a ligazón
á reserva, inscrición, bono ou abono. Ningún número de tarxeta nin IBAN.

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F5 | Confirmar un pago falso | Notificación asinada servidor a servidor; a URL de volta non confirma nada | `test_payments.py::test_notification_endpoint_checks_signature`, `test_return_url_alone_confirms_nothing` |
| F9 | Exportar datos bancarios | A conciliación só leva referencia, importe e estado | `test_payments.py::test_payments_conciliation_export` |

**Conservación:** 6 anos. **Non verificado:** non hai purga automática (O8). **EIPD:** non.

### 4. Control de acceso
**Base:** 6.1.e. Campos: `AccessEvent.facility`, `booking`, `user`, `kind`, `at`, `detail`;
`KeyHandover` (entrega e devolución da chave); `LockDevice` (sen datos persoais). Os códigos de
porta calcúlanse sen conexión e non se gardan.

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F3 | Seguimento de entradas e saídas | Só eventos da reserva; 24 meses (**novo**) | `test_retention.py::test_short_lived_records_are_deleted` |
| F5 | Códigos adiviñables | TOTP por franxa, só válido na súa hora | `test_offline_codes.py` (14 tests) |

**EIPD:** non (C3 débil: non hai observación sistemática nin xeolocalización).

### 5. Incidencias e alertas
**Base:** 6.1.e. Campos: `Incident.reporter`, `category`, `description`, `photo` (sen EXIF),
`status`, datas e `resolution_note`; `Alert.kind`, `origin`, `facility`, `raised_by`, `notified`
(só o **posto** de quen recibiu o aviso).

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F6 | A foto leva GPS | Reencodada sen EXIF | `test_incidents.py::test_report_with_photo_strips_exif` |
| F4 | O persoal ve quen avisou | O operario non ve o contacto | `test_privacy.py::test_operator_never_sees_reporter_contact` |
| F3 | Conservación indefinida | Pechadas: aos 24 meses sen persoa nin foto (**novo**) | `test_retention.py::test_comments_and_reporters_lose_the_person` |
| F6 | Saúde no texto | Aviso no campo (**novo**) | `test_retention.py::test_free_text_fields_warn_against_health_data` |

**EIPD:** non.

### 6. Accidentes
**Base:** 6.1.c e 6.1.e (seguridade das instalacións). Campos (`safety.AccidentReport`):
`occurred_at`, `facility`, `kind` (tipo xeral), `severity` (**percibida**), `called_112`,
`reporter_role`, `reported_by`, `facility_related`, `closed_at`. **Sen diagnósticos nin texto libre.**

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F2 | Inferir saúde | Sen texto libre nin lesións | `test_alert_profiles.py::test_accident_register_is_unchanged_no_free_text`, `test_safety.py::test_accident_register_minimal_data_and_access` |
| F3 | Conservación | 24 meses despois de pechado, configurable; purga | `test_safety.py::test_accident_retention_purges_only_closed_old` |
| F9 | Policía Local | Ningún envío automático | `test_safety.py::test_escalation_reminders_then_contact_never_police` |

**EIPD: si** (C4 por inferencia e C9 se a persoa é menor). Xa hai plantilla: [eipd-plantilla.md](eipd-plantilla.md).

### 7. Saúde: consellos persoais
**Base:** art. 9.2.a (consentimento explícito). **Onde: no dispositivo** (`localStorage`,
`eira-health-v1`); no servidor só se a persoa o pide.

Campos (`accounts.HealthProfile`): `weight_kg`, `age`, `weekly_minutes`, `consent_version`,
`consent_at`. Fan falta para calcular auga e enerxía; nada máis.

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F2 | Categoría especial no servidor | Por defecto non se envía nada | `test_health.py::test_health_page_works_without_account_and_sends_nothing` |
| F1 | Consentimento implícito | Só con consentimento explícito | `test_health.py::test_store_requires_explicit_consent` |
| F4 | O persoal veo | Nunca, nin no admin técnico | `test_health.py::test_owner_sees_profile_in_booking_but_staff_never`, `test_health_not_in_admin_site` |
| F3 | Queda ao marchar | Bórrase coa conta e ao retirar o consentimento | `test_health.py::test_account_deletion_removes_health`, `test_legal.py::test_withdraw_revocable_and_effects` |

**EIPD: si** (C4). Plantilla existente.

### 8. Saúde: RPE, probas físicas e observatorio
**Base:** 6.1.e; para menores, consentimento da familia para o esforzo e as probas
(`Consent.Kind.PERFORMANCE`). Campos: `Attendance.present`, `rpe`, `minutes`, `checked_in_at`,
`auto_in`; `FitnessResult.test`, `date`, `value`, `recorded_by`; `Enrollment.pseudonym` (HMAC).

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F4 | Menores | Sen consentimento non se rexistra o esforzo | `test_activities.py::test_minor_needs_data_consent` |
| F9 | Observatorio identifica | Só agregado, n ≥ 10; microdatos seudonimizados e só para o concello | `test_activities.py::test_observatory_threshold`, `test_microdata_is_pseudonymised_and_admin_only` |
| F4 | A monitora ve outros grupos | Só os seus | `test_activities.py::test_monitor_only_sees_own_groups` |

**Conservación:** tempada + 1 ano. **Non verificado:** sen purga automática (O8).
**EIPD: si** (C4 e C9). Plantilla existente.

### 9. Menores e persoas titoras
**Base:** 6.1.e; consentimento da familia por debaixo dos 14 anos (art. 7 LOPDGDD). Campos:
`Household.responsible`, `Dependent.first_name`, `birth_year`; `Consent.kind`, `granted_by`,
`text_version`, `granted_at`, `revoked_at`; `Enrollment.surnames` (achégaos o concello);
`PendingParticipant.first_name`, `birth_year`, `guardian_email` (alta pendente na tableta).

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F4 | Consentimento do menor | < 14 consente a familia; ≥ 14 a familia confirma o acordo | `test_privacy.py::test_under_14_family_consents_14_plus_needs_minor_agreement` |
| F2 | Apelidos na tableta | Só nome e primeiro apelido | `test_activities.py::test_minor_enrollment_requires_surnames` |
| F3 | Correo da familia nunha alta pendente | 3 meses (**novo**) | `test_retention.py::test_short_lived_records_are_deleted` (regra `pending_participants`) |
| F7 | Dispositivo compartido (tableta) | A caché de páxinas bórrase ao cambiar de persoa (**novo**) | `test_rgpd_device.py` |

**EIPD: si**, xunto co tratamento 8.

### 10. Carné con foto
**Base:** 6.1.e; a foto é opcional. Campos (`members.MemberCard`): `number`, `photo` (sen
metadatos), `version`, `external_id` (número doutro carné municipal, opcional). O QR só leva o
identificador interno, a versión e a caducidade.

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F5 | QR copiado | O dixital caduca aos 3 minutos; o impreso revógase | `test_members.py::test_live_qr_expires_and_print_qr_can_be_revoked` |
| F2 | Foto como biométrico | Non se usa para recoñecemento (non é C5) | — |

**EIPD:** non.

### 11. Partidas abertas
**Base:** 6.1.a (consentimento ao publicar e ao unirse). Campos: `OpenGame.spots`, `level`,
`message` (140 caracteres), `consent_at`; `GameJoin.user`, `status`, `consent_at`;
`GameMessage.code` (só mensaxes predefinidas); `GameReport.reason`.

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F9 | Intercambio de contactos | Sen chat libre; só nome de pila e inicial | `test_v12_open_games.py::test_public_name_is_first_name_and_initial`, `test_list_shows_no_contact_data_and_price_split` |
| F4 | Menores | < 14 non poden publicar nin unirse | `test_v12_open_games.py::test_publish_requires_consent_and_14`, `test_under_14_cannot_join` |
| F3 | Denuncias indefinidas | 12 meses (**novo**); a partida morre coa reserva (24 meses) | `test_retention.py::test_short_lived_records_are_deleted` |

**EIPD:** non.

### 12. Procedencia
**Base:** 6.1.e con garantías do art. 89 (fins estatísticos). Campos: `User.residence_parish`,
`residence_municipality`; `PadronEntry.parish`. Nunca GPS nin enderezo.

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F2 | Xeolocalización | Ningún campo de GPS nin xeolocalización do navegador | `test_provenance.py::test_no_gps_fields_or_browser_geolocation` |
| F7 | Reidentificar por restas | n ≥ 10 persoas despois de cada filtro; sen datas libres | `test_provenance.py::test_lone_person_cannot_be_found_by_narrowing_or_subtraction`, `test_free_filters_are_rejected` |

**EIPD:** non obrigatoria; o risco residual de comparar períodos está descrito en
[matriz.md](matriz.md) e debe revisalo o DPD.

### 13. NPS e valoracións
**Base:** 6.1.e. Campos: `Rating.score`, `tags`, `comment`, `incident`; `UseNps.score`;
`SurveyResponse.user` (para responder unha vez), notas por aspecto e `comment`.

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F4 | O concello sabe quen opinou | Comentarios sen nome; resultados con n ≥ 10 | `test_ratings.py::test_admin_ratings_view_hides_names_and_ranks`, `test_surveys.py::test_results_only_aggregated_with_ten` |
| F3 | Comentario e persoa indefinidos | 24 meses: comentario fóra; na enquisa tamén a persoa (**novo**) | `test_retention.py::test_comments_and_reporters_lose_the_person`, `test_survey_answers_lose_person_and_comment` |

**EIPD:** non.

### 14. Avisos (correo, Telegram e push)
**Base:** 6.1.e (servizo) e 6.1.b se afecta a unha reserva; os informativos, 6.1.a. Campos:
`Notification.title`, `body`, `url`, `channels`, `read_at`; `NoticePreference.matrix`,
`comms_consent_at`; `User.telegram_chat`, `notify_email`, `notify_telegram`; `TelegramLink.code`;
`PushSubscription.endpoint`, `keys`.

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F1 | Informativos sen consentimento | Non se envían por ningunha canle | `test_notices.py::test_informative_notice_is_not_sent_without_consent` |
| F9 | Transferencia (Telegram) | Voluntaria; código dun só uso de 30 minutos | `test_notices.py::test_bot_linking_with_single_use_code`, `test_bot_code_expires` |
| F3 | Avisos antigos | 12 meses | `test_notices.py::test_purge_applies_retention` |
| F6 | Seguimento de aperturas | Non hai píxeles nin ligazóns de seguimento | — (non verificado por test) |

**EIPD:** non.

### 15. Dobre factor e rexistro de auditoría
**Base:** 6.1.c (art. 32 RXPD e ENS). Campos: `TwoFactorDevice.secret` (cifrado con Fernet),
`confirmed_at`, `last_step`; `RecoveryCode.code_hash` (HMAC); `AuditLog.at`, `actor`, `action`,
`object_type`, `object_id`, `detail`.

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F5 | Conta de xestión roubada | TOTP obrigable para administración e DPD | `test_twofactor.py::test_council_can_require_it_for_admin_and_dpo` |
| F8 | Ver o rexistro doutros | Só administración e DPD do concello; a deputación nunca | `test_auditlog.py::test_region_cannot_even_with_support_access` |

**Conservación:** 24 meses (12–120), purga. **EIPD:** non.

### 16. Acceso de soporte da deputación
**Base:** 6.1.e e contrato de encargo (art. 28). Campos (`tenants.SupportAccess`): `region`,
`reason`, `granted_by`, `granted_at`, `expires_at`, `revoked_at`, `first_used_at`.

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F8, F9 | A deputación ve datos persoais | Por defecto só agregados; acceso autorizado polo concello, 24 h, revogable, cada páxina en AuditLog | `test_support_access.py::test_aggregate_always_personal_needs_support_then_expires`, `test_revoke_and_still_read_only` |

**EIPD:** non.

### 17. Textos legais e consentimentos
**Base:** 6.1.c (xustificar a información e o consentimento) e 6.1.a. Campos
(`legal.LegalAcceptance`): `user`, `version`, `accepted_at`, `channel`, `withdrawn_at`.

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F1 | Retirar é difícil | Retirada nun paso, co efecto aplicado | `test_legal.py::test_withdraw_revocable_and_effects` |
| F3 | Rexistro ao eliminar a conta | Queda sen persoa | `test_legal.py::test_export_and_account_deletion_keep_register_without_person` |

**EIPD:** non.

### 18. Acreditación de monitoras
**Base:** 6.1.c (LO 8/2021, LOPIVI, art. 57). Campos (`activities.MinorsAccreditation`): `user`,
`confirmed_by`, `confirmed_at`, `review_notified_at`. **Sen certificado nin datos penais.**

| Factor | Risco | Medida | Test |
|---|---|---|---|
| F2 | Datos penais (art. 10 RXPD) | Non hai campo para o certificado nin o resultado | `test_accreditation.py::test_allowed_after_confirm_and_only_who_and_when_stored` |
| F8 | A deputación marca | Nunca, nin co acceso de soporte | `test_accreditation.py::test_region_cannot_mark_even_with_support` |

**EIPD:** non.

## Gestiona RGPD

A ferramenta é unha páxina web da AEPD (`gestiona2.aepd.es`) que, segundo o seu manual, traballa
no navegador sen enviar datos. **Non se usou nesta auditoría:** é unha aplicación interactiva longa
(rexistro, factores, ata 800 medidas) e automatizala co navegador das probas levaría máis tempo
ca o que quedaba antes da entrega; o manual non describe un modo sen conexión. Esta táboa segue a
mesma orde (rexistro → factores → medidas → EIPD), así que o concello pode pasala á ferramenta.
Ver `docs/DECISIONS.md`.
