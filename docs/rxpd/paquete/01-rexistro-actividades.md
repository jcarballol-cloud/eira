<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Rexistro de actividades de tratamento (art. 30 RXPD)

> **MODELO DE EXEMPLO — require revisión do DPD e dos servizos xurídicos do concello.**

Cuberto co que fai Eira 1.5.1 (ver a [auditoría](../auditoria-aepd.md)). O concello completa o
marcado con `‹ ›`. Como administración pública, ademais debe **publicar o inventario** destas
actividades coa súa base legal, por medios electrónicos (art. 31.2 LOPDGDD).

## Datos comúns a todas as actividades (art. 30.1.a)

| | |
|---|---|
| Responsable | Concello de ‹nome›, ‹NIF›, ‹enderezo›, ‹correo› |
| Delegado/a de protección de datos | ‹nome ou posto, correo› (obrigatorio para os concellos: art. 37.1.a RXPD) |
| Encargado, se o hai | ‹deputación, empresa ou quen aloxe Eira›, con contrato do art. 28 ([04-contrato-encargado.md](04-contrato-encargado.md)) |
| Transferencias internacionais | **Ningunha** cos datos das contas. Avisadas e por decisión da persoa: Telegram (voluntario, fóra do EEE) e o mapa, só baixo demanda («Ver mapa»: o servidor de teselas, OpenStreetMap por defecto, ve o enderezo IP do navegador) |
| Medidas de seguridade (art. 32) | ENS (RD 311/2022) segundo a disposición adicional 1.ª LOPDGDD; en Eira: HTTPS, CSP estrita, sesións de 14 días, acceso sen contrasinal con código dun só uso, dobre factor para a xestión, rexistro de auditoría, illamento por concello, fotos sen metadatos, purga automática |

## Actividades

