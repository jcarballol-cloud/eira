# Progreso (rexistro vivo)

Última actualización: 2026-10-23, fin da sesión nocturna.

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
