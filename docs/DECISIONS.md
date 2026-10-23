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
