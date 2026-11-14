# Plan da v2: de prototipo a produto

Orde de execución (a prioridade pedida é 1 → 3 → 5 → 2 → 4 → 7 → 8 → 6 → 9). Cada fase remata con
tests, E2E e axe en verde e cun commit. A demo debe arrancar en todos os commits.

> **Capturas:** as rutas `docs/capturas/v…/` que se citan aquí son das capturas completas, que non están no repositorio: están dispoñibles baixo petición ao equipo (ver [capturas/README.md](capturas/README.md)). No repositorio quedan as 11 capturas clave do README.

## Fase 1 · Cada perfil, a súa ferramenta
1. **Roles efectivos no backend:**
   - Defínese «veciñanza» como persoa autenticada **sen** rol de persoal no concello.
   - As vistas da app (reservar, inscribirse, avisar, checklist, saúde, familia) esixen ser veciñanza: o persoal recibe un 403.
2. **Operario:** só ve as ordes asignadas a el e as pendentes sen asignar; detalle e peche só desas. O seu calendario está filtrado.
3. **Monitora:** só os seus grupos, sesións e listas (xa era así; amplíase a probas e a novas vistas).
4. **Administración:**
   - Desaparecen do seu menú as entradas da veciñanza e as ligazóns a «Operario» e «Monitor».
   - Gaña «Ordes de traballo» dentro da xestión.
5. **Deputación:**
   - **Vista de consulta** dun concello: banner «Estás vendo X como Deputación · Volver á rede».
   - Só lectura: calquera POST dá 403, agás as accións de soporte documentadas (reenviar a invitación á administración e exportar os datos).
6. **Disposicións por perfil:**
   - app móbil (veciñanza e operario), con barra de lapelas inferior e cabeceira compacta;
   - tableta (monitora);
   - escritorio con navegación lateral (concello e deputación);
   - web pública (sen sesión).
7. **Marco de dispositivo para a demo** (`?marco=1/0`, gardado en cookie): móbil centrado para a app e tableta para a monitora. En pantallas pequenas nunca hai marco.
8. **Navegación común:**
   - O logo leva á pantalla principal do perfil.
   - «Cambiar de perfil» e «Saír» quedan sempre a un toque.
9. **Tests:** matriz rol × URL con 200/403.

## Fase 3 · Cobros cribles
1. **Modelo `Payment`** (pagamento):
   - Estados: `pending → paid | rejected | expired | refunded`.
   - Método: en liña, efectivo ou TPV físico.
   - Referencia e notificación verificada.
2. **Estados da reserva:** `pending_payment → confirmed | rejected | expired`, ademais de `cancelled`, `used` e `no_show`.
3. **TPV simulado tipo Redsys:**
   - Páxina de pago e volta á URL OK ou KO.
   - **Notificación servidor-servidor asinada (HMAC-SHA256)**, que é a única fonte de verdade.
   - Un pago xa resolto non se pode volver resolver.
4. **Bloqueo de 10 min**:
   - Ao caducar, a franxa libérase e a reserva queda «caducada».
   - Un pago rexeitado libera a franxa e **non** envía confirmación.
5. **Tarifas:** empadroamento, idade e colectivo (tarifa reducida validada polo concello).
6. **Desconto en franxas de baixa demanda:** configurable por concello (por defecto −20 %), co prezo tachado na grella e na confirmación.
7. **Recibo** HTML e PDF (xerador mínimo propio) e **devolución automática** na cancelación en prazo.
8. **Cobros e conciliación** na xestión:
   - filtros por data, estado, instalación e método;
   - CSV e ODS;
   - cobro en mostrador marcado a man;
   - o estado «pagada» vese ao momento na axenda e na ficha (test).

## Fase 5 · Mapas
1. Leaflet con `referrerPolicy: 'strict-origin-when-cross-origin'` nas teselas, mantendo a política global `same-origin`.
2. CSP coa orixe das teselas e atribución correcta.
3. Provedor de teselas **por concello** (URL, orixe e atribución), con valor por defecto na instancia.
4. Documentación da política de uso de OSM e das alternativas.
5. Test Playwright de que as teselas responden 200, con captura.

