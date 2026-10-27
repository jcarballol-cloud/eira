# Progreso (rexistro vivo)

Última actualización: 2026-10-26, v5 (versión conxelada `v1.0-certame`).

## Ferramentas da máquina
- Python 3.13 (venv) ✔ · Docker 29 ✔ (arrancouse Docker Desktop durante a sesión) · Node 24 ✔ · Playwright + Chromium ✔
- **Non dispoñibles:** `make`, GNU gettext → substitutos en `tools/` (ver DECISIONS). `makemessages` execútase no contedor.

## Estado por prioridade

Lenda: ✅ feito e verificado (test ou comprobación) · 🟡 feito sen verificar · ⬜ pendente

### P0 — Esqueleto
- ✅ Repositorio, LICENSE (EUPL-1.2 oficial), README (gl), CLAUDE.md, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY
- ✅ publiccode.yml validado con publiccode-parser 5.4.3 (sen rede)
- ✅ 11 apps en `apps/`, configuración por variables de contorno, sen segredos
- ✅ `docker compose up --build` (app + PostgreSQL 16 + demo) — comprobado con peticións HTTP 200
- ✅ Makefile + `tools/tasks.py` (equivalente en Windows), `make licenses`, comprobación SPDX
- ✅ Pipeline da CI executado en local con PostgreSQL (non executado en GitHub: sen push)
- ✅ Sistema de deseño accesible (paleta, foco, texto grande, alto contraste, movemento reducido)

### P1 — Mínimos das bases — ✅ completo
Multi-concello (ruta, subdominio, dominio propio, illamento testado), consulta sen rexistro con
filtros e mapa + lista, ficha, grella semanal (libre/ocupada/recomendada), reserva en 3 pasos con
normas versionadas e pago simulado, cambio e cancelación con penalización, historial, recibos, .ics,
Google Calendar, avisos, acceso sen contrasinal + Cl@ve simulada, panel do día, alta asistida con
plantillas, horarios/peches con aviso, tarifas, normas versionadas, reserva en nome dun veciño,
indicadores con táboa e CSV, alta de concello en 3 pasos, galego e castelán completos.

### P2 — Diferencial — ✅ completo
Niveis de acceso 0–3, códigos sen conexión con documento técnico e bloqueo exponencial, simulador
de pechadura, checklist de peche → incidencia, incidencias con foto sen EXIF, mantemento preventivo,
calendario, app do operario con cola sen conexión (verificada en E2E con Playwright offline).

### P3 — Valor engadido — ✅ case completo
- ✅ Escolas: oferta, prazas, cota, lista de espera, inscrición de menores con consentimentos, pago
- ✅ Modo tableta: asistencia con nomes grandes, OMNI/Borg pictográfica, carga sRPE, probas (ALPHA-Fitness e SFT só nomes)
- ✅ Observatorio anónimo con umbral configurable (tests 9/10), seudonimización, referencia OMS
- ✅ Meteoroloxía simulada na reserva, alertas que pechan e avisan, esqueleto MeteoSIX
- ✅ Saúde no dispositivo (test E2E de rede), fontes documentadas
- ✅ Recomendación horaria
- ⬜ Push real (só adaptador simulado e endpoint de subscrición; sen botón na interface)

### P4 — Soberanía — ✅
Exportación/importación íntegra con test de ida e volta, exportación e borrado de datos persoais,
datos abertos CSV + DCAT-AP, asistente IA (fake + OpenAI-compatible local, só agregados),
declaración de accesibilidade e privacidade modelo, vista de deputación.

### P5 — Demostración — ✅
Datos ficticios (Vilardeiras, Pontedouro, Deputación das Marismas), selector de 7 perfís,
guión de 3 min verificado cun test E2E, 44 capturas automáticas en `docs/capturas/`.

## Mañá do 23/10
- ✅ Auditoría de publicación, demo pública preparada (Caddy) con RAM medida, vídeo do pitch, revisión de nomes.

## Números
- v2: 298 tests unitarios e de integración + 16 E2E (+2 de vídeo); axe en 68 páxinas × 3 viewports, 0 violacións.

## Bloqueos
- Ningún bloqueo activo. Ver riscos en `INFORME_MANANA.md`.

