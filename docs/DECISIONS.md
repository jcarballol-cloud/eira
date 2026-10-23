# Rexistro de decisións

Formato: data · decisión · motivo · alternativas descartadas.

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
