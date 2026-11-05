<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Plantilla de avaliación de impacto relativa á protección de datos (EIPD)

> **Para que serve:** o art. 35 do RXPD obriga a facer unha EIPD antes de tratar datos que poidan
> supoñer un alto risco. Esta plantilla xa ven **cuberta co que fai Eira de verdade** (comprobado no
> código e nos tests citados). O concello ten que completar o marcado con `‹ ›`, revisala co seu DPD e
> aprobala. **Non substitúe o criterio do DPD nin do responsable.**
>
> **Resumo para a veciñanza na app:** *Quen custodia os teus datos → Ver a avaliación de impacto*
> (`/c/<concello>/privacidade/avaliacion-impacto/`). Ver tamén a [matriz de visibilidade](matriz.md),
> o [RAT](rat.md) e o [protocolo de brechas](brechas.md).

| | |
|---|---|
| Responsable do tratamento | Concello de ‹nome›, ‹NIF›, ‹enderezo› |
| Encargado (se a aloxa a deputación) | ‹Deputación/mancomunidade›, con contrato do art. 28 RXPD |
| DPD | ‹nome ou posto, contacto› |
| Versión de Eira avaliada | v1.3 (etiqueta `v1.3-certame`) |
| Data e versión da EIPD | ‹data› · ‹versión› |
| Próxima revisión | ‹data; como mínimo anual ou cando cambie o tratamento› |

## 0. É obrigatoria?

Os tratamentos de Eira que cumpren polo menos dous criterios da lista da AEPD (e das directrices
WP248 do Grupo do art. 29) son os que entran nesta EIPD:

| Tratamento | Datos de categoría especial (art. 9) | Persoas vulnerables (menores) | Datos a grande escala | Outros criterios | EIPD |
|---|---|---|---|---|---|
| A. Saúde: consellos, RPE, probas físicas e observatorio | ✔ (saúde) | ✔ (escolas deportivas) | ‹segundo poboación› | avaliación/perfís de condición física | **Si** |
| B. Menores nas escolas | — | ✔ | ‹› | imaxe | **Si** |
| C. Rexistro de accidentes | posible (saúde, se se escribise) | posible | — | — | **Si (preventiva)** |
| D. Carné municipal con foto | foto (non biométrica: non se usa para identificar automaticamente) | posible | ‹› | — | **Si (preventiva)** |
| Reservas, pagamentos, incidencias | — | — | — | — | Non (só RAT) |

## 1. Descrición do tratamento

### A. Saúde: consellos, esforzo percibido (RPE), probas físicas e observatorio

| | |
|---|---|
| Finalidade | Dar consellos de hidratación e calor na reserva; seguir o esforzo e a condición física nas escolas deportivas; estatísticas anónimas de actividade física |
| Datos | Consellos: idade, peso, minutos semanais de actividade. Escolas: asistencia, esforzo percibido (escala Borg/OMNI), resultados de probas ALPHA-Fitness/SFT |
| Persoas | Veciñanza usuaria; nenos e nenas das escolas; persoas maiores |
| Base xurídica | Consellos: **consentimento explícito** (art. 9.2.a) só se se gardan na conta; no dispositivo non hai tratamento do concello. Escolas: misión de interese público (art. 6.1.e) + **consentimento da familia** para esforzo e probas (`Consent.Kind.PERFORMANCE`) |
| Onde se garda | Consellos: **no dispositivo** (`localStorage`); na conta só con consentimento (`HealthProfile`). Escolas: base de datos do concello |
| Quen accede | Persoa monitora (os seus grupos, se hai consentimento); administración do concello. **Nunca** a deputación sen acceso de soporte; nunca o observatorio público con datos individuais |
| Conservación | ‹ver RAT›; o perfil de saúde bórrase cando a persoa o retira |

### B. Menores nas escolas deportivas

| | |
|---|---|
| Finalidade | Inscrición, listas de asistencia, avisos á familia |
| Datos | Nome, apelidos, ano de nacemento; consentimentos (datos, imaxe, esforzo) con data e versión do texto |
| Base | Misión de interese público (art. 6.1.e); consentimento da familia para imaxe e esforzo; art. 7 LOPDGDD (menores de 14) |
| Quen accede | Familia; persoa monitora (nome e primeiro apelido); administración |

### C. Rexistro de accidentes

| | |
|---|---|
| Finalidade | Coñecer accidentes nas instalacións para mellorar a seguridade e responder a reclamacións |
| Datos | Data e hora, instalación, tipo xeral, gravidade **percibida**, se se chamou ao 112, papel de quen comunica |
| Base | Obrigas legais de seguridade e interese público (art. 6.1.c e 6.1.e) |
| Quen accede | Só administración do concello e DPD (`breach_access`); a deputación só cifras agregadas |
| Conservación | Configurable (`accident_retention_months`, por defecto 24 meses despois de pechado) e purga automática |