## v2 (tarde do 23/10)
- ✅ F0 aprendizaxes e plan · F1 ferramenta por perfil e permisos reais (65 tests de matriz) · F3 cobros crible (17 tests).
- ✅ F5 mapas: Referer de orixe, teselas por concello, política OSM documentada, E2E de teselas 200.
- ✅ F4 deseño: fotos libres de Commons con créditos, formulario con lapelas, accesibilidade con iconas, escala de esforzo nova.
- ✅ F7 valoracións, observatorio con filtros e exportación, comparativa da deputación e alta de concello en 6 pasos.
- ✅ F8 RXPD visible: matriz, RAT, textos modelo, centro de privacidade, menores de 14, fotos, cookies e conservación.
- ✅ F6 saúde: recomendacións persoais en cada reserva, no dispositivo (na conta só con consentimento art. 9).
- ✅ F9 guión e vídeos novos, 99 capturas en 3 viewports, axe en 68 páxinas × 3 viewports, rendemento, castelán completo, servidor da LAN.
- ✅ F2 alta: solicitar a app con padrón simulado, correo con ligazón e código, instalación Android/iPhone, primeira apertura, mostrador con folla QR, persoas apuntadas polo monitor e validadas polo concello (16 tests + E2E).

## v3 (23–24/10)
- **«Devolto/Devolta»: por que aparecía.**
  - Na axenda e no panel do día, a insignia «Devolta» saía en **todas as reservas canceladas** (o 9 % da demo: 768 de 8.409). A seed cancelaba ao chou e devolvía sempre o importe íntegro, sen motivo.
  - No panel do día, «Devolta» tamén era o botón e o estado da **chave** custodiada: dous significados para a mesma palabra.
  - Non había ningunha reserva confirmada ou usada con devolución: a lóxica de cobros era correcta.
  - **Corrección:**
    - Seed: ~4 % de cancelacións, todas con motivo, e o 20 % delas fóra de prazo e sen devolución.
    - Etiquetas: «Cancelada · importe devolto», «Cancelada · devolto en parte», «Cancelada · sen devolución» e, para a chave, «Chave devolta».
    - Tests: as etiquetas e a coherencia da seed (devolucións só en canceladas, con motivo, < 5 % e nunca maiores ca o pagado).
- ✅ v3: 5 ferramentas de demo e Cl@ve · 2 selector de franxas · 1 densidade · 6 tableta tipo AFS +50 · 4 portada da demo · 8 pé, menú e «Devolto» · 3 consellos co tempo · 7 axenda en calendario · 9 vídeos, capturas e castelán.
- Números v3: 332 tests unitarios/integración + 35 E2E (+2 de vídeo); axe 72 páxinas × 3 viewports, 0 violacións.

## v4 (24/10)
- ✅ 1 cero scroll horizontal: test de desbordamento (360/390 px, texto normal e grande, e no marco). Historial en tarxetas en móbil, `.kv` e insignias que parten, tarxetas de instalación e tableta estreita. Código de acceso con `clamp()`, en 3+3 e lido díxito a díxito.
- ✅ 3 tableta: estado da sesión pola hora (a causa de «Pechada» era que gardar o esforzo pechaba a sesión aínda que non empezara). Saída → RPE directo con aviso discreto se se marcou soa. Estatísticas da monitora.
- ✅ 6 barras con escala honesta (porcentaxes de 0 a 100, satisfacción de 0 a 100, absolutos ao máximo e indicándoo), filtro `signed` («▼ −42») e variación tamén no resumo; capturas antes/despois.
- ✅ 7 cabeceira «Ferramentas da demo» (concello e perfil), «← Volver á demo» á última páxina e sen «Acceder».
- ✅ 10 avisos do concello:
  - redacción con vista previa por canle, segmentación, programación e cancelación de reservas;
  - Telegram: canle pública, bot con código, adaptador real co token só no contorno e simulador;
  - preferencias por categoría e canle, con consentimento;
  - bandexa de correo real;
  - seed de 18+1 avisos;
  - `docs/rxpd/avisos.md`.
- ✅ 2 busca compacta (unha liña, «Filtros (n)», chips, Lista/Mapa segmentado).
- ✅ 4 padrón semiautomático (CSV → HMAC, alta automática, cola co motivo, rexistro de cargas, modelo CSV), RAT e capa informativa.
- ✅ 9 apelidos obrigatorios ao inscribir menores.