## Fase 2 · Alta como na vida real
1. **«Solicitar a app»** na web do concello:
   - Comprobación de padrón detrás dun `PadronAdapter`: simulado na demo, cola manual noutros casos.
   - **Correo** coa ligazón de instalación, o **código de empadroamento** e as instrucións Android/iOS.
2. **Primeira apertura** (ligazón de acceso dun só uso):
   1. código de empadroamento;
   2. «Tes fillos ou persoas ao teu cargo?»;
   3. privacidade por capas e consentimentos;
   4. instalación.
3. **Axuda de instalación** con ilustracións propias para Android e iOS.
4. **Alta en mostrador:** invitación e folla imprimible con QR e código.
5. **Unidade familiar visible:** lapela «Familia» con cada menor, as súas inscricións e permisos.
6. **A monitora engade nomes a un grupo:** quedan «pendentes de validar» na xestión.

## Fase 4 · Deseño
1. **Tokens v2:** superficies sen bordos, máis aire, raios de 16/12, sombras mínimas, escala tipográfica e transicións que respectan `prefers-reduced-motion`.
2. **Fotos libres de Wikimedia Commons:**
   - Detalle sen xente, licenza CC0, CC BY ou CC BY-SA comprobada unha a unha.
   - WebP en varios tamaños, `loading=lazy` e texto alternativo.
   - `static/photos/CREDITS.md`.
   - O concello pode subir as súas fotos, que se procesan igual.
3. **Ficha de instalación compacta:**
   - Lapelas Datos, Horario, Tarifas, Normas, Acceso, Mantemento e Fotos.
   - Rexilla de 2–3 columnas e gardado en liña.
4. **Accesibilidade física** como lista de características con iconas de liña (máis tipos), editable con caixas.
5. **Escala de esforzo da tableta:**
   - Unha persoa tras outra, nome grande, 11 botóns de 80 px como mínimo con cor progresiva.
   - OMNI con caras graduadas e CR-10 con todas as etiquetas.
   - Avance automático e «Non son eu».
6. **Estados baleiros ilustrados**, esqueletos de carga, confirmacións (toast) e capturas antes/despois en `docs/capturas/v2/`.

## Fase 7 · Valoracións e observatorio
1. **«Que tal foi?»** (Ben / Regular / Mal) no peche, con etiquetas e comentario. Un «Mal» por estado pode crear unha incidencia, coa confirmación da persoa.
2. **Valoracións na xestión:** media por instalación, mellor e peor, evolución, motivos, e comentarios con resposta e moderación.
3. **Observatorio:**
   - Filtros por datas, instalación e actividade.
   - Mapa de calor; uso real fronte a reservado; satisfacción; participación por idade (e por sexo só con consentimento); minutos fronte á OMS; condición física por grupo; ingresos; ocos con suxestións.
   - Táboa e exportación en cada gráfico, e n ≥ 10 en todo o que teña datos de persoas.
4. **Deputación:** comparativa ampla e alta dun concello en 5 pasos (datos, responsable, módulos, logo e cores, primeira instalación e invitación).

## Fase 8 · RXPD
1. `docs/rxpd/matriz.md` e o rexistro de actividades de tratamento.
2. **Información por capas** na alta.
3. **Centro de privacidade** na app: interruptores datados, descarga, borrado e contacto do DPD.
4. **Menores de 14 anos:** consentimento da persoa titora, por menor.
5. **Fotos:**
   - Icona de cámara permitida ou tachada na lista da tableta e na xestión, co filtro «só quen non pode saír en fotos».
6. Sen cookies de seguimento, documentado.
7. **Tests:** cada perfil accede só aos datos persoais que lle corresponden.

## Fase 6 · Saúde útil
1. **Motor de recomendacións** (JS, no dispositivo):
   - Personalizado co peso, a idade, a duración da reserva, se é cuberta ou exterior e a previsión.
   - Antes / durante / despois, comida, calor-frío-UV, sinais de alarma e aviso de hiponatremia.
   - Fontes documentadas.
2. **Ficha de saúde:**
   - Só no dispositivo por defecto.
   - «Gardar na miña conta» con consentimento explícito (art. 9).
   - Nunca visible para o persoal, nas exportacións do concello nin no observatorio (tests).