| # | Actividade | Finalidade (30.1.b) | Base xurídica | Interesados e categorías de datos (30.1.c) | Destinatarios (30.1.d) | Prazo de supresión (30.1.f) |
|---|---|---|---|---|---|---|
| 1 | Contas e acceso | Identificar a quen reserva ou se inscribe | 6.1.e (Lei 7/1985, art. 25.2.l) | Veciñanza: correo, nome para mostrar; teléfono e ano de nacemento opcionais; idioma e preferencias | Ningún | Mentres a conta estea activa; códigos de entrada ao día seguinte; sesións ao caducar |
| 2 | Alta con padrón e tarifas | Dar a app e a tarifa de veciñanza ou reducida | 6.1.e e ordenanza fiscal | Solicitantes: nome, apelidos, correo, DNI/NIE, data de nacemento, enderezo opcional; do padrón só HMAC e parroquia; colectivo de tarifa reducida | Ningún | DNI, data e enderezo: ao resolver. Solicitude: 12 meses. HMAC: ata a seguinte carga. Códigos sen usar: 1 mes despois de caducar |
| 3 | Reservas | Xestionar o uso das instalacións | 6.1.e; 6.1.b se hai pagamento | Veciñanza e persoas doutros concellos da rede: reserva, participantes opcionais, checklist, estado ao entrar (texto e foto opcional) | Mantemento (só instalación e hora); concello de destino nas reservas da rede (nome para mostrar e concello de orixe) | 24 meses despois de rematar; despois anonimizada |
| 4 | Control de acceso | Abrir a porta e saber que se usou a reserva | 6.1.e | Eventos de acceso e entrega de chaves | Ningún | 24 meses |
| 5 | Cobros e devolucións | Cobrar taxas e prezos públicos | 6.1.c e 6.1.e | Referencia, importe, estado e forma de pagamento; sen datos de tarxeta | Entidade financeira (pasarela) e Intervención | 6 anos (normativa tributaria) |
| 6 | Incidencias e alertas | Reparar avarías e avisar ante un perigo | 6.1.e | Quen avisa, descrición, foto sen metadatos; na alerta, o posto de quen a recibe | Mantemento e limpeza (sen datos de contacto); persoa responsable da instalación | Incidencias resoltas: aos 24 meses sen persoa nin foto. Alertas: coa incidencia |
| 7 | Rexistro de accidentes | Mellorar a seguridade e responder a reclamacións | 6.1.c e 6.1.e | Data, instalación, tipo xeral, gravidade percibida, 112 si/non, papel de quen comunica. **Sen diagnósticos nin texto libre** | Ningún (nin a deputación) | 24 meses despois de pechado (configurable) |
| 8 | Saúde: consellos persoais | Recomendacións de auga e enerxía | **9.2.a** (consentimento explícito), só se se garda na conta | Peso, idade, minutos semanais | Ningún, nin o persoal | Ata retirar o consentimento ou eliminar a conta |
| 9 | Escolas deportivas: asistencia, esforzo e probas | Inscrición, seguimento e observatorio anónimo | 6.1.e; consentimento da familia para esforzo e probas | Menores e adultos: nome, ano, apelidos (achégaos o concello), asistencia, esforzo (RPE), probas físicas; seudónimo HMAC | Monitora (os seus grupos: nome e primeiro apelido); observatorio só agregado (n ≥ 10) | Tempada + 1 ano (sen purga automática) |
| 10 | Menores e persoas titoras | Inscribir menores e recoller os consentimentos | 6.1.e; art. 7 LOPDGDD | Persoa titora; menores: nome e ano; consentimentos con data e versión; altas pendentes na tableta (nome, ano, correo da familia) | Monitora (nome e primeiro apelido) | Mentres teña a conta; altas pendentes, 3 meses |
| 11 | Imaxe | Fotos en actividades e comunicacións | 6.1.a, revogable | Persoas inscritas e adultas que o autorizan | Comunicación municipal | Ata a retirada |
| 12 | Carné municipal e abonos | Acreditar o abono e rexistrar a entrada | 6.1.e; foto opcional | Número de carné, foto sen metadatos, abono, número doutro carné municipal (opcional) | Persoal que le o carné (tipo e validez) | Mentres teña a conta; abonos, 6 anos (cobros) |
| 13 | Partidas abertas | Atopar xente para xogar | 6.1.a | Nome de pila e inicial, nivel, mensaxe curta, solicitudes e mensaxes predefinidas, denuncias | Outras persoas da app (só nome de pila e inicial) | Coa reserva (24 meses); denuncias, 12 meses |
| 14 | Procedencia | Estatística para planificar transporte e instalacións | 6.1.e e art. 89 | Parroquia ou concello de residencia, voluntarios. Nunca GPS | Concello e deputación, só agregados (n ≥ 10) | Mentres teña a conta ou ata que a borre |
| 15 | Valoracións e enquisas (NPS) | Mellorar o servizo | 6.1.e | Valoración, etiquetas, comentario; enquisa anual | Concello, sen nome; deputación, só NPS agregado | Comentarios: 24 meses. Enquisa: persoa e comentario, 24 meses |
| 16 | Avisos do concello | Informar de peches, alertas e actividades | Servizo: 6.1.e (e 6.1.b se afecta a unha reserva). Informativos: 6.1.a | Preferencias por categoría e canle, consentimento, chat de Telegram, subscrición push, avisos recibidos | Provedor de correo do concello; **Telegram** se a persoa o vincula (fóra do EEE) | Avisos: 12 meses. Códigos de Telegram: 1 día |
| 17 | Rexistro de auditoría e dobre factor | Seguridade e trazabilidade (ENS) | 6.1.c (art. 32 RXPD) | Persoal de xestión: correo, accións, datas, descargas; segredo TOTP cifrado | Administración e DPD do concello | 24 meses (12–120, configurable) |
| 18 | Acceso de soporte da deputación | Asistencia técnica ao concello | 6.1.e e contrato art. 28 | Os datos que consulte durante o acceso | Persoal autorizado da deputación | Acceso: 24 h. Rexistro: o da auditoría |
| 19 | Documentos legais e aceptacións | Informar e xustificar aceptacións e consentimentos | 6.1.c e 6.1.a | Persoa, documento, versión, data, canle, retirada | Administración e DPD | A que fixe o concello; ao eliminar a conta queda sen persoa |
| 20 | Acreditación con menores | Constancia da comprobación na contratación | 6.1.c (LOPIVI, art. 57) | Persoal monitor: só quen marcou e cando. **Sen certificado nin datos penais** | Administración do concello | Ata retirar a marca ou eliminar a conta |
| 21 | Rexistro de limpeza | Control do contrato e da hixiene | 6.1.b e 6.1.c | Persoal de limpeza: nome, empresa, data e hora, tarefas, observacións, foto | Concello; veciñanza só «última limpeza» sen nome | 24 meses |
| 22 | Rexistro de brechas | Cumprir os arts. 33 e 34 | 6.1.c | Descrición da brecha, datos e persoas afectadas, medidas | Administración e DPD; AEPD se se notifica | 5 anos |

## Rexistro do encargado (art. 30.2)

Se Eira a aloxa a deputación, unha empresa ou engram, esa entidade leva o seu propio rexistro como
encargada: nome e contacto do encargado e de cada responsable (os concellos), categorías de
tratamento (as 22 de arriba), transferencias (ningunha) e medidas de seguridade. O modelo de
contrato está en [04-contrato-encargado.md](04-contrato-encargado.md).

## Como manter este rexistro

- Revisalo cando se active un módulo novo (escolas, partidas abertas, carné…) ou se cambie un prazo.
- A orixe de cada dato está na [auditoría](../auditoria-aepd.md) e na [matriz](../matriz.md).
- En Eira: «Protección de datos: primeiros pasos» → «Rexistro de actividades descargado e
  revisado» deixa constancia de quen o revisou e cando.