### D. Carné municipal con foto

| | |
|---|---|
| Finalidade | Acreditar a condición de abonado/a e rexistrar a entrada |
| Datos | Número de carné, foto opcional, tipo e validez do abono |
| Base | Execución da relación co servizo (art. 6.1.b) e interese público; a foto, **opcional** |
| Quen accede | A persoa; persoal que le o carné (tipo e validez); administración |

### E. Procedencia e mobilidade (v1.5)

| | |
|---|---|
| Finalidade | **Estatística:** planificar transporte, horarios e instalacións |
| Datos | Parroquia ou concello de residencia, voluntarios. **Nunca GPS, ubicación do dispositivo nin enderezo** |
| Base | Misión de interese público (art. 6.1.e) e fins estatísticos (art. 89); o DPD debe confirmala |
| Quen accede | A persoa ao seu dato. Concello e deputación: só agregados, n ≥ 10 persoas distintas despois de cada filtro |

## 2. Necesidade e proporcionalidade

| Pregunta | Resposta (Eira v1.3) | Onde se comproba |
|---|---|---|
| Hai unha forma menos intrusiva de lograr o mesmo? | Os consellos de saúde funcionan **sen enviar datos ao servidor**; gardalos na conta é opcional | `tests/e2e/test_flows.py::test_health_data_never_leaves_device` |
| Pídense só os datos necesarios? | Sen DNI, enderezo nin apelidos de menores na tableta; da idade só o ano | `docs/rxpd/matriz.md` |
| Os datos de saúde chegan ao persoal? | Non: nin ao persoal nin ás exportacións do concello | `apps/accounts/tests/test_health.py` |
| As estatísticas permiten identificar? | Só se publican grupos con **n ≥ 10** (`EIRA_MIN_AGGREGATION`); microdatos con seudónimo HMAC e banda de idade | `apps/activities/tests/test_activities.py::test_observatory_threshold` |
| O padrón queda copiado en Eira? | Non: cárgase como **HMAC** de «concello\|DNI\|data» e o DNI dunha solicitude bórrase ao decidir | `apps/accounts/padron.py`, `apps/accounts/tests/test_padron.py` |
| O rexistro de accidentes pode ter diagnósticos? | Non: **non hai texto libre** | `apps/safety/tests/test_safety.py::test_accident_register_minimal_data_and_access` |
| Consentimentos revogables? | Si, nun clic e con data | `apps/accounts/tests/test_privacy.py` |
| Información ás persoas | «Quen custodia os teus datos», política de privacidade, resumo da EIPD | `/c/<concello>/privacidade/…` |
| Dereitos | Acceso/portabilidade (JSON), rectificación, supresión con anonimización das reservas | `docs/seguridade-rxpd.md` |

## 3. Riscos e medidas

Escala: probabilidade e impacto **B**aixo · **M**edio · **A**lto. O risco inherente é antes das
medidas; o residual, despois. Valores propostos: o DPD debe revisalos.