3. **Recomendacións dentro de cada reserva.**

## Fase 9 · Peche
1. Guión novo do pitch, vídeos e capturas v2.
2. axe en móbil, tableta e escritorio; revisión do peso das páxinas.
3. `INFORME_MANANA.md`, sección v2.
4. Servidor en `0.0.0.0:8000` cos datos rexenerados, nunha xanela independente.

## v1.2 · Folla de ruta (o que queda despois das propostas do equipo)
Os oito bloques (A–H) están feitos na interface. Queda pendente, sen facelo a medias na app:
1. **Datos reais de DESA:** confirmar se existe un rexistro oficial galego con datos abertos e a súa licenza, e cargalo co adaptador CSV (`EIRA_DESA_CSV`). Non integrar apps de terceiros (p. ex. ARIANA RCP) sen verificar datos e licenza.
2. **Carné:** integración real co carné existente dalgún concello (adaptador `municipal_card`); proba con lectores de QR físicos; lectura coa cámara da tableta como opción.
3. **Purgas programadas** que a matriz xa indica e aínda non se executan soas: denuncias de partidas (1 ano) e rexistros de limpeza (2 anos).
4. **Rendemento:** importar as lecturas das facturas en CSV da comercializadora e, se o concello ten contadores con telelectura, un adaptador para lelos.
5. **PDF do carné e do cartel:** validación con PAC/veraPDF e fontes incrustadas.
6. **Tema escuro no escritorio do concello:** hoxe só no panel Rendemento; estendelo ao resto con revisión de contraste.

## Despois da v1.5 (non entrou na versión conxelada)

1. **Importar `v15.json`:** a portabilidade exporta documentos legais, aceptacións e acreditacións, pero a importación aínda non os restaura.
2. **«Escoitar»:** probar con TalkBack e VoiceOver en dispositivos reais e cunha voz galega real.
3. **Procedencia:** editar a posición das parroquias na xestión (hoxe, no admin técnico) e coropletas con límites parroquiais libres.
4. **Portas legais:** opción do concello para esixir a aceptación antes de reservar (hoxe avísase sen bloquear).

## Auditoría RXPD (14/11/2026): o que queda

Ver [docs/rxpd/auditoria-aepd.md](rxpd/auditoria-aepd.md). Corrixido no código: O1–O6, O9 (mapa só baixo demanda) e O11.

| Prioridade | Oco | Proposta |
|---|---|---|
| **Alta** | O8 · Pagamentos sen purga aos 6 anos | Purga ou anonimización aos 6 anos do peche do exercicio, con aviso previo á Intervención; depende do calendario contable de cada concello |
| **Media** | O8 · Asistencia, esforzo e probas sen purga (tempada + 1 ano) | Data de fin de tempada por grupo e purga ao ano seguinte; o observatorio xa só garda agregados |
| **Media** | Limitación do tratamento (art. 18) e bloqueo (art. 32 LOPDGDD) sen estado propio | Marca «limitado/bloqueado» por persoa que oculta os datos do uso ordinario e só os deixa ver ao DPD |
| **Media** | Push real: o adaptador `VapidWebPushAdapter` é un esqueleto | Implementalo con cifrado RFC 8291 e contido mínimo; documentar que o servizo de push do navegador pode estar fóra da UE |
| **Baixa** | O7 · `GameReport.reviewed_at` nunca se escribe | Rexistrar cando o concello revisa unha denuncia (ou quitar o campo) |
| **Baixa** | O7 · `User.last_login` gárdao Django e Eira non o usa | Usalo para avisar e despois borrar contas inactivas (p. ex. 3 anos) ou deixar de actualizalo |
| **Baixa** | O10 · Os textos libres só levan un aviso | Aviso suave no navegador se se detectan palabras de saúde (sen enviar nada) |
| **Baixa** | Gestiona RGPD | Pasar a táboa da auditoría á ferramenta da AEPD cun concello ficticio e gardar o informe |


## Idioma (14/11/2026): o que queda

- Os correos dos procesos de fondo (avisos, recordatorios, `booking_maintenance`) saen sempre en galego: deberían usar o idioma escollido pola persoa ou, se non escolleu, o do concello.