## v4.1 · Axustes visuais rápidos (24/10)
- ✅ Configuración: módulos en columna fixa de 280 px (sticky; debaixo por baixo de 1200 px), seccións emparelladas sen ocos, nota do padrón unha vez, contacto e DPD sen cortes.
- ✅ Botón «Día / Noite» (barra de demo e enriba do marco), tema na sesión ou do sistema, crossfade da cabeceira (sen animación con movemento reducido), tema escuro AA en veciñanza, operario e tableta.
- ✅ Perfil «Brais · veciño novo» sen actividade, filtro «Mañá» do operario con estado baleiro e catálogo `/dev/ilustracions/`.

## v5 · Versión definitiva (26/10)
Regra: só se engade. Choques anotados en DECISIONS («Choque»).
- ✅ C · participantes (obrigatorio, máximo por instalación), formas de pagamento (TPV, oficina con prazo, gratuíta, bono, aprazado desactivado por defecto), conciliación por forma de pagamento, aprobación do concello (con devolución automática ao rexeitar e cambios pendentes), suplemento de luz (solpor NOAA ou horario fixo, «necesito luz», desglose antes de pagar e no recibo, nivel 3 só con suplemento). 17 tests.
- ✅ A · reservar en concellos próximos da rede coa mesma conta (selector, «Concellos próximos», tarifa de non empadroada, TPV do destino, opción/cupo/antelación por concello, actividades e eventos opcionais en «Avisos»), RXPD na matriz. 7 tests + E2E.
- ✅ B · ficha de seguridade (material, protocolo, DEA, 112, última supervisión calculada) e cartel A4 en PDF etiquetado + plantilla co escudo. 5 tests (con H).
- ✅ D · estado ao entrar con incidencia atribuída a antes da reserva; entrada e saída xuntas na ficha (veciña, operario/a e concello).
- ✅ E · botón «?» con axuda contextual e guía, «Incidencia ou seguridade» (risco con prioridade alta, 112), linguaxe inclusiva (guía e test), modo básico/avanzado.
- ✅ F · «Quen custodia os teus datos» xerada da matriz, rexistro de brechas (admin e DPD), comunicación modelo, protocolo en docs/rxpd/brechas.md. 9 tests.
- ✅ G · índice de vida activa (n ≥ 10, pesos configurables) na ficha, no panel e na deputación. 4 tests.
- ✅ H · plantilla «Revisión de seguridade inicial Eira» e «Revisada o ‹data›»; docs/servizos.md.
- ✅ I · demo v5, guión con paso novo (pitch 2:14 sen pista de subtítulos), anexo de 54 s, 42 capturas en docs/capturas/v5/, informe e etiqueta `v1.0-certame`.
- Números v5: 616 tests unitarios/integración + 54 E2E; axe 105 páxinas × 3 tamaños e 41 en escuro, 0 violacións. RAM sen IA ≈ 270 MiB (Docker).

## v1.1 · Rexistro de limpeza (26/10)
Regra: só se engade. Choques anotados en DECISIONS (v1.1).
- ✅ 1 rol «Persoal de limpeza» (propio ou de empresa contratada), mesma app do operario só coas tarefas de limpeza; matriz de roles ampliada.
- ✅ 2 plans de limpeza co motor preventivo (tipo de tarefa, zonas, «varias veces ao día», checklist) e modelos nas plantillas de instalación.
- ✅ 3 QR por zona imprimible; checklist con quen, data e hora, tarefas e foto opcional; sen conexión coa mesma cola (E2E sen rede).
- ✅ 4 «Última limpeza» na ficha pública e aviso ao concello cando unha zona se atrasa.
- ✅ 5 enrutado por tipo (limpeza → persoal de limpeza; avarías → mantemento; o concello ve todo) e etiqueta «limpeza» no estado ao entrar e no checklist de saída.
- ✅ 6 exportación CSV/ODS/PDF por instalación e período; −10 en «Mantemento ao día» se hai zonas atrasadas.
- ✅ 7 demo: Noela (empresa ficticia), plans no pavillón e vestiarios, 3 semanas de rexistros, aseos atrasados co aviso, perfil novo na portada.
- ✅ 8 22 capturas en docs/capturas/v1.1/, sección v1.1 no informe, etiqueta `v1.1-certame`.
- Números v1.1: 683 tests unitarios/integración + 58 E2E; axe 115 páxinas × 3 tamaños e 47 en escuro, 0 violacións.

