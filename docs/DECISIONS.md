# Rexistro de decisións

Formato: data · decisión · motivo · alternativas descartadas.

> **Capturas:** as rutas `docs/capturas/v…/` que se citan aquí son das capturas completas, que non están no repositorio: publicaranse no adxunto `capturas-v1.4.zip` da versión **v1.4-certame** (ver [capturas/README.md](capturas/README.md)). No repositorio quedan as 6 capturas clave do README.

## 2026-10-23 · Python 3.13 no entorno local
- **Decisión:** venv con Python 3.13 (a máquina ten 3.13 e 3.14). Docker usa `python:3.13-slim`.
- **Motivo:** Django 5.2 LTS está probado en 3.13; 3.14 aínda é moi recente para todo o ecosistema.
- **Descartado:** 3.14 (risco de rodas binarias inexistentes para Pillow/psycopg).

## 2026-10-23 · Django 5.2 LTS
- **Decisión:** Django 5.2 (LTS ata abril de 2028).
- **Motivo:** o prompt pide Django 5; a LTS dálle viabilidade a un concello.

## 2026-10-23 · Sen `make` nin gettext na máquina
- **Decisión:** `tools/tasks.py` replica cada obxectivo do `Makefile` (o Makefile chámao). As traducións compílanse con `polib` (`tools/compile_messages.py`). A extracción con `makemessages` faise no contedor (a imaxe inclúe gettext).
- **Motivo:** Windows sen make/gettext; non instalar software no sistema sen permiso.
- **Descartado:** escribir un extractor propio de cadeas (fráxil con `blocktranslate`).

## 2026-10-23 · Cadeas da interface en galego como msgid
- **Decisión:** os textos da interface escríbense directamente en galego dentro de `{% translate %}`/`gettext`. O castelán tradúcese en `locale/es/`. O galego queda sempre completo por construción.
- **Motivo:** o galego é o idioma por defecto e principal; evita que falten cadeas en galego e reduce á metade o traballo de tradución. O código e os nomes técnicos seguen en inglés.
- **Descartado:** msgid en inglés con dúas traducións (máis traballo e risco de galego incompleto).

## 2026-10-23 · Resolución do concello
- **Decisión:** rutas `/c/<slug>/…` como canónicas; o subdominio `<slug>.EIRA_BASE_DOMAIN` ou o dominio propio reescriben internamente a ruta (`SubdomainTenantMiddleware`). O `TenantMiddleware` converte o kwarg `tenant` en `request.tenant` e carga os roles.
- **Motivo:** un único enrutado para ambos modos; funciona en local sen DNS.
- **Descartado:** esquemas de PostgreSQL por concello (django-tenants): máis complexo de operar para concellos pequenos e incompatible con SQLite en local. O illamento faise por chave foránea `municipality` + tests.

## 2026-10-23 · Contas globais e roles por concello
- **Decisión:** unha persoa ten unha única conta e roles (`Membership`) en cada concello; `region_admin` vén de `RegionMembership` e dá permisos de administración nos concellos da agrupación.
- **Motivo:** unha veciña pode usar instalacións de varios concellos da mesma comarca.

## 2026-10-23 · Empadroamento sen acceso ao padrón
- **Decisión:** o concello entrega un código de invitación (mostrador ou carta) que a persoa introduce na súa conta. Eira só garda «empadroada en X, validada o día D, por método M».
- **Motivo:** minimización; os concellos pequenos non teñen API de padrón. Preparado para validarse con identidade pública no futuro.

## 2026-10-23 · Idade só por ano de nacemento
- **Decisión:** gárdase `birth_year` (opcional), non a data completa.
- **Motivo:** abonda para tarifas (mocidade/maiores) e minimiza datos.

## 2026-10-23 · Esquema de códigos sen conexión (nivel 2)
- **Decisión:** HOTP (RFC 4226) cun contador `C = bloque·16 + duración`, bloques de 30 min, tolerancia ±10 min, 6 díxitos, ata 8 bloques; bloqueo de 5 min tras 5 fallos. Detalle e análise en `docs/access/offline-codes.md`.
- **Motivo:** a pechadura non necesita rede nin coñecer as reservas; só o segredo e a hora.
- **Descartado:** TOTP puro (non liga o código á duración da franxa); códigos asinados longos (incómodos de teclear).

## 2026-10-23 · Recomendación horaria
- **Decisión:** «Recomendada» = como moito as 2 franxas libres por día con menor ocupación histórica (8 semanas) e por baixo do 30 %. Sen histórico suficiente (menos de 10 reservas) non se recomenda nada.
- **Motivo:** se se recomendan moitas franxas o sinal perde valor (detectado ao revisar a grella).

## 2026-10-23 · Peches: cancelación con devolución íntegra
- **Decisión:** ao crear un peche ou alerta, as reservas afectadas cancélanse automaticamente con devolución íntegra e aviso.
- **Motivo:** o prompt pide aviso automático; reubicar automaticamente sería opaco para a persoa.
- **Alternativa futura:** ofrecer franxas alternativas no aviso.

## 2026-10-23 · Gráficos de barras en HTML
- **Decisión:** barras horizontais en HTML/CSS (ancho por clases `.w-N`), sempre con táboa alternativa e CSV.
- **Motivo:** sen dependencias JS, compatibles coa CSP, escalan co texto grande e en móbil.
- **Descartado:** SVG no servidor (primeira versión): o texto quedaba diminuto en móbil e a localización de números en galego rompía os atributos.

## 2026-10-23 · CSP estrita
- **Decisión:** sen `unsafe-inline` (agás no `/admin/` de Django). Cor do concello servida como CSS dinámico (`/c/<slug>/tema.css`); anchos de barras con clases `.w-N`.

## 2026-10-23 · Mapa
- **Decisión:** Leaflet 1.9.4 vendorizado; teselas OSM por defecto e configurables (`EIRA_TILE_URL`) para que unha deputación poida usar o seu servidor. A lista accesible é a vista principal; o mapa é opcional (`?vista=mapa`).

## 2026-10-23 · Nomes ficticios da demo
- **Decisión:** concellos «Vilardeiras» (rural, 1.840 hab.) e «Pontedouro» (mediano, 14.250 hab.), «Deputación das Marismas». Códigos INE ficticios 99001/99002 e dominios `.example`.
- **Motivo:** non coinciden con ningún concello galego real nin cos nomes doutra candidatura.

## 2026-10-23 · Regra DJ008 de ruff desactivada
- **Decisión:** non se esixe `__str__` en modelos internos (rexistros, táboas intermedias).

## 2026-10-23 · Módulos chamados `manage.py` dentro das apps
- **Decisión:** as vistas de xestión viven en `apps/<app>/manage.py`. Por iso `pytest` leva `django_find_project = false` (pytest-django confundíaos co `manage.py` do proxecto).

## 2026-10-23 · Revisión dos nomes ficticios (mañá)
- **Decisión:** mantéñense «Vilardeiras», «Pontedouro» e «Deputación das Marismas».
- **Comprobación:** buscas web estándar e ampliadas dos nomes exactos (23/10/2026): non aparece ningún concello, parroquia, lugar nin deputación/mancomunidade con eses nomes en Galicia. Os máis parecidos son Vilardevós (concello de Ourense), Pontedeume (concello da Coruña) e «Las Marismas» (Andalucía). Non se consultou o Nomenclátor do IGE directamente (pendente).
- **Aviso:** os nomes das parroquias dentro dos concellos ficticios (Bustelo, A Pereira, Outeiro, Fontela, San Martiño, Centro, A Ribeira, Monteagudo, O Castro, Lamas) son topónimos xenéricos que existen en moitos lugares reais de Galicia (p. ex. Monteagudo é unha parroquia de Arteixo). Mantéñense porque sempre aparecen dentro dun concello inexistente; se se quere evitar calquera coincidencia, cambiar a lista en `apps/tenants/management/commands/seed_demo.py` (`MUNICIPALITIES[*]["parishes"]`).

## 2026-10-23 · Esquema OpenAPI independente do motor
- **Decisión:** `tools/tasks.py openapi` xera sempre o esquema con SQLite en memoria.
- **Motivo:** drf-spectacular deriva os límites dos enteiros da base de datos; con PostgreSQL (CI) o ficheiro cambiaba e a comprobación `git diff --exit-code` da CI fallaría.

## 2026-10-23 · Franxas xa empezadas
- **Decisión:** unha franxa que xa comezou non se mostra como reservable.
- **Motivo:** a grella ofrecíaa como libre e despois a reserva rexeitábaa (detectado nas probas E2E á hora de comer).

