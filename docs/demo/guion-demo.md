<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Guión da demostración v4 (≈ 4 minutos e medio)

**Preparación:** `python tools/tasks.py dev` (ou `docker compose up`) e abrir <http://localhost:8000>. Os datos de demo rexenéranse con `python manage.py seed_demo`; son ficticios e as reservas créanse arredor da hora actual.

No escritorio, a app da veciñanza e a do operario aparecen dentro dun **marco de teléfono**, e a do monitor nun de **tableta**. Na barra da demo está «Sen marco» para quitalo.

O mesmo percorrido está gravado en `docs/demo/eira-demo-movil.webm` e `docs/demo/eira-demo-escritorio.webm`, con subtítulos. As capturas de cada paso están en `docs/capturas/v3/pitch-*/` e as novidades da v4 en `docs/capturas/v4/`. Regénerase con `pytest tests/e2e/test_video.py`.

| Tempo | Pantalla | Que facer | Que dicir |
|---|---|---|---|
| 0:00 | Portada da demo: paso 1 «Escolle un concello» (Vilardeiras, rural pequeno) → portada de Vilardeiras | Botón **«Solicita a app de deportes»** | «Eira é software libre para a xestión deportiva municipal: reservas, acceso, mantemento e actividades nunha soa plataforma.» |
| 0:10 | Solicitude | Nome, apelidos, correo, **DNI 12345678Z** e **data 14/05/1990** (persoa ficticia do padrón da demo), «estou empadroada» → Enviar. Abrir a capa «Que facemos con estes datos» | «Alta automática: o DNI e a data coinciden co padrón que cargou o concello, e o código chega ao momento. Eira non garda o padrón: só un resumo criptográfico (HMAC) de cada liña, e o nome nunca se usa para comprobar. Se non coincide, o concello revisa cun clic.» |
| 0:25 | Correo simulado | Abrir o correo: ligazón e código de empadroamento | «Un código que só vale para este correo.» |
| 0:35 | Instalar → Abrir a app | Instrucións Android/iPhone → entrar co correo (código de 6 díxitos) → o código de empadroamento xa vén cuberto | «Sen contrasinais nin tendas de aplicacións.» |
| 0:50 | «Tes fillos ou persoas ao teu cargo?» | «Non, ir á app» | «A familia, desde o primeiro minuto.» |
| 0:55 | A miña saúde | Idade, peso e minutos → Gardar | «Quedan no teléfono. Non se envían a ningures.» |
| 1:05 | Pista de pádel → tira de días → pastilla **★** → resumo fixo «Reservar» | Prezo riscado, −20 % | «As franxas tranquilas son máis baratas: así repártese o uso.» |
| 1:15 | TPV simulado | **«Simular pagamento rexeitado»** → «Tentalo de novo» → Pagar | «Un rexeitamento nunca confirma: a franxa líbrase ao momento. Só a notificación asinada da pasarela confirma o pagamento.» |
| 1:40 | Reserva | **Para esta sesión**: 2–4 consellos dunha liña co tempo real da franxa (temperatura, sensación, UV, chuvia) e «Ver máis» coas fontes | «Consellos concretos, coa fonte: ACSM, OMS. Calculados no dispositivo.» |
| 1:55 | Simulador de pechadura | Código → **ABERTO** | «A pechadura non ten internet: segredo compartido e reloxo.» |
| 2:10 | Uxía → Checklist de peche | Porta si, todo en orde non; **«Que tal foi?» → Mal → «Luces avariadas»** | «Ao marchar, tres preguntas e unha valoración. Se é Mal, avísase ao concello.» |
| 2:25 | Concello → incidencia | Validar → Crear orde para Brais | «Na cabeceira, o concello; ninguén do persoal pode reservar como veciño.» |
| 2:40 | Brais (operario) | Só as súas ordes → checklist → Pechar | «Funciona sen cobertura. Uxía recibe «Arranxado!».» |
| 2:50 | Antía (tableta) → rexistro do grupo de 40 | Modo **Saída** → inicial do apelido → nome (icona de fotos) → RPE → «Grazas!» e volta soa | «Pensada para dedos de nenos e maiores; funciona sen conexión.» |
| 2:55 | Antía → **Estatísticas** | Asistencia por sesión, quen leva 3 sesións sen vir, esforzo medio e carga semanal (sRPE) | «Só os seus grupos. Cada gráfica ten a súa táboa.» |
| 3:05 | Concello → **Avisos** → Novo aviso | Alerta por vento, «reservas nas descubertas», franxa e «cancelar reservas» → **Vista previa**: app, push, correo e Telegram, e a cantas persoas chega → Enviar | «Un aviso, catro canles. Os peches e alertas chegan a quen lle afectan; as festas e novidades, só a quen deu o consentimento.» |
| 3:20 | Telegram simulado | Canle pública do concello e chat de Uxía co bot | «A canle pública non leva datos persoais. O bot persoal vincúlase cun código dun só uso.» |
| 3:30 | Concello → **Valoracións** | Índice, ranking e comentarios **sen nomes** | «A satisfacción, medida con cada uso.» |
| 3:45 | **Observatorio** | Filtros, fronte á OMS, grupos ocultos por n < 10, CSV/ODS | «Datos de actividade física anónimos para a política de saúde.» |
| 4:00 | **Deputación** | Comparativa con tendencia, por 1.000 hab. e satisfacción → «Consultar» un concello (aviso de só lectura) → «Dar de alta un concello» (6 pasos) | «Unha deputación desprega unha vez e dá servizo a todos. Software libre EUPL, datos exportables enteiros.» |

**Se sobra tempo:**
- Mostrador: «Altas da app» → folla co QR. **Padrón**: cargar o CSV (modelo descargable) e ver o rexistro de cargas; a cola de revisión mostra o motivo («Non figura no padrón cargado»).
- Veciña → Avisos → Preferencias: consentimento, canles por categoría e «Vincular Telegram» → simulador.
- Monitor na tableta: asistencia coas cámaras de fotos e esforzo unha persoa tras outra, con caras OMNI.
- Centro de privacidade.
- Mapa con teselas do servidor do concello.
