<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Matriz de visibilidade de datos por perfil

Que dato ve cada perfil e onde se comproba. As probas en `apps/*/tests/test_privacy*.py`, `apps/tenants/tests/test_roles.py` e `apps/accounts/tests/test_privacy.py` verifican esta matriz.

**Avaliación de impacto (EIPD):** os tratamentos de maior risco (saúde, menores, accidentes e carné con foto) teñen unha plantilla de EIPD cuberta co que fai Eira: [eipd-plantilla.md](eipd-plantilla.md). Resumo para a veciñanza en *Quen custodia os teus datos → Ver a avaliación de impacto*.

Lenda: **✔** ve o dato · **—** non o ve · **agr.** só agregado (n ≥ 10) · **seud.** seudonimizado.

| Dato | Veciña (propio) | Operario/a | Monitor/a | Concello | Deputación | Observatorio público | Exportacións |
|---|---|---|---|---|---|---|---|
| Correo e teléfono | ✔ | — | — | ✔ (reservas, altas) | só con acceso de soporte (24 h) | — | — |
| Nome para mostrar | ✔ | — | ✔ (nome e primeiro apelido dos seus grupos) | ✔ | só con acceso de soporte (24 h) | — | — |
| Empadroamento (si/non) | ✔ | — | — | ✔ | só con acceso de soporte (24 h) | — | — |
| Colectivo de tarifa reducida | ✔ | — | — | ✔ (sen documentos) | só con acceso de soporte (24 h) | — | — |
| Reservas | ✔ | só instalación e hora na orde | — | ✔ | agr.; detalle só con acceso de soporte (24 h) | agr. (datos abertos) | agregados (CSV/ODS) |
| Pagamentos | ✔ | — | — | ✔ (referencia, importe e estado) | só con acceso de soporte (24 h) | — | conciliación (sen datos bancarios) |
| Menores: nome e ano | ✔ (os seus) | — | ✔ (nome e primeiro apelido nos seus grupos) | ✔ | só con acceso de soporte (24 h) | — | — |
| Consentimento de imaxe | ✔ | — | ✔ (icona de cámara) | ✔ (icona e filtro) | só con acceso de soporte (24 h) | — | — |
| Asistencia e esforzo (RPE) | — | — | ✔ (os seus grupos, se hai consentimento) | ✔ | só con acceso de soporte (24 h) | agr. por banda de idade | seud. (só concello) |
| Valoracións «Que tal foi?» | ✔ | — | — | ✔ **sen nome** | só con acceso de soporte (24 h) | — | agregados sen comentarios |
| Incidencias que comunica | ✔ | ✔ (sen datos de contacto) | — | ✔ | só con acceso de soporte (24 h) | — | agregados |
| Saúde (peso, idade para recomendacións) | ✔ no dispositivo; na conta só con consentimento art. 9 | — | — | — | — | — | — |
| Padrón | — (Eira non o garda) | — | — | só o resultado si/non da consulta | só con acceso de soporte (24 h) | — | — |

## Principios
- **Minimización:** non se piden DNI, enderezo nin apelidos dos menores. O pago faise na pasarela da entidade.
- **Saúde (art. 9 RXPD):** os datos quedan no dispositivo por defecto. Só se gardan na conta con consentimento explícito e revogable. Nunca os ve o persoal, nin van ás exportacións nin ao observatorio (ver `docs/health/recomendacions.md`).
- **Menores:** por debaixo dos 14 anos consente a familia (art. 7 LOPDGDD). Con 14 ou máis, a familia confirma que o menor está de acordo.
- **Imaxe:** consentimento separado, por persoa e revogable. O monitor e o concello ven unha cámara verde ou riscada en vermello.
- **Deputación:** por defecto ve só datos agregados e anónimos: indicadores, comparativa, instalacións, peches e plans de mantemento (`@aggregate_view`). Para os datos persoais precisa un **acceso de soporte** que autoriza o concello en «Persoal e códigos», con motivo. Caduca ás 24 h, pódese revogar, cada páxina vista queda en AuditLog (`support.view`) e o concello recibe un aviso no primeiro uso. Mesmo co acceso, é só lectura. Tests: `apps/tenants/tests/test_support_access.py` (403 → 200 → 403 ao caducar).
- **Apelidos:** son un dato da inscrición que achega o concello. A tableta só recibe nome e primeiro apelido (o segundo nin sequera chega ao navegador); o nome completo só se ve na administración.
- **Sen seguimento:** só hai cookies técnicas (`sessionid`, `csrftoken`, `django_language`, `eira_prefs` e, na demo, `eira_marco`). Unha proba falla se aparece outra.