| # | Risco | Trat. | Inherente (P/I) | Medidas que xa ten Eira | Residual (P/I) |
|---|---|---|---|---|---|
| R1 | Acceso indebido do persoal a datos de saúde | A | M/A | O persoal non ve os datos de saúde; saúde no dispositivo por defecto; nin no admin técnico (`HealthProfile` excluído) | B/A → **Baixo** |
| R2 | Reidentificación no observatorio | A | M/A | n ≥ 10; bandas de idade; seudónimo HMAC co segredo do servidor; IA opcional só con agregados (o adaptador rexeita campos persoais) | B/M → **Baixo** |
| R3 | Rexistro de esforzo de menores sen consentimento | A, B | M/A | Consentimento `performance` da familia, por menor, con data e revogable; a tableta non deixa rexistrar sen el | B/M → **Baixo** |
| R4 | Exposición da imaxe de menores | B | M/A | Consentimento `image` separado; icona de cámara verde ou riscada na tableta | B/M → **Baixo** |
| R5 | Datos clínicos no rexistro de accidentes | C | M/A | Sen texto libre; gravidade percibida en categorías; nin a deputación nin co acceso de soporte; purga automática | B/M → **Baixo** |
| R6 | Policía ou terceiros reciben datos automaticamente | C | B/A | **Non hai ningún envío automático**; só queda constancia de quen decidiu contactar | B/B → **Baixo** |
| R7 | Uso da foto do carné para outros fins ou suplantación | D | M/M | Foto opcional, sen EXIF/GPS; QR sen datos persoais, dinámico (caduca en minutos); impreso revogable por versión | B/M → **Baixo** |
| R8 | Conta de administración comprometida (roubo do correo) | todos | M/A | Código ao correo con caducidade e intentos limitados; **dobre factor TOTP** (obrigatorio se o concello o configura); **rexistro de auditoría** consultable por administración e DPD | B/A (con 2FA obrigatorio) · M/A (sen el) |
| R9 | A deputación (encargada) accede a datos persoais | todos | M/A | Só agregados; acceso de soporte autorizado polo concello, 24 h, só lectura, cada páxina vista rexistrada e avisada | B/M → **Baixo** |
| R10 | Exportacións masivas de datos sen control | todos | M/A | Toda descarga do persoal queda en `AuditLog` (`export.download`); as exportacións do concello non levan saúde | B/M → **Baixo** |
| R11 | Brecha de seguridade non xestionada en prazo | todos | M/A | Rexistro de brechas con prazo de 72 h e texto de comunicación | B/M → **Baixo** |
| R12 | Copia do padrón ou do DNI | padrón | M/A | HMAC por concello; DNI da solicitude borrado ao decidir | B/M → **Baixo** |
| R13 | Reidentificar unha persoa cruzando filtros de procedencia | E | M/A | n = persoas distintas; limiar **despois de cada filtro**; «outras procedencias» sen cifra se n < 10; sen totais; períodos pechados; só concello para quen vén de fóra; exportacións rexistradas. Queda o risco de comparar datas distintas nun fluxo visible | B/M → **Baixo (o DPD debe revisalo)** |
| R14 | Asignar a menores unha persoa sen a comprobación da contratación, ou gardar datos penais | B | M/A | Eira **non garda o certificado**; só quen marcou e cando; asignación bloqueada e revisión periódica. A marca é unha declaración do concello, non unha comprobación de Eira | B/A → **Medio-baixo (depende do concello)** |
| R15 | Aceptar un modelo de exemplo como se fose un texto legal revisado | todos | M/M | Aviso visible na app e nos ficheiros; só desaparece se o concello adapta o texto e declara que o revisou | B/M → **Baixo** |

## 4. Risco residual e conclusión

- **Risco residual global proposto: baixo**, coa condición de que o concello **active o dobre
  factor obrigatorio** para a administración e o DPD (*Configuración → Seguridade das contas e
  rexistro de auditoría*). Sen el, o risco R8 queda en **medio**.
- Non se propón consulta previa á AEPD (art. 36) ‹se o DPD está de acordo›.
- **Medidas pendentes ou fóra de Eira** (responsabilidade do concello ou da entidade que o aloxa):
  - cifrado da base de datos e das copias de seguridade; control de acceso ao servidor;
  - contrato de encargo (art. 28) coa deputación/mancomunidade e coa empresa de limpeza, se a hai;
  - formación do persoal;
  - borrado automático do rexistro de limpeza aos 2 anos e das denuncias de partidas ao ano
    (**documentado, non programado** en Eira v1.3);
  - desde a v1.4 o segredo TOTP gárdase cifrado; para que as copias da base de datos non abonden,
    definir `EIRA_TOTP_KEY` fóra da base de datos (ver `docs/seguridade-rxpd.md`).
  - o rexistro de auditoría consérvase 2 anos por defecto (configurable) e bórrase só (v1.4).

## 5. Plan de acción

| Medida | Responsable | Prazo | Estado |
|---|---|---|---|
| Activar o dobre factor obrigatorio para administración e DPD | ‹› | ‹› | ‹› |
| Revisar o rexistro de auditoría ‹mensualmente› | DPD | ‹› | ‹› |
| Asinar o contrato de encargo coa entidade que aloxa Eira | ‹› | ‹› | ‹› |
| Revisar textos legais (privacidade, consentimentos) | ‹› | ‹› | ‹› |

## 6. Opinión do DPD

> ‹A persoa delegada de protección de datos, tras revisar esta avaliación, emite a seguinte opinión
> (art. 35.2 RXPD):›
>
> ‹Conforme / conforme con condicións / non conforme›
>
> ‹Observacións e condicións:›
>
> ‹Data e sinatura›

## 7. Aprobación do responsable

> ‹Órgano que aproba (alcaldía, concellaría delegada…), data e sinatura.›
> ‹Se se aparta da opinión do DPD, motivo.›

---

**Nota de verificación (equipo Eira):** as medidas desta plantilla están no código da v1.3 e teñen os
tests citados. A **valoración do risco** (probabilidade, impacto e residual) é unha **proposta**: non
está verificada por ningún DPD.