## v1.2 · Aportacións do equipo (27/10)
Regra: só se engade. Choques anotados en DECISIONS (v1.2). Orde de prioridade: A → C → B → E → F → D → G → H → I.
- ✅ A · «Aviso» e «Alerta» (forma, cor e texto), protocolo de accidente paso a paso por concello e instalación, 112, DESA, aviso automático, rexistro mínimo de accidentes (admin + DPD, conservación configurable), incidencia de prioridade máxima, botóns na reserva en curso e «Alerta» na tableta.
- ✅ C · accesibilidade detallada (7 puntos si/parcial/non que encheen a lista básica), sostibilidade, DESA (na instalación ou o máis próximo co adaptador `defibrillators`), filtros «Accesible», «Con aparcabicis» e «Con DESA», revisión de seguridade (+3 puntos) e índice de vida activa coa accesibilidade detallada.
- ✅ B · peche sen confirmar: recordatorio push → app + canle → persoa responsable por orde e horario; a Policía Local só por decisión dunha persoa (rexistrada); estado da porta no nivel 3 (simulador); incumprimento só se o concello o activa.
- ✅ E · enquisa anual con NPS (n ≥ 10, unha resposta por persoa, sete aspectos, evolución por ano e instalación), aviso por app/correo/Telegram, NPS tras o uso opcional (desactivado por defecto), panel e comparativa da deputación.
- ✅ F · paso a paso Elixe → Paga → Confirma, «que tes que facer e cando», recordatorios ás 24 h e 2 h con «Confirmo»/«Cancelo», lista de espera nas franxas (cancelación, sen confirmar se o concello o activa, sen check-in aos 15 min) con oferta por orde, rexistro do ciclo e devolución da penalización se se volve vender.
- ✅ D · inventario de equipos e lecturas de facturas, consumo estimado (kWh, €, CO₂) por semana/mes/ano, ocupación reservada e real, tempo medio, kWh e € por hora de uso, perfil agregado (n ≥ 10), tendencia mensual, estimado fronte a real; comparativa da deputación só agregada; docs/rendemento-instalacions.md.
- ✅ G · «Busco xente» desde a reserva, «Partidas abertas» (propio concello e próximos, filtros por deporte, día e nivel), solicitudes que acepta quen organiza, mensaxes predefinidas, nome de pila e inicial, menores de 14 fóra, reparto orientativo, denuncias e módulo desactivable.
- ✅ H · tipos de abono e abonos (TPV e oficina, renovación encadeada), desconto que se suma ás tarifas, carné na app con QR dinámico asinado (3 min), carné imprimible en PDF etiquetado tamaño tarxeta e anulable, lector do persoal (entrada e bonos), «Ler carné» na tableta (a lista por nome mantense), adaptador simulado `municipal_card` e docs/carne-municipal.md.
- ✅ I · demo v1.2 coherente, 65 capturas en docs/capturas/v1.2/ (A–H en móbil e escritorio; A, D e H tamén en escuro), anexo regrabado (65 s), RAM medida en Docker, sección v1.2 no informe, etiqueta `v1.2-certame`.

## v1.3 · Documentación para a adopción e publicación (27/10)
Regra: só se engade. Decisións en DECISIONS (v1.3).
- ✅ A · `docs/concello/ordenanza-modelo.md` (gl + es): prezo público e variante de taxa, cada artigo co campo de Eira. Engadido á configuración o desconto de baixa demanda (non era editable).
- ✅ B · `docs/rxpd/eipd-plantilla.md` cuberta co que fai Eira; resumo na app (`privacidade/avaliacion-impacto/`) enlazado desde «Quen custodia os teus datos»; ligazón desde a matriz.
- ✅ C · dobre factor TOTP (opcional por persoa, obrigatorio por concello para administración e DPD, e por agrupación para a deputación), 10 códigos de recuperación, restablecemento por outra administración; rexistro de auditoría consultable (administración e DPD) con categorías, filtros e CSV; retirada de roles e descargas do persoal rexistradas. 34 tests novos + 4 E2E.
- ✅ D · auditoría de todo o historial (65 commits, todas as referencias): sen segredos, documentos alleos, rutas nin correos reais; 4 puntos para decidir. README (demo en 5 minutos, licenza, contribucións), `publiccode.yml` validado, `GOVERNANCE.md`.
- ✅ E · sección v1.3 no informe, etiqueta `v1.3-certame`.