## v5 · Reservas en concellos próximos da mesma rede

Unha persoa de Vilardeiras pode reservar en Pontedouro (mesma deputación) coa súa conta, sen crear outra. **O concello de destino só recibe o imprescindible para esa reserva:**

| Dato | Concello de destino | Concello de orixe | Deputación |
|---|---|---|---|
| Nome para mostrar (ou «Persoa de ‹concello›» se non o ten) | ✔ (para identificar a reserva no mostrador) | — | só con acceso de soporte (24 h) |
| Concello de orixe (só o nome) | ✔ (para aplicar a tarifa de non empadroada e para estatísticas) | — | agr. |
| Data, hora, instalación, número de persoas e nomes opcionais dos participantes | ✔ | — | agr. |
| Importe, forma de pagamento e referencia do cobro | ✔ (cobra no seu TPV) | — | — |
| Correo, teléfono, ano de nacemento | **—** (os avisos da reserva envíaos Eira á persoa; o concello de destino non ve o enderezo) | — | — |
| Empadroamento, familia, menores, saúde, inscricións, valoracións noutros concellos | **—** | — | — |

- A tarifa de non empadroada calcúlase sen consultar o padrón do concello de orixe: abonda con que a persoa non estea empadroada no destino.
- O concello de orixe non ve as reservas que a persoa fai noutros concellos. Na app, a persoa vee todas xuntas («Noutros concellos»).
- Cada concello decide se se abre á rede (`network_open`), cun máximo de reservas activas por persoa e unha antelación propia.
- Proba: `apps/bookings/tests/test_v5_network.py` (o persoal do destino non ve o correo; o de orixe non ve a reserva).

## v5 · Outros datos novos

| Dato | Veciña (propio) | Operario/a | Concello | Deputación | Conservación |
|---|---|---|---|---|---|
| Número de persoas e nomes opcionais dos participantes | ✔ | — | ✔ | agr. | os da reserva |
| Estado ao entrar (texto e foto opcional, sen EXIF) | ✔ | ✔ | ✔ | só con acceso de soporte (24 h) | os da reserva; se hai incidencia, os da incidencia |
| Bonos (usos e caducidade) | ✔ | — | ✔ | — | os dos cobros (obriga contable) |
| Rexistro de brechas de seguridade | — | — | só administración do concello e DPD | **—** | 5 anos (ver `brechas.md`) |

## v1.1 · Rexistro de limpeza (datos do persoal)

Son datos do persoal (propio ou da empresa contratada), non da veciñanza; por iso a táboa non vai na páxina «Quen custodia os teus datos».

| Dato do persoal | Persoal de limpeza (propio) | Mantemento | Concello | Deputación | Veciñanza | Conservación |
|---|---|---|---|---|---|---|
| Nome, empresa, data e hora de cada limpeza, tarefas feitas e observacións | ✔ (os da súa zona, últimos 5) | — | ✔ (páxina «Limpeza» e exportación CSV/ODS/PDF) | só con acceso de soporte (24 h) | só «Última limpeza: ‹día e hora›», **sen nome** | 2 anos (inspeccións e control do contrato); despois bórranse |
| Foto opcional da zona (sen EXIF nin localización) | ✔ | — | ✔ | só con acceso de soporte (24 h) | — | a do rexistro |

- Base xurídica: execución do contrato de limpeza e obriga de hixiene das instalacións (art. 6.1.b e 6.1.c RXPD). A empresa contratada é **encargada** do tratamento: o contrato debe recoller o art. 28.
- Non se rexistra a localización: o QR só proba que a persoa abriu a páxina da zona, non onde estaba. Sen conexión, a hora é a do móbil ao gardar (ata 7 días atrás; nunca no futuro).
- **Non verificado:** o borrado automático aos 2 anos non está programado (vai coa purga dos avisos cando se implemente para todos os rexistros).

## v1.2 · Alertas, rexistro de accidentes e peche sen confirmar