## 2026-10-23 · Demo pública
- **Decisión:** compose de produción con Caddy (HTTPS automático, Let's Encrypt gratuíto), servizo `reseed` cun bucle de shell en vez de cron, e bloqueo consultivo de PostgreSQL en `seed_demo` para que nunca se executen dúas cargas á vez.
- **Descartado:** cron/supercronic nun contedor aparte (dependencia extra); Traefik (máis configuración).

## 2026-10-23 · v2 F1 · Cada perfil, a súa ferramenta
- **Decisión:** o perfil efectivo no concello é o rol de máis responsabilidade (admin > deputación > mantemento > monitora > veciñanza). **O persoal non usa a app da veciñanza coa mesma conta:** se tamén é veciño, usa outra conta. As vistas da app (`neighbour_required`) dan 403 a calquera rol de persoal.
- **Motivo:** permisos simples e verificables; evita que a administración «reserve como veciña» por erro (petición explícita).
- **Descartado:** un selector de modo dentro da mesma conta (máis complexo e fácil de saltar).

- **Decisión:** o operario ve só as ordes **asignadas a el e as pendentes sen asignar** (para poder collelas); calquera outra orde dá 404. A administración xestiona as ordes desde `/xestion/ordes/` e xa non entra na app do operario.
- **Decisión:** a tableta é só da monitora (`role_required("monitor")`); a administración ve as escolas na xestión.

- **Decisión:** a deputación entra nos concellos en **modo consulta**: lectura permitida; calquera POST dá 403 agás as vistas marcadas con `@support_action`. Na interface hai un banner «Estás vendo X como Deputación · só lectura · Volver á rede» e ocúltanse os botóns de escritura (a garantía está no backend).
- **Accións de soporte permitidas:** exportar os datos do concello (lectura) e reenviar a invitación á administración do concello (fase 7).

- **Decisión:** catro disposicións: pública (sen sesión), app móbil (veciñanza e operario, con barra de lapelas inferior), tableta (monitora) e escritorio con barra lateral (concello e deputación). Unha única `base.html` escolle a disposición segundo o perfil.
- **Decisión:** marco de dispositivo para a demo con `?marco=0/1` (cookie); por defecto activo cando `EIRA_DEMO_TOOLS=1`. Por CSS só aparece en pantallas grandes (≥ 700 px para o móbil e ≥ 1100 px para a tableta); nun móbil real a app ocupa a pantalla.
- **Decisión:** o logo leva sempre á pantalla principal do perfil (`profiles.home_url`); «Saír» está sempre na cabeceira e «Cambiar de perfil» na barra de demo.

## 2026-10-23 · v2 F3 · Cobros
- **Fallo corrixido:** o TPV simulado permitía cambiar o resultado dunha operación xa resolta (KO → «atrás» → «Pagar») e a volta do navegador era a que decidía. Agora:
  - **só a notificación servidor a servidor asinada** (HMAC-SHA256 sobre os parámetros en base64, como Redsys) cambia o estado do pagamento;
  - un pagamento resolto xa non cambia nunca;
  - a URL de volta só mostra o estado (e consulta cada 2 s mentres está pendente).
- **Estados:** `Payment` (pendente → pagado | rexeitado | caducado | devolto/devolto en parte) e `Booking` (`pending_payment` → `confirmed` | `rejected` | `expired`, ademais de `cancelled`/`used`/`no_show`).
- **Rexeitado:** libera a franxa ao momento e envía un aviso de «pagamento non completado» só na app (non por correo), nunca unha confirmación.
- **Bloqueo:** 10 min (`EIRA_PAYMENT_HOLD_MINUTES`). Un pagamento aceptado que chega tarde confírmase se a franxa segue libre; se non, devólvese automaticamente e avísase.
- **Reservas feitas polo persoal sen cobrar:** a franxa gárdase ata a hora de uso para cobrar no mostrador (decisión práctica para concellos pequenos).
- **Tarifas:** aplícase a **máis favorable** entre as que lle corresponden á persoa (empadroamento, idade, colectivo validado). A tarifa reducida valídaa o persoal (`Eligibility`), que só garda o colectivo e a data, nunca a documentación.
- **Desconto en franxas tranquilas:** é o das franxas «recomendadas» (como moito 2 por día e por instalación). Configurable por concello (por defecto −20 %; 0 desactívao) e gárdase na reserva (prezo base e %).
- **Recibo PDF:** xerador mínimo propio (Helvetica e WinAnsi, unha páxina), sen dependencias.

## v2 F5 — Teselas do mapa
- O 403 das teselas de OSM debíase á política global `Referrer-Policy: same-origin`. Non se relaxa: a capa de Leaflet envía só a orixe (`referrerPolicy`). Así a URL das páxinas non sae a terceiros.
- O servidor de teselas é configurable por concello (URL, atribución e ligazón). A orixe da CSP dedúcese da URL, polo que xa non hai que manter `EIRA_TILE_ORIGIN` a man.
- `tile.openstreetmap.org` só para a demo. Recoméndase un servidor propio ou da deputación (`docs/despregamento.md`).

## v2 F2 — Alta como na vida real
- **Padrón detrás dun adaptador (`padron`).** Eira non copia o padrón: pregunta «figura?» e garda só o resultado.
  - Simulado: recoñece os códigos postais do termo (`Municipality.postcodes`).
  - Real: esqueleto `SvdrPadronAdapter`, para o Servizo de Verificación de Datos de Residencia da PID ou o servizo web do padrón municipal.
- **Solicitar a app.**
  - Se o padrón coincide: correo coa ligazón `/app/instalar/?codigo=…` e o código de empadroamento.
  - Se non coincide: queda pendente para o concello.
  - Quen non está empadroado recibe a app sen código (tarifa xeral).
- **Os códigos enviados a un correo só valen para esa conta** (`ResidencyInvitation.email`). Así un correo reenviado non serve. O código admite minúsculas e sen guión.
- **Primeira apertura.** A páxina de instalación garda o código na sesión. «Abrir a app» → acceso por correo → código xa cuberto → «Tes fillos ou persoas ao teu cargo?». O inicio da app repite esta pregunta mentres non haxa menores engadidos.
- **PWA, non tendas de aplicacións.** Botón «Instalar agora» con `beforeinstallprompt` cando o navegador o ofrece; instrucións para Android e iPhone sempre visibles (iOS non ten API de instalación).
- **Mostrador.** Alta asistida co empadroamento comprobado no momento e folla imprimible co QR, o código e os pasos. O correo é opcional, para quen non o ten.
- **Monitor.** Pode apuntar a alguén que aparece na pista sen inscrición. Non conta para a asistencia nin para o esforzo ata que o concello o valida.
  - Para validar un menor fai falta marcar a autorización en papel. Queda como consentimento `text_version="papel"`.
  - O concello pode descartar a persoa.
- **Contido que responde ao panel (container queries):** os marcos de teléfono e tableta da demo vense coma os dispositivos reais.

## v2 F4 — Deseño
- **Fotos de referencia libres (16, de Wikimedia Commons).**
  - Licenzas aceptadas: CC0, CC BY, CC BY-SA e dominio público. Cada licenza comprobouse unha por unha cunha consulta individual á API.
  - Escolléronse detalles ou espazos baleiros: sen persoas identificables nin marcas.
  - Tratamento: recorte a 3:2, sen EXIF, WebP en 480/960/1440 px, `loading="lazy"`, `srcset` e texto alternativo propio en galego.
  - Créditos en `CREDITS.md`, en `/creditos/` e no pé da foto na ficha.
  - As fotos CC BY-SA modificadas seguen baixo CC BY-SA, non baixo a EUPL.
- **Fotos do concello.** Se o concello sube unha, substitúe a de referencia. Gárdase reencodada (sen metadatos) e xéranse as variantes WebP.
- **Formulario da instalación.**
  - Lapelas WAI-ARIA (frechas, Inicio, Fin). Sen JavaScript vense todas as seccións seguidas.
  - Se hai erros, ábrese a lapela que os ten e esta leva a marca «!».
- **Accesibilidade física.** Sete características, cada unha cunha icona de liña: sen chanzos, ascensor, aseo, vestiario, aparcadoiro, bucle magnético e braille. Na ficha amósanse como lista limpa.
- **Escala de esforzo (patrón do quiosco de AFS +50, sen datos).**
  - Unha persoa por pantalla e avance automático aos 650 ms. Pódese ir a «Anterior» ou «Saltar», e ao final hai un resumo antes de pechar.
  - Cores OKLCH (L 0.86, C 0.07, matiz de 150° a 30°).
  - Infancia: cinco caras OMNI de debuxo propio. Adultos: número grande coa etiqueta Borg CR-10.
  - Quen non ten consentimento sáltase. Sen JavaScript, todas as persoas na mesma páxina.
- `[hidden]` gaña sempre ao `display` dos compoñentes, e os `input` ocultos non tapan os clics.

## v2 F7 — Valoracións e observatorio
- **«Que tal foi?»**: Ben, Regular ou Mal, con 11 etiquetas (positivas e negativas) e un comentario de ata 500 caracteres.
  - Vai integrado no checklist de peche, e alí é opcional. Tamén se pode valorar despois, desde a reserva. Unha valoración por reserva.
  - «Mal» co aviso marcado crea unha incidencia. A categoría sae da primeira etiqueta negativa (luces → iluminación; porta → acceso…).
- **Privacidade nas valoracións.** O concello ve os comentarios sen nome nin correo. O CSV/ODS só leva agregados por instalación, sen comentarios.
- **Índice de satisfacción 0–100** (Ben = 100, Regular = 50, Mal = 0). No ranking só entran instalacións con 5 valoracións ou máis; as demais aparecen entre parénteses.
- **Observatorio.**
  - Filtros por período (6, 12 ou 26 semanas) e por actividade.
  - Gráficas HTML/SVG sen JavaScript nin estilos en liña, cada unha coa súa táboa.
  - Exportación CSV/ODS de agregados, coas celas suprimidas como `<10`. Os microdatos seudonimizados quedan só para o concello.
  - Os números dos atributos SVG xéranse en Python con punto decimal, porque a localización galega pon coma.
- **Deputación.**
  - Comparativa coa variación fronte ao período anterior, reservas por 1.000 habitantes, satisfacción, horas ata resolver incidencias e ingresos por habitante, máis CSV/ODS.
  - Acción de soporte «Reenviar invitación», só para concellos da propia rede.
- **Alta dun concello en 6 pasos:** datos, responsable, módulos, imaxe (escudo limpo de metadatos e cor con contraste AA comprobado), primeira instalación con plantilla (sen publicar) e invitación con vista previa. Non se pode saltar pasos.

## v2 F8 — RXPD visible
- **Documentos.** Matriz de visibilidade por perfil (`docs/rxpd/matriz.md`, cuberta por probas), rexistro de actividades de tratamento (`docs/rxpd/rat.md`) e textos modelo (`docs/rxpd/textos-modelo.md`).
- **Centro de privacidade (`/conta/privacidade/`).**
  - Contadores de que datos hai.
  - Interruptores: avisos e imaxe. O consentimento de imaxe garda a data e queda no rexistro de auditoría.
  - Resumo dos consentimentos dos menores, descarga JSON e borrado da conta.
  - DPD de cada concello co que se ten relación (campo novo `dpo_contact`) e a AEPD.
  - As cookies, explicadas.
- **Menores (art. 7 LOPDGDD).** Por debaixo dos 14 anos consente a familia. Con 14 ou máis faise o rexistro igual, pero hai que confirmar que o menor está de acordo.
- **Imaxe.** Cámara verde ou cámara riscada en vermello, por persoa:
  - Na asistencia da tableta, o filtro «Só quen non pode saír en fotos» é só visual (CSS `:has()`), porque un filtro no servidor marcaría como ausentes as persoas ocultas ao gardar.
  - Na ficha do grupo do concello, o filtro vai na URL (`?sen_fotos=1`).
- **Conservación.** `booking_maintenance` borra as solicitudes da app aos 12 meses (RAT n.º 10).
- **Cookies.** Unha proba percorre páxinas públicas, da veciñanza e do concello e falla se aparece algunha cookie que non sexa técnica.
- **Deputación.** A matriz recolle con honestidade que ve o mesmo ca o concello, en só lectura.

## v2 F6 — Saúde personalizada
- **Motor en JavaScript, no navegador** (`static/js/health-engine.js`). Así o peso e a idade non saen do dispositivo por defecto, e non hai un segundo motor en Python que manter sincronizado. As regras, os limiares e as fontes están en `docs/health/recomendacions.md`.
- **Dentro de cada reserva**: icona, título, texto, cantidade e fonte.
  - Auga antes, coa hora concreta (inicio − 4 h); durante; sales; aviso de hiponatremia; hidratos; despois; tempo; idade; semana OMS.
  - Sen perfil, consellos cualitativos e unha ligazón para engadilo.
- **Prudencia.**
  - Cantidades por peso só para persoas adultas.
  - «Punto de partida» nas cantidades durante a sesión.
  - Sen taxa de suor inventada.
  - Aviso «non é consello clínico».
- **Gardado na conta (opcional, art. 9.2.a).**
  - `HealthProfile` con consentimento explícito e versionado, rexistrado en auditoría, e botón de borrado.
  - Fóra do admin técnico, da exportación do concello e do observatorio.
  - Si na exportación persoal (art. 15).
- **Probas.**
  - Python: o persoal non ve o dato en ningunha páxina nin no ZIP de portabilidade, e o gardado esixe consentimento.
  - E2E: as recomendacións calcúlanse no dispositivo e ningunha petición leva o peso.

## v3 · 5 — Ferramentas de demo e Cl@ve
- **Ferramentas de demo independentes.** Correo, outras canles e pechadura usan `templates/dev/base.html`, un deseño neutro que nunca herda o marco, as pestanas nin o menú do perfil. TPV e Cl@ve usan esa mesma base co rótulo «Simulación dun servizo externo». Dende a barra de demo ábrense nunha pestana nova.
- **Correo:** `white-space: pre-wrap` e `overflow-wrap: anywhere`, con ligazóns pulsables (`urlize`).
- **Pechadura: «cousas raras» reproducidas e corrixidas.**
  1. O bloqueo por intentos usaba o reloxo **simulado**. Ao fallar 5 veces cunha hora futura, `locked_until` quedaba horas por diante en tempo real e o teclado ficaba bloqueado para todas as persoas que probaban a demo. Agora `validate_code(..., lock_clock=)` aplica o bloqueo co tempo real no simulador; nunha pechadura real os dous reloxos son o mesmo.
  2. Desde a barra abría sempre o primeiro dispositivo da base de datos, e o código da persoa daba DENEGADO. Agora, con sesión, preselecciona o dispositivo e a hora da súa próxima reserva de nivel 2.
  3. Engadín o botón «Restablecer a pechadura (só demo)».
  4. En escritorio, teclado e «Como funciona» van en dúas columnas; en móbil, unha debaixo da outra.
- **Cl@ve.** Con outra sesión aberta, `login()` baleira a sesión ao cambiar de persoa, perdíase o destino e a persoa acababa en Pontedouro, que é o primeiro concello alfabeticamente. Agora o destino e o último concello visitado (`last_tenant`, gardado só se xa hai sesión) lense antes de `login()`. Se a identificación caduca ou se reutiliza, explícase e mantense o destino. O mesmo arranxo aplícase ao acceso por código.

## v3 · 2 — Selector de franxas
- **Problema reproducido** (`docs/capturas/v3/franxas-antes-movil.png`): no móbil, un acordeón por día cunha liña por franxa (moito scroll) e a palabra «Recomendada» dentro do botón.
- **Deseño novo:**
  - **Tira de 7 días** (lapelas WAI-ARIA, frechas, Inicio e Fin), con puntos que indican franxas tranquilas (ámbar) e reserva propia (verde).
  - Debaixo, unha **grella de pastillas** de ~5 rem coa hora e o prezo:
    - tranquila: ★ e prezo con desconto, co prezo base tachado;
    - ocupada ou pechada: atenuada, con borde descontinuo, hora riscada e texto «Ocupada»;
    - propia: ✓.
  - **Lenda** unha soa vez e **resumo fixo** («Sáb 24 · 09:00–10:30 · 3,20 € ~~4,00 €~~ · Reservar»).
- **Melloras sobre a proposta, e por que:**
  - Tocar unha pastilla **escolle**, non navega: así pódese comparar e corrixir antes de reservar. O botón do resumo leva á confirmación.
  - Sen JavaScript, a pastilla é unha ligazón directa e amósanse todos os días seguidos.
  - As franxas **pasadas non se amosan** (menos ruído); un día sen franxas di «Non quedan franxas este día».
  - A navegación entre semanas queda como frechas ‹ › co mes.
- **Accesibilidade.**
  - Cada pastilla ten `aria-label` completo («sábado 24, 15:00, libre, recomendada, 3,20 € en vez de 4,00 €»).
  - O estado non depende só da cor: hai ★, ✓, texto e liña de borde.
  - A escollida leva `aria-current`.
- **Prezo por franxa.** `week_grid` calcula a tarifa máis favorable da persoa unha vez e aplícalle o desconto de cada franxa. No modo concello non se amosan prezos.
- **Texto grande:** pastillas máis altas e en dúas columnas; nunha columna en pantallas moi estreitas.
- **Igual en toda a app.** É o mesmo compoñente para a veciñanza, «Reservar por alguén» e «Cambiar hora». A app da veciñanza sempre é dunha columna, tamén no escritorio sen marco.

## v3 · 1 — Densidade
- **Escala compacta por defecto** (capa final do CSS, `html:not(.pref-large-text) body:not(.layout-tablet)`):
  - base de 15 px (93,75 %) e liña de 1,45;
  - títulos máis pequenos;
  - botóns de 38 px (30 px os pequenos e 44 px os grandes) e campos de 38 px;
  - menos recheo en tarxetas, listas, táboas, cabeceiras, barra de pestanas (56 px) e menú lateral (228 px).
  - Os botóns seguen por riba do mínimo de WCAG 2.2 AA (24 × 24 px).
- **«Texto grande»** non pasa por esa capa: escala ao 125 % e recupera as alturas cómodas (botóns de ~52 px).
- **A tableta da monitora** queda fóra (16 px e botóns grandes).
- **Fallo previo atopado ao facer as capturas.** Na app sen marco, o shell medía `100dvh` e a barra de demo empuxaba a barra de pestanas fóra da pantalla. Agora o `body` mide 100dvh e o shell ocupa o que queda, tamén en pantallas estreitas cando a cookie do marco está activa.
- Capturas antes e despois en móbil, tableta e escritorio: `docs/capturas/v3/densidade/`.

## v3 · 6 — Tableta da monitora (patrón AFS +50)
- **Referencia escollida:** `D:\AFS +50\src\modules\asistencia\kiosko\` (28/09, a máis recente) e os seus requisitos. Os HTML de `referencia/` (`asistencia_rpe_claro_v3.html` e `af50_asistencia_rpe_cloud.html`, do 22/09) son prototipos anteriores. Lín a carpeta só para coller a lóxica e o estilo; non copiei código nin datos.
- **Fluxo:**
  - Modo **Entrada / Saída** arriba.
  - Abecedario A–Z con Ñ e contador por letra, e buscador global (desde 2 letras, sen acentos).
  - Letra → nomes ordenados por apelido, con filtro se hai máis de 6 e icona de fotos.
  - Entrada: rexistra, amosa unha confirmación breve e volve en 1,5 s.
  - Saída: escala RPE da persoa (caras OMNI na infancia, etiquetas Borg CR-10 en adultos), cores OKLCH de verde a vermello, «¡Grazas, Nome!» e volta soa aos 3 s, con barra de progreso.
  - Cabeceira: entraron X de N, esforzos rexistrados, «Faltan N» (despregable) e estado de sincronización.
- **Inicial do primeiro apelido** (`apps/activities/names.py`): ignóranse as partículas (de, del, da, do, dos, das, la, las, los, van, von, mc, mac, y, e), normalízanse os acentos e a Ñ é letra propia.
- **Minimización.** Os **apelidos son opcionais** (persoas adultas e menores). Engadínos porque, nun grupo de 40, a monitora non pode atopar a ninguén só polo nome. Sen apelidos úsase a inicial do nome.
- **Regras:**
  - Un toque de «saída» sen entrada previa conta como presente.
  - Se se repite, vale o último RPE.
  - Os menores sen consentimento de esforzo rexistran a saída sen RPE.
- **Sen conexión.** Cada toque vai a unha cola en `localStorage` por sesión e envíase en lote a `…/rexistro/api/` (idempotente) ao volver a rede e cada 15 s. Ao abrir, os toques pendentes reaplícanse.
- A lista rápida anterior queda como alternativa sen JavaScript.
- **Demo:** grupo «Ximnasia activa · Grupo grande (40)» con 40 persoas ficticias (nomes e apelidos galegos combinados ao chou, con partículas, acentos e Ñ) e sesión todos os días.

## v3 · 4 — Portada da demo e lema
- **Dous pasos.**
  1. Escoller concello: Vilardeiras (rural pequeno, sen conserxe, con escolas) ou Pontedouro (mediano, pechaduras conectadas, máis volume), cunha frase que explica a diferenza. Ou entrar como a deputación, que ve os dous.
  2. «Quen es en X?»: cada tarxeta di **que verá** (app da veciñanza, panel do concello, app do operario, tableta da monitora…), **onde entra**, e leva unha miniatura real da súa pantalla de inicio (`static/img/demo/*.webp`).
- O paso vai na URL (`?concello=`): funciona sen JavaScript e pódese ligar.
- **Pontedouro** ten agora perfís propios ficticios (Rosa, veciña; Tino, mantemento) e unha reserva próxima para Rosa. A función de reservas da seed usa o concello da instalación.
- **Barra de demo:** amosa sempre o concello e o perfil activos («Vilardeiras · Brais (operario de mantemento)») e un botón «Cambiar» que volve ao paso 2 dese concello.
- **Lema:** «Reservar é o fácil…» retirado da portada, o README, o guión, o vídeo, a meta descrición, o `publiccode.yml` e o `CLAUDE.md`. Substitúeo «Eira · Software libre para a xestión deportiva municipal» e o subtítulo «Reservas, acceso ás instalacións, mantemento e actividades deportivas do concello, nunha soa plataforma.»

## v3 · 8 — Navegación e deseño
- **Sticky footer:** `body` con `min-height: 100dvh`, e `.shell-main` como columna flex co pé en `margin-top: auto`. Comprobado en `/preferencias/` e `/acceso/codigo/`: antes o pé remataba nos px 543 e 424 dunha xanela de 900; agora remata no 900.
- **Menú lateral:** un test percorre as 16 entradas do menú do concello e esixe `aria-current="page"` na súa páxina. Só fallaba o Observatorio (a vista non pasaba `sub`).
- **«Devolto»:** causa e corrección en `docs/PROGRESS.md` (v3).

## v3 · 3 — Consellos de saúde breves co tempo real
- **Antes:** ata 8 consellos longos por reserva (`docs/capturas/v2/saude-reserva.png`), sen sensación térmica, humidade nin vento. Ademais, a tarxeta da próxima reserva non os amosaba.
- **Agora:** de 2 a 4 consellos dunha liña e un único «Ver máis» co detalle e as fontes. Van na reserva, na tarxeta da próxima reserva da app e na páxina de Saúde.
  - Usan a previsión da instalación para o día e a hora: temperatura, sensación, humidade, UV, vento e chuvia.
  - A sensación térmica calcúlase no servidor (`Forecast.feels_like_c`); o resto do cálculo, no dispositivo.
- **Primeira hora.** Para sesións temperás non se di «bebe ás 5:00»: aplícase a variante de 2 h do ACSM.
- **MeteoSIX** queda listo para produción (`EIRA_ADAPTERS["weather"]` e `EIRA_METEOSIX_API_KEY`). O seu parser está probado cunha resposta de mostra, non coa API real.

## v3 · 7 — Axenda en calendario
- **Vistas:** «Lista» (a de antes, por día), «Semana» e «Mes» (`?vista=`).
  - Filtro de instalacións con checkboxes (`?i=`); sen marcar ningunha, son todas.
  - Exportación `.ics` do rango e o filtro activos, sen datos persoais (instalación, estado e referencia).
- **Semana:** táboa con columnas por día e filas por hora (da primeira á última con eventos), con cabeceiras `th` de fila e columna.
  - Fichas con cor e texto oculto de estado: pagada, reservada, pendente de pago, pechada (peches) e actividade municipal (sesións das escolas, calculadas cos días do grupo).
  - Cada ficha enlaza á reserva, aos peches ou á ficha do grupo.
  - Nas instalacións compartidas, as reservas da mesma hora e estado van nunha ficha con contador que leva á lista dese día: a semana pasou de 3.222 px a 1.872 px.
- **Mes:** grella luns–domingo con contadores por estado (texto oculto e `title`); cada día abre a súa semana.
- As canceladas, rexeitadas e caducadas non ocupan a axenda.
- **Teclado:** todas as fichas e días son ligazóns. A alternativa en lista segue dispoñible.

## v3 · Apelidos como dato da inscrición (minimización)
- **Antes:** os apelidos eran un campo novo na conta, nos menores e no formulario da monitora para persoas que viñan a probar.
- **Agora:** `Enrollment.surnames`, un dato da **inscrición** que achega o concello (padrón ou folla de inscrición).
  - O concello edítao na ficha do grupo e ao validar unha persoa apuntada.
  - A monitora non os enche: só anota o nome de quen vén a probar.
  - A migración copia os apelidos existentes ás inscricións e despois borra os campos de `User`, `Dependent` e `PendingParticipant`.
- **Na tableta**, só nome e primeiro apelido, coas partículas («Fina do Campo»).
  - O resto dos apelidos non sae do servidor: úsanse alí para calcular a inicial e a orde, e ao navegador non chega nin a clave de orde. Hai un test que comproba que o segundo apelido non está no HTML.
  - O nome completo só se ve na administración do concello e na exportación persoal da propia persoa.
- **Por que:** a monitora necesita distinguir persoas nun grupo de 40, e para iso abondan o nome e o primeiro apelido. O nome completo xa o ten o concello pola inscrición, así que non se crea outra copia nas contas.

## v3 · Deputación: agregados por defecto e acceso de soporte
- Por defecto, a deputación só ve vistas sen datos persoais (`@aggregate_view`): indicadores, comparativa da rede, instalacións, peches e plans de mantemento. A súa ligazón «Consultar» leva aos indicadores.
- **Datos persoais:** só con **acceso de soporte** (`SupportAccess`).
  - Autorízao o concello en «Persoal e códigos», con motivo; a deputación non se pode autorizar a si mesma.
  - Caduca ás 24 h e pódese revogar antes.
  - Cada páxina vista rexístrase en AuditLog (`support.view`, coa ruta), e o concello ve as últimas consultas e o historial.
  - No primeiro uso, o persoal administrador do concello recibe un aviso (na app e por correo).
  - A deputación pode **solicitalo** desde a páxina 403, o que avisa ao concello pero non dá acceso.
  - Mesmo con acceso, todo é só lectura. A exportación íntegra tamén precisa este acceso.
- Tests en `apps/tenants/tests/test_support_access.py`: 403 → autorización → 200 con rexistro e aviso → 403 ao caducar; revogación; acceso por concello; solicitude; exportación.

## v4 · Cero scroll horizontal
- **Test:** `tests/e2e/test_no_hscroll.py` percorre as pantallas de veciñanza, operario e tableta a 360 e 390 px, con texto normal e grande, e dentro do marco de teléfono do escritorio. Falla se:
  - a páxina ou o panel teñen `scrollWidth > clientWidth`;
  - algún elemento sae do seu panel;
  - algún bloque con texto desborda a súa propia caixa (así se detectou o importe cortado e os díxitos do código).
- **Fallos reproducidos e corrixidos:**
  - Historial de reservas: en móbil é unha **lista de tarxetas** (data · instalación · estado · importe); a táboa queda para escritorio (container query de 640 px).
  - `.kv` (confirmación, detalle, privacidade): columnas `fit-content(45%) minmax(0,1fr)`, e as insignias dentro poden partir.
  - Tarxetas de instalación: a columna da grella era `auto` e as insignias longas («Código temporal sen conexión») ensanchábana.
  - Tableta estreita: os botóns Entrada/Saída repártense o ancho e a grella de letras baixa a 60 px.
- **Código de acceso:** tamaño fluído `clamp(1.9rem, 1.2rem + 5cqi, 3.6rem)` e sempre en **dous grupos de 3** («842 261»). Se non caben nunha liña, o segundo grupo baixa.
  - Os díxitos visibles van con `aria-hidden`, e o lector le un texto oculto díxito a díxito («Código de acceso: 8 4 2 2 6 1»).
  - Non usamos `aria-label` nun `<p>`: axe considérao un atributo prohibido.

## v4 · Tableta: estado da sesión, saída e estatísticas
- **Por que saía «Pechada» (Cerrada) unha sesión de hoxe:**
  - O estado era só «ten `closed_at`?».
  - `record_rpe` (o formulario «Esforzo», ao que leva «Lista rápida») poñía `closed_at` ao gardar, aínda que a sesión non empezara ou estivese en curso. Por iso, despois de probar o fluxo, a sesión do día quedaba «Pechada».
  - Ademais, a seed pechaba as sesións pasadas ás 00:49 dese mesmo día, antes de empezar.
- **Agora o estado depende da hora**, cunha marxe de 15 min: «Por empezar» → «Aberta» → «Rematada» (sen pechar) → «Pechada».
  - Gardar o esforzo antes do final non pecha a sesión.
  - A seed pecha as sesións 10 min despois de rematar.
  - Tests paramétricos de estado e de «gardar esforzo antes do final non pecha».
- **Saída:** tocar o nome abre directamente a escala de esforzo; non hai pantallas extra. Se esa persoa non tocara «Entrada», a asistencia márcase soa (`Attendance.auto_in`) e a monitora ve un aviso discreto:
  - unha liña gris na pantalla de grazas;
  - un chip co número de «marcadas na saída»;
  - «(marcada na saída)» na lista rápida.
- **Estatísticas da monitora** (`/monitor/estatisticas/`): só os grupos onde ela é a monitora (tampouco a administración ve alí os doutros), últimas 8 semanas.
  - Asistencia por sesión e media do grupo.
  - Persoas con 3+ ausencias seguidas, contadas sobre as sesións con lista pasada e só con nome + primeiro apelido.
  - Esforzo medio por sesión, en escala fixa 0–10.
  - Carga semanal sRPE: media por persoa da suma de RPE × minutos na semana (Foster).
  - Probas físicas agregadas: último valor de cada persoa, con n, media, mínimo e máximo. Sen baremos.
  - Cada gráfica ten a súa táboa (`<details>`).

## v4 · Gráficas de barras con escala honesta
- **Antes:** todas as barras escalaban ao máximo da serie. 23 % enchía a barra e 12 % quedaba na metade; a satisfacción 84 e 85 /100 enchía as dúas.
- **Agora** `hbar(..., scale="percent")` vai de 0 a 100 (ocupación, non presentadas, asistencia, % OMS); `maximum=100` para a satisfacción e `maximum=10` para o esforzo.
  - Os valores absolutos (reservas por 1.000 hab., ingresos, carga) seguen relativos ao máximo, pero o gráfico **dío visiblemente**: «Barras relativas ao valor máis alto (606,5)».
  - As de escala fixa din «Escala de 0 a 100 %».
- **Variacións:** un único formato, «▼ −42» / «▲ +37», con menos tipográfico (U+2212) e decimais do idioma (filtro `signed`). Agora tamén aparecen nas tarxetas de resumo da deputación (reservas e ocupación).
- Tests de ancho en `apps/analytics/tests/test_hbar.py`; capturas antes/despois en `docs/capturas/v4/graficas-*`.

## v4 · Ferramentas da demo (correo, Telegram, pechadura)
- **Cabeceira común «Ferramentas da demo»**, coa mesma estética ca barra de demo (granito e etiqueta en millo). Inclúe:
  - o concello e o perfil activos («Vilardeiras · Uxía (veciña)»);
  - as ligazóns ás ferramentas.
- **«← Volver á demo»** leva á última páxina vista co perfil activo. `DemoFrameMiddleware` garda na sesión a última páxina HTML (GET 200, fóra de `/dev/`, `/static/`…) e, se non hai, a portada do perfil.
- **Sen sesión** a cabeceira ofrece «Escoller perfil»; non hai ningún «Acceder». Hai un E2E que comproba as dúas cousas.
- Na barra de demo, «Concello · Persoa (perfil)» deixa de ser un `inline-flex` (con texto grande partía en tres anacos). Agora parte coma texto.

## v4 · Avisos do concello
- **Modelo:**
  - `Notice`: categoría, público, franxa, canles, data de envío programada e cancelación das reservas.
  - `NoticePreference`: consentimento por concello e matriz categoría × canle.
  - `TelegramLink`: código dun só uso.
  - `Notification` gaña `notice` e `category` para poder filtrar.
  - `Municipality.telegram_channel`.
- **Base xurídica por categoría** (`CATEGORY_BASIS`, documentada en `docs/rxpd/avisos.md`):
  - Peches e alertas son de **servizo** (6.1.e/6.1.b): chegan sempre á app de quen lle afectan.
  - Horarios, actividades, festas e novidades son **informativos** e precisan consentimento (6.1.a). **Sen consentimento non se envían por ningunha canle**, pero pódense consultar no «Taboleiro do concello» da pantalla Avisos (consultar non é un envío).
- **Público:** toda a veciñanza, reservas nunha instalación, reservas nas descubertas, inscritas nunha actividade, ou reservas nunha parroquia.
  - As reservas contan na franxa «desde–ata» (por defecto, os próximos 30 días).
  - Non se usan datos doutras fontes.
- **Cancelación:** crea o peche (`Closure`) de cada instalación afectada e reutiliza `apply_closure`: devolución íntegra e o aviso de cancelación de sempre.
- **Redacción:** formulario con «Vista previa» sen JavaScript. Mostra:
  - a estimación de persoas por canle e de reservas que se cancelarían;
  - o aviso tal como se ve na app, na notificación push (truncada a 120 caracteres), no correo (asunto e pé coas preferencias) e en Telegram (burbulla).
  - Só a administración do concello pode enviar; a deputación ve, pero non envía.
- **Programación:** sen Celery. A orde `send_notices` envía os que xa tocan e aplica a conservación (avisos 12 meses, códigos 1 día); o despregamento chámaa por cron ou un temporizador de systemd. O envío é idempotente.
- **Telegram:**
  - Canle pública por concello. Na demo, `@eira_demo_vilardeiras` e `@eira_demo_pontedouro`: nomes ficticios co prefixo `eira_demo_` para non pisar canles reais.
  - Bot persoal con vinculación por ligazón `t.me/<bot>?start=<código>` ou `/start <código>`: un só uso, 30 min. `/stop` desvincula.
  - `BotApiTelegramAdapter` real (`sendMessage` por HTTPS). O token **só** se le de `EIRA_TELEGRAM_TOKEN` no contorno: non está no repositorio, na documentación nin na base de datos.
  - Webhook `/telegram/webhook/<EIRA_TELEGRAM_WEBHOOK_SECRET>/`, que dá 404 se o segredo non está configurado.
  - Na demo, o simulador `/dev/telegram/` fai de cliente: escribir ao bot pasa polo mesmo código ca o webhook.
- **App:**
  - Pantalla Avisos con chips de categoría, «Para ti» e o taboleiro, e ligazón á canle pública.
  - Preferencias: interruptor de consentimento e, por cada categoría, chips de canle (unha táboa de 5 columnas non collía en 360 px).
  - Vinculación de Telegram.
- **Correo da demo como bandexa real:** lista (destinatario, data, asunto e extracto) e vista da mensaxe (De, Para, Data). En móbil, lista ou mensaxe. Telegram sae de «Outras canles» e pasa ao seu simulador.
- **Seed:** 18 avisos enviados (15 en Vilardeiras e 3 en Pontedouro) e un programado («Horario de Nadal», dentro de 5 días).
  - Consentimento: Uxía, Manuel, Rosa e a metade da veciñanza. Uxía ten o bot vinculado.
  - A alerta amarela por vento crea reservas pagadas nas pistas exteriores e cancélaas con devolución.
  - Correos e mensaxes de «Reserva confirmada» das reservas próximas das persoas da demo.
  - As datas axústanse ao día de cada aviso. A bandexa de correo e Telegram nunca quedan baleiros despois de rexenerar.

## v4 · Busca compacta de instalacións
- **Unha liña:** campo de busca (con lupa), «Buscar» e un botón «Filtros» co número de filtros activos (a busca non conta, porque xa se ve no campo).
- **Filtros nun `<details>` despregable**, sen JS (a CSP non o precisa): tipo, parroquia e características como chips de casilla.
  - Debaixo, o reconto e os filtros activos como chips con «×» para quitar cada un.
  - Os resultados vense ao momento, sen a tarxeta grande de filtros.
- «Lista / Mapa» é un control segmentado pequeno xunto ao título. A chamada «Solicita a app» (persoas sen sesión) baixa ao final.
- **Por que `<details>` e non unha folla inferior:** funciona con teclado e lector sen código propio e non tapa os resultados. Nun móbil de 360 px a busca e «Filtros» collen nunha liña.

## v4 · Padrón semiautomático
- **Alta en liña:** nome, apelidos, DNI/NIE (con letra de control), data de nacemento e enderezo opcional.
  - O contraste usa **só DNI/NIE + data de nacemento**; o nome nunca. A interface `PadronAdapter.check(municipality, *, id_number, birth_date)` nin sequera o recibe, e un test compróbao.
- **Padrón:** o concello sobe un CSV (Xestión › Altas › Padrón; modelo descargable coas liñas de exemplo comentadas).
  - Normalízase: maiúsculas, sen espazos, puntos nin guións, e recheo con ceros nos DNI curtos. As datas acéptanse como DD/MM/AAAA, AAAA-MM-DD, DD-MM-AAAA, DD.MM.AAAA ou DD/MM/AA. O separador, `;`, `,` ou tabulador.
  - De cada liña gárdase só un `HMAC-SHA256(EIRA_PADRON_SECRET, «concello|DNI|AAAA-MM-DD»)`. Se o segredo non está definido, derívase de `SECRET_KEY`.
  - O ficheiro procésase en memoria e non se garda. Cada carga substitúe a anterior e queda en `PadronImport` (data, válidas, rexeitadas, quen) e en AuditLog.
- **Coincidencia exacta:** alta automática e correo coa ligazón e o código.
- **Sen coincidencia:** vai á cola de «Altas da app» co motivo («Non figura no padrón cargado», «Aínda non hai padrón cargado», «DNI/NIE ou data non válidos»). O persoal aproba ou rexeita cun clic.
- **Minimización:** ao resolver (ao momento se coincide), bórranse o DNI/NIE, a data e o enderezo. A alta no mostrador non pide DNI, porque o persoal compróbao en persoa.
- **Adaptador:** `CsvPadronAdapter` por defecto; `SvdrPadronAdapter` é o esqueleto para unha API futura, coa mesma interface. `FakePadronAdapter` queda como alias para configuracións antigas.
- **Demo:** padrón ficticio de 400 persoas por concello, xerado con números inventados e letra correcta. Inclúe a persoa do guión (DNI de exemplo `12345678Z`, nada o 14/05/1990), que recibe a alta automática.
  - Hai dúas solicitudes pendentes co motivo.
  - O padrón usa un xerador aleatorio propio para non mover o resto da seed.
- RAT (actividade 10) e capa informativa do formulario actualizadas (art. 6.1.e).
- Tests en `apps/accounts/tests/test_padron.py`: coincidencia exacta, sen coincidencia, minúsculas e espazos, formatos de data, recarga, que o CSV non se garda, que o nome non se usa, segredo e concello no HMAC, e borrado ao resolver.

## v4 · Apelidos ao inscribir menores
- Ao inscribir un/unha menor nunha escola, os **apelidos son obrigatorios** e gárdanse como dato da inscrición (`Enrollment.surnames`, decisión v3). Para a propia persoa adulta son opcionais.
- O formulario explica por que: «como no padrón; a monitora só verá o primeiro apelido».

## v4 · Configuración do concello en seccións
- Seis tarxetas nunha grella de dúas columnas: Identidade, Contacto (coa canle pública de Telegram), Regras de reserva, Padrón (coa ligazón á carga do CSV), Mapa e Textos legais (a ancho completo). Dentro de cada tarxeta, os campos van en grella.
- Os módulos van na columna lateral, que queda fixa ao desprazar e ten o seu propio «Gardar». Arriba hai chips para saltar a cada sección.
- O texto de axuda dos códigos postais xa non di que serven para o padrón (agora é o CSV).

## v4 · Pase de espazado
- **Familia:** cada consentimento é unha fila compacta (texto, data e interruptor `role="switch"` con `aria-checked`) no canto dun botón «Outorgar/Retirar» en liña propia. Úsase o mesmo formulario POST de sempre, así que non fai falta JS.
- **«Engadir menor»:** nome e ano en dúas columnas e consentimentos agrupados nun `fieldset`. Explica que os apelidos se piden ao inscribir nunha escola.
- Capturas antes/despois en `docs/capturas/v4/espazado-*`.

## v4.1 · Avisos de actividade: servizo fronte a informativos
- Nova categoría **«Cambios nas túas actividades»** (`activity_change`), de **servizo** (art. 6.1.b): suspensións e cambios de horario ou de sala dunha actividade na que a persoa xa está inscrita. Non precisa consentimento e chega sempre á app.
- **«Actividades e inscricións»** segue sendo **informativa** (consentimento): novas inscricións, prazas libres, actividades novas. Aínda que vaia ás mesmas persoas, é promoción.
- Garantías: o formulario só deixa enviar cambios ás persoas inscritas nesa actividade. Se un aviso desta categoría tivese outro público, `Notice.basis` trátao como informativo.
- Na seed, «cambio de sala o xoves» pasa a esta categoría e engádese «Escola de fútbol: adestramento do venres suspendido». Substitúe a decisión v4 de tratar todos os avisos de actividade como informativos.

## v4.1 · Segredo do padrón obrigatorio en produción e avisos programados en Docker
- `EIRA_PADRON_SECRET` é **obrigatorio en produción**. Se falta, `settings.py` detén o arranque cunha mensaxe que explica que é, como xeralo e que cambialo obriga a volver cargar o padrón.
  - Non se deriva de `SECRET_KEY`, que se pode rotar por outros motivos e invalidaría o padrón sen avisar.
  - Defino «produción» como `EIRA_DEBUG=0` **e** `EIRA_DEMO_TOOLS=0`. Os dous `docker-compose` da demo corren con `DEBUG=0`, pero teñen datos ficticios e as ferramentas de demo activas: neles e en desenvolvemento mantense a derivación. Se se pedise só con `DEBUG=0`, a demo pública deixaría de arrancar.
  - Hai un test que arranca Django nun subproceso nos tres casos.
- **Avisos programados:** novo servizo `notices` en `docker-compose.yml` e `deploy/demo/docker-compose.yml`. É un bucle sen cron (`tools/send-notices-loop.sh`) que agarda ás migracións e executa `send_notices` cada 5 min (`EIRA_NOTICES_INTERVAL`).
  - En produción sen Docker, liña de cron en `docs/despregamento.md`.

## v4.1 · Portada sen estilos: caché do service worker
- **Causa:** a versión do service worker era fixa (`eira-v1`). Os estáticos servíanse primeiro da caché e cun URL sen versión (`/static/css/eira.css`), e `caches.match()` buscaba en todas as cachés. Despois de cambiar o CSS, o navegador seguía usando o vello ata forzar a recarga.
  - Comprobouse que non era o CSS: nun navegador limpo a portada vese ben.
- **Corrección:**
  - **Produción:** `CompressedManifestStaticFilesStorage` (nomes con hash).
  - **Desenvolvemento:** `{% asset %}` engade `?v=<hash do contido>`, que se recalcula ao cambiar o ficheiro.
  - **Service worker:** a versión deriva destes hashes; no `activate` bórranse todas as cachés doutras versións. Só se busca nas cachés propias; o CSS (e, en desenvolvemento, todos os estáticos) vai á rede primeiro; o HTML sempre á rede primeiro.
  - `sw.js` sérvese con `Cache-Control: no-cache` e rexístrase con `updateViaCache: "none"`.
- **Efecto secundario descuberto:** co manifesto, `collectstatic` fallaba polo `sourceMappingURL` de Leaflet, que apuntaba a un `.map` que non distribuímos. Quitouse esa liña do ficheiro vendorizado.
  - Un test fai `collectstatic` co manifesto e debuxa as páxinas principais.
  - `{% static 'img/demo/' %}` (un directorio) substituíuse polo filtro `static_file`.
- **E2E (`tests/e2e/test_service_worker.py`):**
  - Un service worker «anterior» coa caché envelenada actualízase, borra as cachés vellas e a portada ten estilo (`display: grid`, sen viñetas).
  - Un CSS vello na caché do service worker activo non se serve. Este test falla co `sw.js` anterior.

## v4.1 · Ilustración propia
- Seis ilustracións xeradas con IA para Eira (CC BY-SA 4.0, sen obras de terceiros), con nomes segundo o contido:
  - `cabecera-eira` e `cabecera-eira-noite` (modo escuro);
  - `eira-icono-baleiro` (1:1);
  - `baleiro-reservas`, `baleiro-avisos` e `baleiro-mantemento` (4:3).
- Os orixinais PNG (1,9–2,4 MB) quedan en `assets-originais/` e non se serven. `tools/build_illustrations.py` xera AVIF e WebP sen metadatos, de 5 a 63 KB: cabeceiras en 480, 960 e 1600 px e estados baleiros en 2 anchos.
- **Cabeceira da app:** `<picture>` `eager` con `fetchpriority=high`. É a única imaxe `eager` da pantalla (comprobado nun E2E).
  - O saúdo vai superposto na zona despexada da esquerda, cun degradado de papel ao 86–94 % baixo o texto (contraste AA de granito).
  - Co modo escuro do sistema úsase a versión nocturna, con texto branco sobre degradado escuro.
  - **Texto grande:** a ilustración pasa debaixo do saúdo, sen superposición.
  - **Alto contraste:** sen ilustración.
  - Non hai animacións.
- **Portada da demo:** a mesma ilustración, `lazy`, como fondo ao 20 % detrás do granito.
- **Estados baleiros:** reservas (inicio e «As miñas reservas»), avisos, «Todo feito por hoxe» do operario e busca de instalacións sen resultados (icona 1:1).
- Créditos en `CREDITS.md`, `assets-originais/CREDITS.md` e a páxina `/creditos/`.

## v4.1 · Axustes visuais rápidos (24/10)
- **Configuración do concello: grella de dúas columnas con seccións emparelladas, non masonry.**
  - Con `columns` de CSS a orde visual vai por columnas (abaixo e despois á dereita). Quen le ou navega co teclado salta da última sección da columna 1 á primeira da 2, e as tarxetas pódense partir entre columnas.
  - Por iso reordénanse as seccións para que cada fila teña dúas de altura parecida: Identidade + Padrón e Contacto + Regras de reserva. Mapa e Textos legais ocupan as dúas columnas.
  - As filas estíranse (`align-items: stretch`), así que non quedan ocos. A orde do DOM, a das pestanas (chips) e a do foco son a mesma ca a visual.
  - **Columna de módulos:** 280 px fixos e `sticky` desde 1200 px de xanela. Por debaixo vai debaixo do formulario e sen o seu «Gardar», que sería duplicado. O `fieldset` ten `min-width: 0`: polo `min-content` por defecto do navegador era o que podía empurrar a columna fóra.
  - **Campos que se cortaban:** Contacto vai nunha soa columna dentro da tarxeta, os campos ocupan o 100 % e o contacto do DPD é un `textarea` de 2 liñas. Só cambia o widget, sen migración.
  - **Padrón:** a nota «as altas automáticas usan o padrón cargado en CSV» xa está na axuda do campo. Debaixo só queda a ligazón «Cargar o padrón».
- **Tema escuro (botón «Día / Noite» da demo):**
  - **Onde se garda:** `request.session["eira_theme"]` («light» | «dark»). O servidor pon `data-theme` no `<html>`; sen valor, segue a preferencia do sistema.
  - **Unha soa clase:** o CSS só mira `.theme-dark`. Ponse un script síncrono e moi pequeno no `<head>` (`static/js/theme.js`, sen JS en liña polo CSP), que resolve «escolla da sesión ou sistema» antes de pintar e escoita os cambios do sistema. Así non hai que duplicar as regras nun `@media (prefers-color-scheme)`. Sen JS, o tema escollido segue funcionando porque o servidor tamén pon a clase.
  - **Alcance:** só a app da veciñanza, a do operario e a tableta (`body.themable`). O escritorio do concello segue claro: non está auditado en escuro e non se pediu.
  - **Paleta:** os mesmos tokens con valores de noite. O fondo (papel, branco) pasa a escuro, o texto (granito) a claro e as cores de acción (musgo, millo, arxila) aclaran e levan texto escuro enriba.
    - As cores fixas que había no CSS (insignias, avisos, fondos claros de estado e texto branco sobre musgo ou granito) corríxense nun bloque final.
    - O código de acceso e a tarxeta da próxima reserva seguen escuros, cun bordo.
  - **Verificación:** axe sen violacións en 31 pantallas en escuro (`tests/e2e/test_dark_theme.py`).
  - **O botón:** é un formulario POST a `/dev/tema/`, que sen JS recarga a páxina. Con JS cambia o tema ao momento, anúnciao por `aria-live` e gárdao con `fetch` (204). Leva `aria-pressed` (true = noite).
  - Vai na barra de demo e enriba do marco do dispositivo. O cambio de perfil da demo conserva o tema.
- **Ilustración día/noite con crossfade:** cando hai versión nocturna van as dúas `<picture>` superpostas. Só a de día é `eager`; a de noite é `lazy`.
  - O tema cambia a opacidade cunha transición de 0,6 s, que se anula con `prefers-reduced-motion` ou coa preferencia «movemento reducido».
  - Xa non se usa `<source media="(prefers-color-scheme: dark)">`, que non podería obedecer ao botón.
- **Perfil «Brais · veciño novo» (`brais.novo@demo.eira.example`):**
  - Mantense o nome pedido aínda que xa hai un Brais operario. O rol que se ve na barra e na portada («veciño novo» / «operario de mantemento») distíngueos.
  - A seed créao ao final, despois dos avisos masivos, para que non teña reservas, avisos nin inscricións.
- **Mantemento «todo ao día»:**
  - O operario ten un filtro «Hoxe» (atrasadas e de hoxe, por defecto) / «Mañá».
  - Na seed, Brais deixou feitas hoxe as ordes de mañá, así que «Mañá» mostra o estado baleiro. O xerador non as volve crear porque xa existen.
  - **Cambio:** antes a lista por defecto incluía mañá; agora mañá vai no seu filtro.
- **Catálogo de ilustracións** en `/dev/ilustracions/`, só con `EIRA_DEMO_TOOLS`. Cada ilustración ten un botón «Ir á pantalla» que entra co perfil axeitado: `entrar-como` acepta `next` (só local) e `tema`.

## v4.1 · Vídeo final do pitch (24/10)
- **Captura por CDP (`Page.startScreencast`) e montaxe con ffmpeg**, non o gravador de Playwright: este comprime en VP8 a ~1 Mbit/s e a 1080p o texto vese borroso. Os fotogramas JPEG (calidade 92) colócanse nunha grella de 1/30 s polas súas marcas de tempo para que a duración e os subtítulos non deriven.
- **1280×720 CSS con escala 1,5** (saída 1920×1080): a 1920 px CSS o marco do teléfono ocupaba un cuarto da pantalla e non se lía.
- Subtítulos **queimados** (lense en calquera reprodutor e en redes) e, ademais, `.vtt` e pista `mov_text` (gl) no MP4 para quen os queira desactivar ou traducir. A pausa de cada un depende do número de palabras (≥ 2,2 s, ~0,28 s/palabra).
- Datos rexenerados (`seed_demo`) ao comezo da gravación e **IA desactivada** (`EIRA_AI_ENABLED=0`). O aviso por vento usa como franxa a próxima reserva nunha instalación descuberta (de Uxía se hai), para que a vista previa chegue a alguén aínda que se grave de noite.
- Recorte fronte ao guión longo: fóra saúde, consellos da sesión, valoracións e observatorio, para quedar en ≈ 2 min.
- MP4, WebM e `.vtt` quedan en `docs/demo/` e ignorados polo git; van a unha release privada en borrador (ver `docs/demo/VIDEOS.md`).

## v5 · Versión definitiva (26/10)

Regra principal da tanda: **só se engade**. Cando algo novo choca co existente, gaña o existente e anótase aquí («Choque»).

### C · Participantes, formas de pagamento, aprobación e luz
- **Participantes:** número de persoas obrigatorio (o formulario xa vén con 1) e un máximo por instalación (`max_participants`, 12 por defecto). Os nomes son opcionais, un por liña, e só os ve o concello.
  - Os tests antigos que confirmaban sen o campo actualizáronse para envialo (agora é obrigatorio, como pide a especificación).
- **Formas de pagamento** (`PaymentMethod`): TPV, pagamento na oficina, gratuíta, bono e aprazado.
  - O concello escolle as admitidas (por defecto **só TPV**, como ata a v4) e cada instalación pode restrinxilas (baleiro = as do concello).
  - **Aprazado** desactivado por defecto: aínda que unha instalación o marque, non se ofrece se o concello non o activou.
  - **Oficina:** a franxa queda gardada `office_payment_hours` (48 h por defecto) ou ata o inicio, o que chegue antes. Se non se paga, caduca igual ca un pagamento co TPV sen completar (`expire_pending`).
  - **Gratuíta:** sen taxa e luz incluída.
  - **Bono:** cada reserva desconta un uso, **luz incluída** (o concello fixa o prezo do bono). Se se cancela a tempo, o uso devólvese; fóra de prazo, non (igual ca o importe). Cómprase co TPV do concello ou na oficina.
  - **Conciliación:** nova táboa «Por forma de pagamento» en Cobros (reservas, cobrado neto, pendente de cobro e suplemento de luz) e bonos vendidos. Os cobros de bonos van na táboa de cobros co seu concepto.
- **Aprobación do concello** (`booking_mode`: directa por defecto, ou con aprobación):
  - Primeiro págase (se é co TPV) e despois apróbase. Se o concello a rexeita, **devólvese o importe automaticamente** e a persoa recibe o motivo (obrigatorio).
  - Con pagamento na oficina, primeiro apróbase e despois empeza o prazo para pagar.
  - Unha reserva pendente de aprobación **garda a franxa** (se non, poderían aprobarse dúas para a mesma hora).
  - **Cambios:** nas instalacións con aprobación, o cambio de hora queda pendente (`requested_start`) e a reserva segue na hora vella ata que o concello o aprobe. A franxa nova compróbase ao pedilo e outra vez ao aprobalo (non se garda mentres tanto).
  - O persoal recibe un aviso na app e ve «Para aprobar» no panel do día.
- **Suplemento de iluminación** (`lighting_supplement_cents` por instalación):
  - Regra do concello: **solpor** (por defecto; amencer e solpor calculados coa fórmula da NOAA para as coordenadas da instalación, sen rede nin dependencias) ou **horario fixo** (`lighting_from`–`lighting_until`).
  - Aplícase se algunha parte da franxa cae fóra das horas de luz natural, ou se a persoa marca «Necesito luz».
  - Desglose «Pista 4,00 € + luz 1,50 €» antes de pagar (refréscase con HTMX ao cambiar o formulario), na reserva, no recibo HTML e no PDF. A grella mostra que franxas levan luz.
  - **Nivel 3:** se a instalación ten suplemento, as luces só se acenden se a reserva o leva (pagado ou incluído no bono ou na gratuíta). **Choque:** ata agora acendíanse sempre que a instalación tiña luz; iso mantense nas instalacións sen suplemento configurado.
  - Ao cambiar de hora non se recalcula o suplemento; se a franxa nova precisa luz, acéndese igual (asúmeo o concello).
- **Escolas deportivas:** sen cambios, seguen xestionándose desde o concello.

### D · Estado ao entrar
- Despois da entrada (QR, código, apertura remota ou chave), a reserva ofrece «Como está todo ao entrar?»: «Todo ben» / «Hai un problema», texto e foto opcional (sen EXIF, coma as incidencias).
- Se hai un problema créase unha incidencia con orixe «Estado ao entrar» e `prior_to_booking` = esta reserva: **queda rexistrado que xa estaba antes**. O texto inclúe a reserva anterior nesa instalación, se a hai.
- A ficha da reserva (veciña, operario/a e concello) mostra o estado ao entrar e ao saír xuntos. O persoal de mantemento pode ver a ficha da reserva só en consulta.

### A · Concellos próximos da mesma rede
- Unha persoa reserva noutro concello da súa rede (mesma deputación ou mancomunidade) coa mesma conta. Na app: selector de concello en «Reservar» e páxina «Concellos próximos». Mentres reserva noutro concello, as lapelas da app seguen sendo as do seu concello e un aviso lembra a tarifa.
- **Tarifa:** a de persoas non empadroadas do concello de destino (xa era a que se aplicaba a quen non está empadroado alí). O prezo vese antes de pagar e o cobro créase no concello de destino: o TPV simulado mostra o comercio dese concello (`FakePayment.merchant`).
- **Opción de cada concello** (`network_open`, cupo `network_max_active` e antelación `network_advance_days`).
  - **Choque:** ata a v4 calquera persoa con conta podía reservar en calquera concello á tarifa de non empadroada. Para non quitalo, `network_open` vale **Si por defecto**. Se un concello o desmarca, só reservan as persoas con vínculo con el (conta ou empadroamento); a reserva en nome doutra persoa desde o mostrador non se ve afectada.
  - O cupo interprétase como **reservas activas á vez por persoa doutro concello** (2 por defecto) e a antelación como días máximos (baleiro = a mesma ca para a veciñanza; nunca máis).
- **Concello de orixe:** só polos vínculos explícitos (empadroamento ou conta). Quen non ten ningún vínculo non é «da rede»: segue como ata agora.
- **RXPD:** o destino recibe o nome para mostrar (ou «Persoa de ‹concello›» se non o hai), o concello de orixe, data, hora, persoas e cobro. Non ve correo, teléfono, ano de nacemento, empadroamento, familia nin saúde. O de orixe non ve as reservas noutros concellos. Documentado en `docs/rxpd/matriz.md`.
- **Actividades e eventos próximos:** opcionais. A persoa activa cada concello en «Concellos próximos»; en «Avisos» aparecen os seus avisos públicos de actividades, festas e novidades e os grupos das escolas, filtrables por concello. Non se envía nada: é un taboleiro, coma o do propio concello, así que non precisa consentimento de comunicacións.

### B · Ficha de seguridade e cartel
- Material dispoñible (un por liña, a cantidade primeiro), protocolo de accidentes, DEA máis próximo e o 112 (ligazón `tel:112`) na ficha pública.
- **Última supervisión:** calculada, data de peche da última orde de mantemento pechada da instalación. Non se garda.
- **Cartel A4 en PDF etiquetado** xerado sen dependencias novas (`apps/facilities/poster.py`): árbore de estrutura (H1, H2, P, L/LI, Figure), `/Lang`, título visible, XMP, QR como figura con texto alternativo e decoración como artefacto. O QR leva ao rexistro de entrada (nivel 0) ou á reserva (resto).
  - **Non verificado** con PAC nin veraPDF (non hai rede nin licenzas); as fontes estándar non van incrustadas, o que impide declarar PDF/UA estrito.
- **Plantilla do concello:** o mesmo cartel co escudo (ou as iniciais na cor do concello) e os campos en branco.

### E · Axuda, seguridade e inclusión
- **Botón «?»** en todas as cabeceiras (app, operario, tableta e administración): `details`/`summary`, sen JS. Axuda da pantalla actual segundo o nome da URL, guía completa en `/axuda/` e contacto do concello.
- **«Incidencia ou seguridade»** (icona de escudo) sempre na cabeceira: avaría, aviso de risco (prioridade alta, aviso inmediato á administración e a mantemento tamén por correo, primeiro na lista) e chamada ao 112 destacada.
- **Linguaxe inclusiva:** guía en `docs/accesibilidade/linguaxe-inclusiva.md` e test que busca as formas a evitar no catálogo e nas plantillas.
- **Modo básico/avanzado** da administración por persoa (`User.desk_mode`, básico por defecto). Só cambia o menú; os permisos e as URL son os mesmos.

### F · Protección de datos explicada
- «Quen custodia os teus datos» (`/c/‹concello›/privacidade/datos/`, pública e na app): a columna «quen o recibe» lese de `docs/rxpd/matriz.md` en tempo de execución; para que, canto tempo e como borralo están en `apps/accounts/custody.py`. Un test falla se a matriz ten unha fila sen explicación.
- **Rexistro de brechas** só para administración do concello e o novo rol **DPD** (`dpo`, escritorio cun menú propio). A deputación non o ve nin co acceso de soporte (pode ser parte da brecha como encargada). Prazo de 72 h calculado e marcado; con risco hai que notificar ou explicar por que non. Comunicación modelo do art. 34 descargable.

### G · Índice de vida activa
- Ver `docs/indice-vida-activa.md`. Engádese ao observatorio, que non cambia. Sen cifra se hai menos de dous compoñentes de persoas con n ≥ 10. No panel do día gárdase 10 min en caché e na comparativa da deputación vai coa caché existente (5 min).

### H · Revisión de seguridade inicial
- Orde de traballo `kind="safety_review"` co checklist de 10 puntos. Ao pechala, a ficha mostra «Revisada o ‹data›» e conta como última supervisión. Se xa hai unha aberta, non se crea outra.

### v5 · Choques e correccións do peche
- **Choque (E, modo básico por defecto):** ocultar entradas do menú faría «menos visible» o existente. No modo básico non se quita ningunha: o día a día queda á vista e o resto vai en «Máis ferramentas» (un `details` pechado que se abre só se estás nunha desas pantallas). No avanzado todo vai aberto.
- **Dockerfile:** desde a v4.1 a imaxe non se construía (`collectstatic` sen `EIRA_PADRON_SECRET`). A construción usa agora un valor só para construír, como xa facía coa clave secreta; en execución segue sendo obrigatorio en produción.
- **Bonos e rexeneración da demo:** `Voucher.type` pasa de PROTECT a CASCADE para que borrar un concello (a demo rexenérase así) non falle.
- **Pitch:** o MP4 xa non leva pista de subtítulos activable; só os queimados (o `.vtt` queda aparte). Dous subtítulos acurtados para quedar en ≈ 2:14 co paso novo.
- **Versión conxelada:** etiqueta `v1.0-certame`. Desde aquí só correccións.

## v1.1 · Rexistro de limpeza (26/10)
Regra de sempre: só se engade; nos choques gaña o existente.

- **Rol `cleaning` («Persoal de limpeza»)** por concello, co campo opcional `Membership.company` (empresa contratada; baleiro = persoal propio). Perfil `cleaning` co mesmo deseño da app do operario (`/operario/`): lapela «Tarefas», marca «Limpeza» e só ordes `kind="cleaning"`. Unha orde de mantemento ábrese con 404 (como as doutro operario) e o resto de ferramentas dá 403 (matriz de roles en `test_roles.py`).
- **Plans co motor de mantemento preventivo:** `MaintenanceTask.kind` (mantemento/limpeza), `zone` e `times_per_day`; frecuencia nova «Varias veces ao día». Cada quenda é unha orde (`WorkOrder.slot`); a restrición única pasa de (tarefa, día) a (tarefa, día, quenda), compatible coas ordes existentes (slot 0).
- **Zonas** (`CleaningZone`: vestiarios, aseos, pista, bancadas, almacén, vaso, outra) con tempo máximo sen limpar e un token para o QR. O checklist da zona xúntase das súas tarefas (ou un por defecto segundo o tipo).
- **Modelos nas plantillas de instalación:** cada plantilla trae o seu modelo de zonas (`apps/maintenance/cleaning.TEMPLATES`) e créase un **plan de limpeza aparte**. **Choque:** o plan preventivo existente («Limpeza de vestiarios» diaria no pavillón, «Limpeza de follas» na pista) **non se toca**; dous tests que contaban «un só plan» agora escollen o de mantemento. Para instalacións xa creadas, botón «Aplicar modelo de limpeza» (idempotente). A demo non os aplica automaticamente: só no pavillón e no campo de Outeiro de Vilardeiras.
- **Horas máximas por defecto:** varias veces ao día → 16 h (de 19:30 a 8:30 van 13 h; con 8–12 h o aviso saltaría todas as mañás), diaria → 30 h, semanal → 8 días. Unha zona nova sen rexistros conta desde que se creou.
- **QR da zona** (`/c/‹concello›/operario/limpeza/‹token›/`): o persoal de limpeza, mantemento ou a administración ven o checklist e rexistran (quen, nome e empresa no momento, data e hora, tarefas, observacións, foto opcional sen EXIF). Ao rexistrar péchase a quenda pendente máis antiga da zona. Quen non é persoal ve só a última limpeza (sen nome) e o botón de avisar; a POST dálle 404.
- **Sen conexión:** mesma cola IndexedDB que o operario. A cola envía agora `_queued_at` (hora en que se gardou) e o servidor úsaa se non é futura nin de hai máis de 7 días. A lista de tarefas precarga as páxinas das zonas (unha a unha, despois de cargar) para que o service worker as garde e o QR abra sen cobertura. **Comprobado en E2E** co navegador sen rede.
- **Última limpeza** na ficha pública («hoxe 10:40», «onte 18:05») xunto á última supervisión. **Choque:** as ordes de limpeza pechadas **non contan** como «Última supervisión» (senón sería sempre «hoxe» e perdería significado).
- **Avisos de atraso:** `check_overdue` avisa (app, sen correo) á administración e ao persoal de limpeza unha vez por atraso; volve avisar só despois dunha limpeza nova. Execútase no bucle `send_notices`, ao abrir o panel do día e a páxina «Limpeza».
- **Enrutado por tipo:** incidencias de categoría «Limpeza» (tamén estado ao entrar co novo tic «é de limpeza», o tic «fai falta limpeza» do checklist de saída e as valoracións «Mal» con «Sucia») → orde de limpeza + aviso ao persoal de limpeza; a administración segue recibindo o seu aviso. As avarías avísanse agora tamén a mantemento (a orde segue creándoa o concello). «Mal» con «Sucia» e outra avaría: a incidencia vai pola avaría e créase ademais unha tarefa de limpeza.
  - **Choque:** sen persoal de limpeza no concello todo segue como antes (non se crean ordes automáticas e mantemento segue vendo as tarefas de limpeza). Con persoal de limpeza, mantemento deixa de ver as de limpeza sen asignar (si as que se lle asignen).
  - Ao asignar unha orde dunha incidencia a unha persoa de limpeza, a orde é de limpeza.
- **Exportación** do rexistro por instalación e período en CSV, ODS (o escritor propio) e PDF de varias páxinas (`paged_pdf`, sen dependencias, Helvetica sen incrustar; non é PDF accesible etiquetado). Máximo un ano por exportación.
- **Índice de vida activa:** feito como parte de «Mantemento ao día» (era doado): −10 se a instalación ten algunha zona atrasada. Ver `indice-vida-activa.md`.
- **Datos persoais do persoal:** ver `docs/rxpd/matriz.md` (v1.1). Non se garda localización.
- **Icona nova** «sparkle» no sprite (debuxo propio).

## v1.2 · Aportacións do equipo: uso diario, seguridade e rendemento (27/10)
Regra de sempre: **só se engade**; se algo novo choca co existente, gaña o existente e anótase aquí («Choque»).

### A · «Aviso» e «Alerta»
- **Onde:** a páxina «Incidencia ou seguridade» (`/c/‹concello›/seguridade/`) mostra primeiro dous botóns grandes e diferenciados por **forma** (cadrado coa chave para «Aviso», octógono co «!» para «Alerta»), **cor** (millo / vermello) e **texto**. Debaixo segue todo o de antes (112, «Avisar dun risco», «Avisar dun problema»), agora baixo o título «Aviso», máis «Comentario para o concello» (incidencia de categoría «Outra»).
- **Alerta** (`/seguridade/alerta/`): «Accidente deportivo» abre o protocolo paso a paso da instalación; «Emerxencia de seguridade» mostra o 112 en grande (`tel:112`). As dúas son formularios POST (funcionan sen JS) e **avisan ao momento**: á primeira persoa responsable de servizo (bloque B) por correo e app, e á administración do concello por app e correo.
- **Incidencia vinculada de prioridade nova «Máxima»** (`Incident.Priority.URGENT`, orixe «Alerta»), categoría Seguridade, para que mantemento revise se a instalación tivo que ver. Mantemento recibe o aviso tamén por correo.
- **Alertas sen sesión:** permítense (é unha emerxencia), cun límite de 3 por hora e orixe (IP) para evitar abusos. Superado o límite, segue a verse o 112.
- **Reserva en curso:** a pantalla da reserva mostra os dous botóns sen abrir o menú (versión compacta). **Tableta:** botón «Alerta» na lista de asistencia e no modo rexistro; a alerta leva a sesión e a instalación do grupo (orixe «Tableta da persoa monitora»).
- **Protocolo:** 5 pasos **fixos na súa función** (protexer; 112 con botón; DESA co dato do bloque C; aviso automático; rexistro) e **texto editable** por concello e por instalación (`AccidentProtocol`; sen instalación = plantilla do concello; sen ningún, a plantilla por defecto). **Choque:** o campo de texto libre da v5 «Protocolo en caso de accidente» **mantense** na ficha e móstrase tamén no protocolo como «Indicacións desta instalación».
- **Rexistro de accidentes** (`AccidentReport`): data e hora, instalación, tipo xeral (caída, golpe, lesión muscular, outro), gravidade percibida (leve / require atención / 112), se se chamou ao 112 e quen o comunica (o papel, non o nome). **Sen ningún campo de texto libre** (un test compróbao) para que non se poidan escribir diagnósticos. A gravidade «112» marca «chamouse ao 112». Só o ven a administración do concello e o DPD (o mesmo control ca o rexistro de brechas); a deputación non. Conservación configurable (por defecto **24 meses** despois de pechado); a purga vai en `booking_maintenance`.
- **Termos:** a v5 usaba «DEA» na ficha; o novo usa «DESA (desfibrilador)», o termo da proposta. Conviven: o dato antigo «DEA máis próximo» segue visible.

### B · Peche sen confirmar
- **Cando:** reservas **usadas** (con entrada rexistrada) en instalacións de **nivel 1, 2 ou 3** sen lista de peche, ata 12 h despois do fin. **Decisión:** o nivel 0 (pista aberta) non ten porta que pechar (e a v5 xa non marca alí «non presentada»); non se escala.
- **Fases** (tempos por concello; por defecto 10 + 10 + 10 min): 1.º recordatorio **só app/push** (`notify(..., email=False, telegram=False)`; parámetro novo `telegram`); 2.º app + canle activa (correo e/ou Telegram); 3.º **aviso á primeira persoa responsable de servizo** segundo orde e horario (`ResponsibleContact`; os horarios poden pasar da medianoite) e á administración.
- **A Policía Local non se avisa nunca de forma automática** (proporcionalidade e para evitar falsas alarmas). O aviso á persoa responsable leva unha ligazón á súa páxina (`/seguridade/peche/‹token›/`, sen conta) cun botón «Contactar coa Policía Local» (teléfono configurable). Primeiro rexístrase o contacto (`PoliceContact`) e despois aparece o `tel:`: así queda constancia de cada decisión. Na mesma páxina pódese marcar «Revisado».
- **Nivel 3:** método novo `door_state()` no adaptador de pechadura. O simulador garda o estado en `LockDevice.door_closed` (botóns novos no simulador de pechadura). Se consta «pechada», o 3.º paso non se dá (resultado «A pechadura informa de que a porta está pechada»); os recordatorios á persoa si, porque a lista de peche tamén pregunta pola chave e polo resto.
- **Anotado na reserva:** `Booking.close_unconfirmed`. **Incumprimento** só se o concello o activa (`close_breach_enabled`, desactivado por defecto). **Choque:** o sistema de penalizacións que xa existe só ten a penalización por cancelación tardía e o estado «non presentada»; non hai bloqueos. Non se inventan sancións: o incumprimento queda marcado na escalada e visible na xestión.
- Execútase en `booking_maintenance` (recoméndase cron cada 5 min).

### C · Ficha ampliada
- **Accesibilidade detallada** en `Facility.accessibility_detail` (JSON: os 7 puntos con si / parcial / non e nota). Edítase na lapela «Accesibilidade». A **lista básica da v5 mantense** e enchese soa: só «si» marca o elemento básico correspondente (aparcamento, sen chanzos, aseo, vestiario, braille); «parcial» ou «non» desmárcano; «sen datos» non o toca. Un formulario sen os puntos detallados non borra o detalle.
- **Filtros novos** na busca, sen quitar os de antes: «Accesible» (itinerario desde o exterior **e** corredores/portas con «si»: a cadea mínima para entrar), «Con aparcabicis» e «Con DESA» (na propia instalación).
- **Sostibilidade:** aparcabicis (prazas; baleiro = sen datos, 0 = non), puntos de recarga (número e tipo), parada de transporte (opcional).
- **DESA:** na instalación (si/non, ubicación e horario) ou o máis próximo (nome, enderezo, distancia aproximada e horario). Botón «Buscar o DESA máis próximo» co adaptador novo `defibrillators` (por defecto le un CSV; o da demo é **ficticio**). Distancia en liña recta (haversine), mostrada como «a uns ‹n› m».
- **Non verificado:** non sabemos se existe un rexistro oficial galego de DESA con datos abertos reutilizables nin con que licenza. **Non se integra ningunha app concreta** (p. ex. ARIANA RCP) sen verificar antes os seus datos e a súa licenza. O adaptador CSV permite cargar un rexistro oficial cando se confirme (`EIRA_DESA_CSV`).
- **Revisión de seguridade inicial:** +3 puntos (accesibilidade detallada, DESA, aparcabicis e recarga). O test que contaba 10 puntos pasa a 13.
- **Índice de vida activa:** o compoñente de accesibilidade usa os 7 puntos detallados (si = 1, parcial = 0,5). Sen ningún punto detallado úsase a lista básica, para non baixar a nota por falta de datos. Ver `docs/indice-vida-activa.md`.
- **Choque de nomes:** `Facility.equipment_items()` (material da v5) xa existía; o inventario de equipos do bloque D usa `energy_equipment`.

### E · Satisfacción con NPS
- **«Que tal foi?» mantense** igual despois de cada uso (Ben/Regular/Mal). Todo o novo vai na app `apps/surveys`.
- **Enquisa anual** (`Survey`, unha por concello e ano) cunha xanela de datas: NPS (0–10), sete aspectos do 1 ao 5 (cada un admite «Non sei»), instalación que máis usa (opcional) e comentario opcional. **Unha resposta por persoa** (restrición única). O persoal do concello non responde (403).
- **NPS = % promotoras (9–10) − % detractoras (0–6)**, redondeado. Só se mostra con **n ≥ 10** (a enquisa, cada aspecto e cada instalación por separado). Os comentarios móstranse sen nome nin data, en orde aleatoria, e só cando a enquisa ten 10 respostas ou máis. **Decisión:** a proposta di «resultados só agregados»; un comentario libre non é un agregado, pero sen el a enquisa perde moito valor. Mostrámolos desligados da persoa e co aviso «non escribas datos persoais».
- **Evolución** por ano (táboa) e **por instalación** (a «instalación que máis usas» da enquisa e, á parte, o NPS despois do uso dos últimos 12 meses). Non se mesturan as dúas medidas porque se preguntan en momentos distintos.
- **Aviso da enquisa** por app, correo e Telegram (`announce`): á veciñanza do concello (rol veciñanza ou empadroamento) segundo as canles que cada persoa ten activas; non ao persoal. Na app sae un aviso no inicio mentres non responda.
- **NPS despois de cada uso:** opción do concello **desactivada por defecto** (`nps_after_use`). Se se activa, aparece debaixo de «Que tal foi?» (valoración e lista de peche) como pregunta opcional.
- **Onde se ve:** «Enquisas (NPS)» na xestión, tarxeta no panel do día e táboa «Satisfacción anual (NPS)» na comparativa da deputación (e columna no CSV/ODS), sempre agregada.

### F · Menos ausencias
- **Paso a paso visible de 3 pasos** (Elixe → Paga → Confirma) na ficha de cada instalación, enriba da dispoñibilidade. **Choque:** os pasos do proceso de reserva da v3 («Escolle franxa → Normas e confirmación → Pagamento e acceso») non se tocan; o novo explica o ciclo enteiro, incluída a confirmación de asistencia.
- **«Que tes que facer e cando»** en cada reserva: pagar (se falta), confirmar (desde 24 h antes), ata cando se cancela gratis, como entrar segundo o nivel (e que se libera aos 15 min se hai lista de espera) e a lista de peche.
- **Recordatorios ás 24 h e ás 2 h** (`send_reminders`, en `booking_maintenance`): o de 24 h tamén por correo, o de 2 h só na app (push), para non saturar. Levan á reserva, onde están **«Confirmo»** e **«Cancelo»**. Cancelar é **un toque** (POST directo, sen pantalla intermedia); a penalización, se a hai, xa se mostra ao lado do botón.
- **Lista de espera nas franxas** (`WaitlistEntry`): nas franxas ocupadas da ficha, a pílula leva a «Avísame se queda libre». **A franxa libérase só se hai alguén agardando** (sen lista de espera non se toca nada) e:
  1. alguén cancela (calquera cancelación agás os peches da instalación, que nunca ofrecen a franxa);
  2. o concello o activa (`confirm_release_enabled`, **desactivado por defecto**) e non se confirmou N minutos antes (120 por defecto): cancélase coas regras de sempre;
  3. non hai check-in aos 15 min do inicio nos **niveis 0, 2 e 3**: a reserva pasa a «non presentada». **Choque:** a v5 non marca «non presentada» no nivel 0 porque o QR é voluntario; iso segue igual cando non hai lista de espera. Co nivel 1 (chave custodiada) non se libera nunca.
- **Oferta por orde** de chegada á lista, unha persoa cada vez, co prazo configurable (30 min; nunca máis alá do fin da franxa). Se non responde, pasa á seguinte. Quen acepta reserva e paga como sempre (TPV se é a forma por defecto). Unha franxa xa comezada pódese coller (`create_booking(..., allow_started=True)`).
- **O ciclo queda rexistrado** (`SlotRelease.log`: liberada, ofrecida a, non respondeu, colleuna, penalización devolta) e vese na reserva orixinal (app e xestión). Só co nome de pila.
- **Penalizacións:** as que xa existen mantéñense. **Decisión «devolución se corresponde»:** se a franxa se volve vender despois dunha cancelación tardía, devólvese a penalización (o concello non perde o ingreso). Nas non presentadas por falta de check-in non hai devolución (como ata agora).
- Tarefa periódica: `booking_maintenance` (recoméndase cron cada 5 min para que as ofertas caduquen a tempo).

### D · Rendemento: consumo estimado e KPI
- **Inventario de equipos** (`Equipment`: tipo, potencia kW, modo de uso, factor 0–1) e **lecturas de facturas** (`EnergyReading`) por instalación, no panel novo «Rendemento» (lapela da instalación). Resumo de todas as instalacións en «Xestión → Rendemento». Fórmulas en `docs/rendemento-instalacions.md`; probas coas contas feitas á man.
- **Decisións de cálculo:** o modo «só con reserva» conta as reservas **usadas** (con check-in) e, no nivel 0, tamén as confirmadas (o QR é voluntario); as non presentadas non acenden nada. Nas instalacións compartidas úsase a unión no tempo (catro persoas á vez = unha hora de equipo). As horas de apertura descontan os peches.
- **Sempre «estimación orientativa»**: aviso fixo no panel e etiqueta na táboa. Prezo €/kWh e factor de CO₂ configurables por concello (por defecto 0,18 €/kWh e 0,150 kg/kWh, orientativos).
- **Perfil** de persoas usuarias só agregado e con n ≥ 10. **Deputación:** ve o panel en modo consulta (vista agregada, sen editar) e unha táboa por concello na comparativa (ocupación, uso real, kWh, kWh por hora de uso); tamén no CSV/ODS.
- **Tendencia mensual** desde o primeiro mes con reservas (mínimo 3, máximo 12), para non encher a gráfica de ceros.
- **Tema escuro:** o escritorio do concello non tiña tema escuro (decisión v4.1). Para as capturas pedidas en escuro do bloque D, **só o panel Rendemento e o resumo** activan o tema escuro (`themable-desk`), con cores literais para a barra lateral e o pé. O resto do escritorio segue igual. axe en escuro comprobado nesas dúas páxinas.

### G · Partidas abertas
- **«Busco xente» desde a reserva confirmada** (tarxeta na pantalla da reserva e ligazón desde «Partidas abertas»): prazas libres (ata o máximo de persoas da instalación), nivel e mensaxe curta (140 caracteres). **Decisión:** a proposta di «ao reservar»; como a reserva non existe ata que se paga (TPV, oficina…), publícase **xusto despois**, desde a reserva confirmada, e nunca unha reserva sen pagar.
- **Sección «Partidas abertas»** (`/reservas/partidas/`, atallo no inicio da app) filtrable por deporte (tipo de instalación), día e nivel, co propio concello e os concellos próximos da rede abertos (como as reservas da v5).
- **Unirse** = solicitude que quen organiza acepta ou rexeita (aviso na app). Ao aceptar, **sube o número de persoas da reserva** e baixan as prazas libres; se alguén aceptado se retira, volve baixar.
- **Privacidade:** só nome de pila e inicial do apelido (`public_name`); nunca teléfono nin correo; **sen chat libre** (cinco mensaxes predefinidas, só entre quen organiza e quen xoga); consentimento explícito ao publicar e ao unirse; **menores de 14 non publican nin se unen** (tampouco sen ano de nacemento). Matriz en `docs/rxpd/matriz.md` e filas en «Quen custodia os teus datos».
- **Reparto orientativo** = prezo ÷ (persoas da reserva ao publicar + prazas). O pagamento segue sendo de quen organiza; Eira non cobra nin reparte cartos.
- **Denunciar:** motivo predefinido, aviso á administración do concello; **con 3 denuncias** a partida ocúltase ata que o concello a revise. Cada concello pode desactivar a función (módulo «Partidas abertas», activado por defecto).
- **Non verificado:** a conservación indicada para as denuncias (1 ano) non ten purga automática programada.

### H · Carné municipal único
- **App nova `apps/members`**: tipos de abono por concello (xeral, mocidade, maiores, familiar, outro) con prezo, validez e desconto; abonos (`SportsPass`) e carné (`MemberCard`, un por persoa e concello, foto opcional). Módulo «Carné municipal e abonos» activado por defecto e desactivable.
- **Alta e renovación** co TPV (desde «O meu carné»; o `Payment` leva un campo novo `sports_pass` e a pasarela simulada actívao) ou na oficina (efectivo ou tarxeta no TPV físico). A renovación empeza cando remata o abono activo.
- **Desconto:** aplícase despois da tarifa (empadroada/non empadroada, mocidade, maiores) e do desconto de baixa demanda, e non toca o suplemento de luz. **Choque:** as regras de tarifa existentes non cambian; o abono só engade unha porcentaxe ao final, que se mostra no desglose («−20 % co teu abono»).
- **QR dinámico asinado** (`TimestampSigner`, caduca aos 3 min, renóvase cada minuto con HTMX) e **carné imprimible** en PDF etiquetado tamaño ID-1 co xerador accesible do cartel (o seu QR leva versión e data de fin; o concello pode anulalo). O QR non leva datos persoais.
- **Usos:** lector na xestión (entrada da reserva actual, abono e bonos); tableta da persoa monitora (campo «Ler carné» enriba da lista por nome, que **se mantén**; se a persoa non está inscrita, marca as crianzas da súa unidade familiar no grupo). **Decisión:** o lector acepta o código como texto, que é o que envían os lectores de QR USB/Bluetooth; non se usa a cámara (evita permisos e funciona en tabletas sen cámara traseira). Non probado con lectores físicos (non verificado).
- **Adaptador `municipal_card`** (simulado con CSV ficticio) para vincular cun carné existente (biblioteca, piscina): **só o adaptador e a documentación** (`docs/carne-municipal.md`), sen integración real.

### I · Peche da v1.2
- **Demo** (`apps/tenants/demo_v12.py`, todo ficticio): fichas con accesibilidade detallada, aparcabicis, recarga e DESA (na instalación ou o máis próximo do CSV ficticio); equipos de seis instalacións e lecturas de facturas de dous meses (pavillón e piscina); enquisa do ano pasado pechada (Vilardeiras 26 respostas, Pontedouro 22) e a deste ano aberta (Uxía aínda non respondeu); Pontedouro co NPS tras o uso activado; partidas abertas (unha con solicitudes, unha persoa aceptada e mensaxes); tipos de abono e abonos (Uxía polo TPV, Manuel na oficina e cun abono caducado no historial, carné vinculado ao carné ficticio da biblioteca); unha lista de espera resolta (cancelación tardía, primeira persoa sen resposta, segunda colle a franxa, penalización devolta) e Uxía agardando unha franxa; un peche escalado á conserxaría e revisado; un accidente leve rexistrado e pechado.
- **Corrección:** `SportsPass.type` levaba `PROTECT` e impedía borrar un concello con abonos, o que rompía a rexeneración da demo. Agora `CASCADE` (test de regresión).
- **Corrección:** a tarefa `annex` de `tools/tasks.py` non estaba rexistrada (desde a v5); agora si.
- **Corrección:** «Que tes que facer e cando» xa non mostra «Confirma» nin «Cancelación gratuíta ata…» cando a reserva comezou ou o prazo pasou.
- **Corrección (preexistente):** desbordamento horizontal a 360 px no selector de franxas («+luz») e na táboa de tarifas da ficha con texto grande; apareceu ao engadir o pavillón á proba sen scroll horizontal.
- **Vídeos:** o pitch non se regraba (o guión non se rompe). O anexo regrábase con dous pasos novos (Rendemento e NPS): 65 s.
- **RAM sen IA** medida con `docker compose -p eira-v12` (PostgreSQL, volumes novos, sen tocar os existentes).

## v1.3 · Documentación para a adopción e preparación para publicar (27/10)
Regra de sempre: **só se engade**. Tanda case toda de documentación; o código novo é só o do bloque C.

### A · Modelo de ordenanza
- **Un só ficheiro** `docs/concello/ordenanza-modelo.md` co texto en galego e, debaixo, a versión en castelán (é o que pedía a ruta). Cada artigo leva entre corchetes o campo de configuración de Eira; se Eira non o fai, dino (**suspensión por non presentarse** e **vía de constrinximento**).
- **Prezo público por defecto** (arts. 41–47 TRLRHL) e **variante de taxa** (arts. 20 e seguintes) ao final de cada artigo e resumida na sección 3. Para Eira son iguais.
- **Choque:** a ordenanza remite ao desconto das franxas de baixa demanda, pero `low_demand_discount_pct` **non se podía cambiar desde a xestión** (só desde o admin técnico). **Engádese** á sección «Regras de reserva» da configuración; se non vén no formulario, mantense o valor (mesmo criterio que os campos da v5 e v1.2).
- **Non hai campo de «entidade exenta»**: a ordenanza indica facelo coa forma de pagamento «Gratuíta» ou cunha tarifa 0. Non se crea un campo novo nesta tanda (só documentación).
- As citas legais (TRLRHL, LBRL, LGT, Lei 40/2015) **revisáronse sen consultar o BOE consolidado** nesta sesión: o propio documento avisa de que require informe xurídico e de Intervención.

### B · EIPD
- Plantilla en `docs/rxpd/eipd-plantilla.md`, cuberta co que fai Eira e cos tests que o comproban. A valoración de riscos (probabilidade, impacto, residual) é unha **proposta** para o DPD.
- **Enlace desde «Quen custodia os teus datos»:** a app non pode ligar a un ficheiro do repositorio (aínda sen URL pública), así que se engade un **resumo en linguaxe clara** na propia app (`/c/‹concello›/privacidade/avaliacion-impacto/`, datos en `apps/accounts/dpia.py`) e unha tarxeta «Datos con máis risco» na páxina de custodia. A matriz (`docs/rxpd/matriz.md`) liga á plantilla.
- A táboa nova da matriz (contas de xestión) usa a cabeceira «Dato do persoal» para que non entre na páxina de custodia da veciñanza (o mesmo criterio ca na v1.1).

### C · Seguridade das contas de xestión
- **Comprobado:** non había dobre factor. **Había** rexistro de auditoría (`AuditLog`) para tarifas, asignación de roles, exportación íntegra, soporte, brechas e accidentes, pero faltaban a retirada de roles, as descargas do persoal e unha vista para consultalo.
- **TOTP con `pyotp`** (xa era dependencia polos códigos sen conexión): sen dependencias novas. Valores estándar (30 s, 6 díxitos, SHA-1) porque son os que admiten todas as apps.
- **Bloqueo por middleware** (`TwoFactorMiddleware`) e non nas vistas de acceso: así cobre o código ao correo, Cl@ve, o cambio de perfil da demo e o admin técnico, e tamén as sesións que xa estaban abertas cando se activa. `/acceso/`, `/static/`, `/i18n/` e `/dev/` quedan fóra (a demo debe poder cambiar de perfil).
- **Obrigatorio por concello** para administración e DPD (`require_2fa_admin`, **desactivado por defecto** para non cambiar a demo nin os despregamentos existentes). Para a deputación, `Region.require_2fa` no admin técnico: non existe pantalla de configuración da deputación e non se crea nesta tanda.
- **Restablecemento** por outra persoa administradora do mesmo concello, só se a persoa non xestiona outros concellos nin a deputación (senón, un concello podería quitarlle o segundo factor a quen xestiona outro).
- **O segredo TOTP gárdase sen cifrado adicional** na base de datos (como `django-otp`). Cifralo cunha clave derivada de `SECRET_KEY` sen unha biblioteca criptográfica auditada sería peor; anótase como risco na EIPD (protexer BD e copias).
- **Descargas:** un middleware (`ExportAuditMiddleware`) rexistra toda resposta `attachment` pedida polo persoal, en vez de tocar cada vista de exportación. A descarga do propio rexistro márcase para non contala dúas veces.
- **Vista do rexistro** en `xestion/privacidade/auditoria/`, co mesmo control ca o rexistro de brechas (`breach_access`: administración e DPD do concello; a deputación non, nin co acceso de soporte). Os inicios de sesión gárdanse sen concello; móstranse os do persoal de xestión dese concello, nunca os da veciñanza.
- **Tema escuro:** o escritorio do concello segue sen tema escuro (decisión da v1.2); as pantallas novas da conta (seguridade, segundo paso, códigos) si se proban en escuro.

### D · Publicación
- **Non se reescribiu o historial.** Os achados (subdominio `demo` de `eira.gal` en commits antigos, un nome de pila nos commits da v1.2, un apelido común na lista ficticia, tamaño das capturas) e a proposta de limpeza están en `docs/AUDITORIA_PUBLICACION.md`.
- O repositorio xa ten un remoto `origin` con `origin/master` en `5181c06`: non se fixo push (regra da sesión) e non se consultou a rede para saber se é público.
- `.gitignore` ignora desde agora `*.docx`, `*.doc`, `*.odt` e `*.pdf` (agás en `docs/`), para que a carta de interese ou outros documentos alleos non se poidan versionar por erro.
- `GOVERNANCE.md` en galego e castelán. Non se inventan persoas mantedoras: figura o «Equipo Eira» e proponse un comité de persoas usuarias cando haxa concellos.

### Corrección
- **Demo v1.2:** o exemplo de «peche sen confirmar» só se creaba se, ao chou, había unha reserva usada onte no pavillón. Algúns días non a hai e as probas axe fallaban (`esc` baleiro). Agora `demo_v12` crea esa reserva se falta (na primeira hora libre dunha lista: 20 h, 19 h, 21 h… ata as 10 h). Só engade datos á demo.

## v1.4 · Copia limpa para publicar (27/10)
Decisións do equipo sobre a auditoría da v1.3: **este repositorio e o seu remoto non se reescriben** (quedan como arquivo privado co historial completo) e prepárase **á parte** unha copia limpa que será o repositorio público. Sen push nin repositorios remotos.

### A · Correccións neste repositorio
- **Conservación do rexistro de auditoría:** campo por concello `audit_retention_months`, **24 meses por defecto**, entre 12 e 120 (menos dun ano deixaría sen rastro incidentes que se detectan tarde; máis de dez anos non ten xustificación). Purga no comando de mantemento que xa existía (`booking_maintenance`, o mesmo onde se borran os accidentes e as solicitudes da app). As entradas sen concello (inicios de sesión e dobre factor das contas, accións da deputación) seguen o prazo por defecto. Cada purga con borrados deixa unha entrada `audit.purge`, sen datos persoais, para que se saiba que faltan entradas e por que.
- **Segredo TOTP cifrado:** na v1.3 descartouse cifralo «sen unha biblioteca criptográfica auditada». Agora engádese **`cryptography`** (Apache-2.0 / BSD-3, compatible coa EUPL-1.2; `make licenses` en verde) e úsase **Fernet** (AES-128-CBC + HMAC-SHA256), sen criptografía propia.
  - Chave: `EIRA_TOTP_KEY` se existe (recomendada en produción, así a chave non está na base de datos nin nas súas copias); se non, **derivada de `EIRA_SECRET_KEY` con HKDF** e un contexto propio. Cos dous admítense os valores antigos (MultiFernet) e o comando `rotate_totp_key` pásaos á chave nova.
  - Campo propio (`EncryptedCharField`) que cifra ao gardar e descifra ao ler: o resto do código non cambia. Prefixo `enc1:` para distinguir os valores cifrados do texto claro anterior, que se le tal cal ata que a migración o cifra (a actualización non deixa a ninguén fóra).
  - Se a chave cambia sen rotar, o segredo le baleiro e os códigos fallan **sen erro 500**; a persoa entra cun código de recuperación ou llo restablece outra administración.
  - A importación de `cryptography` é diferida para que os comandos que só cargan os modelos (como `makemessages` na imaxe Docker anterior) non a precisen.
- **Demo:** o apelido común da lista ficticia substitúese por «Calvo». As mencións ao dominio de demostración antigo na documentación reescríbense describíndoo («subdominio `demo` de `eira.gal`») en vez de copialo literalmente, para que non quede no repositorio nin o reintroduza ningunha busca e substitución.
- **Base de datos local da demo:** quedaban 43 contas de demo antigas (do 23/10) co dominio anterior, porque `seed_demo` só borra as do dominio actual. Borráronse a man **só na base local** (non é código). Unha instalación nova non as ten.
- O menú da configuración pasa a chamarse «Seguridade das contas e rexistro de auditoría» (inclúe o prazo); a documentación actualízase.

### B · Copia pública
- **Script reproducible** fóra dos dous repositorios (carpeta `Eira-release/ferramentas/`, ao lado do repositorio): clona con `--no-local`, quita o remoto, reescribe con `git filter-repo` (MIT; instalado nun contorno virtual á parte, non é dependencia de Eira), engade un commit coas capturas clave, move a etiqueta `v1.4-certame` a ese commit e compacta. A copia pódese rexenerar en segundos tras cada cambio aquí.
- **Substitucións no historial da copia:** o dominio de demostración antigo → `demo.eira.example`; o nome de pila da persoa que fixo as propostas da v1.2 → «o equipo» (con formas concordadas: «do equipo», «del equipo»…; tamén nas mensaxes de commit e nas anotacións das etiquetas); e, **ademais do pedido**, o apelido común da demo → «Calvo» en todo o historial, coa mesma razón ca o cambio do bloque A (doutro xeito seguiría nas versións antigas de `apps/activities/demo.py`). Se non se quere, abonda con quitar esa liña do ficheiro de substitucións e volver xerar a copia.
- **Capturas:** `docs/capturas/` sae do historial e vai a `capturas-v1.4.zip` (as 615 PNG e o README de `v2/` do último commit, tal cal; as versións anteriores de cada captura non se gardan). As **6 capturas clave** fixéronse **de novo** coa demo da v1.4 (apelido e dominio novos), só da parte visible da pantalla e con 256 cores: entre 19 e 87 KB cada unha. O README da copia móstraas na sección «Como se ve».
- **Binarios > 5 MB:** fóra de `docs/capturas/` non hai ningún no historial (o maior é de 2,4 MB, en `assets-originais/`). Igualmente pásase `--strip-blobs-bigger-than 5M` como rede de seguridade.
- Os **hashes dos commits cambian** na copia: os documentos que citan commits (auditoría, informe) refírense aos deste repositorio. A correspondencia vella → nova gárdase en `Eira-release/correspondencia-commits.txt`.
- **Etiqueta `v1.4-certame`:** aquí, no último commit da tanda; na copia, no commit de publicación (README con capturas), coa mesma anotación.

## 2026-11-05 · v1.5: versión definitiva

### A · «Escoitar»
- **Só `speechSynthesis`.** Ningún servizo externo. Sen a API, o botón non aparece (oculto ata que o JS o comprobe).
- **Interface en castelán → voz en castelán, sen aviso.** O aviso «non hai voz en galego» só aparece unha vez por dispositivo.
- **Lectura automática do código desactivada por defecto:** o código oiríase en voz alta e pode pisar o lector de pantalla. Algúns navegadores non deixan falar sen tocar antes a pantalla.
- **Non verificado:** TalkBack e VoiceOver en dispositivos reais; as probas usan unha voz simulada. Para non interferir: só fala se se lle pide, non move o foco e non usa `aria-live` mentres le.

### B · Alerta
- **«Sesión activa» defínese así:** monitora con sesión aberta nesa instalación (co seu marxe), persoal cunha orde «en curso» nela e persoal de limpeza cun rexistro nas últimas 2 h. **Conserxe:** `ResponsibleContact.facility`, nova, opcional. Non se usa ningunha ubicación do móbil.
- **Na alerta queda o posto, non o nome**, porque a pantalla de confirmación pode vela quen a lanzou.
- **Botón Alerta na cabeceira e na pantalla principal** de mantemento, limpeza e monitora; na cabeceira da administración. A deputación en consulta non o ten. O acceso anterior «Incidencia ou seguridade» mantense.

### C · Procedencia
- **`n` son persoas distintas**, non reservas: máis protector ca o pedido literal.
- **Só períodos de 30, 90 e 365 días**, sen datas libres, para dificultar comparar dúas ventás case iguais.
- **«Outras procedencias» sen cifra se n < 10; sen totais; puntos quentes só con fluxos visibles**, para que non se poida restar.
- **Concellos fóra da rede:** non se nomean; van a «outras procedencias».
- **Mapa SVG no servidor, sen teselas:** funciona sen conexión e sen terceiros. Os concellos afastados móstranse na súa dirección real, fóra de escala e coa distancia no nome. A táboa é a alternativa accesible.
- **Límite coñecido:** comparar datas distintas pode deixar ver variacións pequenas dun fluxo visible. Documentado na matriz e na EIPD para que o revise o DPD. Non se redondean as cifras.

### D · Documentos legais
- **Non bloquea o uso:** un aviso permanente na app leva aos pendentes. Bloquear podería impedir chegar á propia reserva ou ao código nun momento crítico. Opción de bloqueo en `PLAN_V2`.
- **Obrigatorios para mostrar:** privacidade, condicións, normas e, con menores ao cargo, o de menores. **Imaxe e saúde son opcionais**: nunca se pide aceptalos con insistencia, e retirados non volven aparecer.
- **O aviso «MODELO DE EXEMPLO» só se quita ao adaptar o texto e declarar que se revisou.** Un modelo adoptado tal cal seguiría sendo un modelo.
- **Normas:** as normas versionadas de cada instalación seguen igual e móstranse dentro do documento xeral.
- **Ao eliminar a conta** a aceptación queda sen persoa, para que o rexistro siga cadrando sen datos persoais.
- **O texto do concello pasa por un Markdown mínimo que escapa o HTML** (`apps/tenants/markup.py`), sen dependencias novas.

### E · Acreditación
- **Grupo con menores:** admite menores de 18 ou xa ten menores inscritos.
- **Revisión vencida:** bloquea novas asignacións e avisa, pero non desfai as existentes, para non deixar un grupo sen persoa á vista. Tampouco se desfán as anteriores á v1.5: a ficha mostra o aviso.
- **Voluntariado:** `Membership.is_volunteer` no rol de monitora, sen crear un rol novo.
- **Límite:** o bloqueo está na interface e no admin técnico (`Group.clean`), non na base de datos.

### Outros
- **Cabeceira da xestión en móbil:** agora axústase ao ancho. Xa desbordaba antes e o botón Alerta empeorábao; non se quitou nada.
- **`tools/i18n_check.py`:** sen GNU gettext, comproba que o catálogo teña todas as cadeas e engade traducións. Unha proba impide deixar cadeas sen catálogo.
- **Portabilidade:** exporta os datos novos en `v15.json`; a importación queda en `PLAN_V2`.

## 2026-11-05 · v1.5.1: CI de GitHub en verde
- **Causa:** `docs/api/openapi.yaml` non se rexenerara desde a v5 (faltaban `pending_approval`, `pending_office` e `declined`). O paso OpenAPI paraba o job antes de Tests e E2E. Rexenérase; non cambia ningunha API.
- **Runner fixo:** `ubuntu-24.04`, non `ubuntu-latest`, para que non cambie só.
- **Accións:** `actions/checkout@v7` e `actions/setup-python@v7`, as vixentes o 05/11/2026; comprobouse no seu `action.yml` que usan Node 24. Son máis novas que as `@v5` e `@v6` citadas como exemplo.
- **Caché de pip:** xa estaba `cache: pip`; engádese `cache-dependency-path: requirements*.txt` para que tamén cambie con `requirements-dev.txt`.
- **E2E con vídeo:** xa ían excluídos (`tools/tasks.py e2e` usa `e2e and not video`). Non se cambia.
- **Reprodución previa:** en contedor `python:3.13-bookworm` con `postgres:16-alpine`, sobre un clon limpo da copia e cos mesmos comandos. Non é o mesmo sistema ca o runner (Debian, non Ubuntu 24.04): a proba definitiva é o run de GitHub.
- **Disparadores:** a CI execútase só en push a ramas e en pull requests, sen etiquetas: evita runs duplicados do mesmo commit (uns 40 min cada un) nun repositorio privado. O commit etiquetado próbase igual na rama.
- **Proba dependente da hora:** a demo deixa abertas as limpezas das últimas 20 h, así que de madrugada a primeira orde pendente é unha limpeza de onte, que mantemento non debe ver (404 correcto). As probas de axe e do recorrido elixen agora unha orde que non sexa de limpeza. A aplicación non cambia.
- **Máis probas dependentes da data (atopadas co reloxo fixado nas 23:50 e nas 00:30):** a lista de espera miraba a grella da semana actual, e en fin de semana a franxa de dentro de 2 días cae na seguinte; varias probas esixían a lista de espera de Uxía, que a demo só crea se mañá hai unha reserva doutra persoa no pádel. Corríxense as probas. **A demo non cambia:** nalgunhas datas e horas Uxía pode non ter esa lista de espera.