| Dato | Veciña (propio) | Monitor/a | Mantemento | Concello | DPD | Deputación | Conservación |
|---|---|---|---|---|---|---|---|
| Alerta (tipo, instalación, hora, a quen se avisou) | ✔ (ve o aviso enviado) | ✔ (as que dá) | só a incidencia vinculada, sen quen alertou | ✔ | — | agr. | a da incidencia |
| Rexistro de accidentes (data e hora, instalación, tipo xeral, gravidade percibida, 112 si/non, papel de quen comunica) | — (só o rexistra) | — | — | ✔ | ✔ | **—** (nin co acceso de soporte) | configurable por concello (por defecto 24 meses despois de pechado); purga automática |
| Peche sen confirmar (fases, persoa responsable avisada, resultado) | ✔ (na súa reserva) | — | — | ✔ | — | só con acceso de soporte (24 h) | o da reserva |
| Contactos coa Policía Local (quen decidiu, cando, teléfono) | — | — | — | ✔ | — | só con acceso de soporte (24 h) | o da reserva |

| Dato do persoal | Persoa responsable | Mantemento | Concello | Deputación | Veciñanza | Conservación |
|---|---|---|---|---|---|---|
| Persoas responsables (nome ou posto, teléfono, correo, horario) | ✔ (os seus) | — | ✔ | — | — | mentres estean designadas |

- **Accidentes sen datos de saúde:** non hai diagnósticos, lesións concretas nin texto libre (un test compróbao). A gravidade é a **percibida** por quen comunica, non unha valoración clínica. Base xurídica: interese público e obrigas de seguridade da instalación (art. 6.1.c e 6.1.e RXPD).
- **Policía Local:** non hai ningún envío automático de datos. Se unha persoa decide chamar, só queda rexistrado que se contactou, cando e por quen.

## v1.2 · Partidas abertas («Busco xente»)

| Dato | Veciña (propio) | Outras persoas da app | Concello | Deputación | Conservación |
|---|---|---|---|---|---|
| Partida aberta (nome de pila e inicial de quen organiza, instalación, día e hora, nivel, prazas e mensaxe curta) | ✔ | ✔ só nome de pila e inicial (do concello e dos concellos próximos da rede) | ✔ | — | ata o fin da reserva; despois só na reserva (2 anos) |
| Solicitudes para unirse e mensaxes predefinidas (nome de pila e inicial) | ✔ | só quen organiza e quen xoga | ✔ | — | os da reserva (2 anos) |
| Denuncias dunha partida (motivo) | ✔ | — | ✔ | — | 1 ano |

- **Nunca** se mostran teléfono nin correo; non hai chat libre (só mensaxes predefinidas), así non se poden intercambiar datos de contacto pola app.
- **Consentimento explícito** para aparecer (ao publicar) e para que quen organiza vexa o nome de pila (ao unirse). Revogable: deixar de buscar xente ou retirarse.
- **Menores de 14 anos** non poden publicar nin unirse (sen ano de nacemento tampouco). Base: art. 7 LOPDGDD.
- Tres denuncias ocultan a partida ata que o concello a revise; o concello pode desactivar a función (módulo «Partidas abertas»).

## v1.2 · Carné municipal e abonos

| Dato | Veciña (propio) | Monitor/a | Mantemento | Concello | Deputación | Conservación |
|---|---|---|---|---|---|---|
| Abono (tipo, validez, canle de pagamento) | ✔ | — | ✔ (ao ler o carné: tipo e validez) | ✔ | agr. | 6 anos (cobros) |
| Carné municipal (número e foto opcional) | ✔ | só marca a asistencia (non ve a foto) | ✔ (ao ler o carné) | ✔ | — | mentres teña a conta; a foto bórrase cando a persoa a quita |

- O **QR** só leva o identificador interno do carné, a versión e (no impreso) a data de fin: ningún dato persoal. O dixital caduca aos 3 minutos.
- **Foto opcional**, gardada sen metadatos; non se usa para nada máis.
- **Vínculo con outro carné do concello** (biblioteca, piscina): só o número externo, mediante o adaptador `municipal_card` (simulado). Ver `docs/carne-municipal.md`.

## v1.3 · Contas de xestión: dobre factor e rexistro de auditoría

| Dato do persoal | Persoa (propio) | Outra administración do concello | DPD | Deputación | Conservación |
|---|---|---|---|---|---|
| Segredo TOTP (dobre factor) | só na súa app; en Eira, gardado e nunca mostrado despois de activalo | — (só ve se o ten activado e pode restablecelo) | — | — | mentres o teña activado |
| Códigos de recuperación | ✔ unha soa vez; en Eira só o HMAC | — | — | — | ata que se usan ou se xeran outros |
| Rexistro de auditoría (quen, que acción, cando, obxecto, detalle) | — | ✔ (o do seu concello) | ✔ | **—** (nin co acceso de soporte) | 2 anos por defecto, configurable por concello (12–120 meses); purga automática (v1.4). Non se borra a man desde a app |

- O rexistro inclúe os accesos e o dobre factor do **persoal de xestión** do concello; os inicios de sesión da veciñanza non se mostran.
- Ver [seguridade-rxpd.md](../seguridade-rxpd.md#v13--seguridade-das-contas-de-xestión).

## v1.5 · Procedencia (mobilidade): só agregada

**Finalidade estatística:** planificar transporte, horarios e instalacións. Nunca para decidir nada sobre unha persoa.

| Dato | Persoa (propio) | Monitor/a | Mantemento | Concello | Deputación | Conservación |
|---|---|---|---|---|---|---|
| Parroquia ou concello de residencia | ✔ (vela, cámbiaa e bórraa en «Concellos próximos»; vai na súa exportación) | — | — | só agregada, n ≥ 10 | só fluxos entre concellos, agregados, n ≥ 10 | mentres teña a conta ou ata que a borre |
| Parroquia na entrada do padrón (columna opcional do CSV) | — | — | — | — (non se mostra) | — | ata a seguinte carga, que a substitúe |

- **Minimización:** só parroquia ou concello. **Nunca GPS, ubicación do dispositivo nin enderezo.** Sen parroquia nin concello indicados, a persoa non conta. Para persoas doutro concello úsase o concello, nunca a súa parroquia.
- **Voluntaria:** ou a indica a persoa ou sae do cruce co padrón no alta, gardando só a parroquia. En ambos casos pódese cambiar ou borrar nun paso.
- **Limiar:** `n` son persoas distintas, non reservas. Aplícase **despois de cada filtro** (período e deporte). O resto vai a «outras procedencias» e, se tampouco chega a 10, móstrase «menos de 10», sen cifra.
- **Sen restas:** sen totais por destino nin por orixe; os puntos quentes da deputación só suman fluxos visibles. Só períodos pechados (30, 90 e 365 días).
- **Risco residual:** comparar dúas datas distintas pode deixar ver variacións pequenas dun fluxo xa visible. Non identifica a ninguén por si só, pero con coñecemento externo podería axudar: por iso a páxina non admite datas libres e a exportación queda rexistrada. Debe revisalo o DPD na EIPD.
- Exportacións CSV e GeoJSON: os mesmos datos agregados; quedan en `AuditLog`.

## v1.5 · Documentos legais

| Dato | Persoa (propio) | Concello | DPD | Deputación | Conservación |
|---|---|---|---|---|---|
| Aceptación: persoa, documento, versión, data, canle, retirada | ✔ («Documentos aceptados») | ✔ (CSV) | ✔ (CSV) | **—** (só o número de aceptacións por documento) | a que fixe o concello para xustificar o consentimento; ao eliminar a conta queda sen persoa |

- Retirar un consentimento conserva a data no rexistro e aplica o efecto: imaxe → retira a autorización; saúde → borra os datos da conta.
- **Todos os modelos incluídos son modelos de exemplo, non documentos legais válidos.**

## v1.5 · Acreditación con menores

| Dato | Persoa monitora | Administración do concello | DPD | Deputación | Conservación |
|---|---|---|---|---|---|
| Quen marcou a comprobación e cando | — | ✔ | — (no rexistro de auditoría, sen datos penais) | — | ata retirar a marca ou eliminar a conta |

- **Eira non garda nin sube o certificado do Rexistro Central de Delincuentes Sexuais (art. 10 RGPD).** Ver [acreditacion-menores.md](acreditacion-menores.md).

## v1.5 · Alertas

- A alerta avisa á persoa responsable designada e ao persoal de servizo nesa instalación, polas canles de cada persoa. Na alerta queda o **posto** de quen a recibiu, nunca o nome nin o correo do persoal.
- O rexistro de accidentes non cambia: datos mínimos e sen texto libre.
