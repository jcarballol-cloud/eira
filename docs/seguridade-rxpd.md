# Seguridade e protección de datos (RXPD)

## Base xurídica e responsable

- **Responsable:** cada concello para os seus datos (Eira é unha ferramenta; a deputación que a aloxe
  actúa como encargada do tratamento, art. 28 RXPD, con contrato de encargo).
- **Base:** cumprimento dunha misión de interese público / exercicio de poderes públicos
  (art. 6.1.e RXPD) na prestación do servizo municipal de deportes (Lei 7/1985, art. 25.2.l).
  O **consentimento** (art. 6.1.a e 8) só para o opcional: uso da imaxe e rexistro de esforzo e
  probas físicas de menores.
- **Textos modelo:** páxina `/c/<slug>/privacidade/` (personalizable por concello).

## Minimización e privacidade desde o deseño

| Dato | Por que | Decisión |
|---|---|---|
| Correo | Identificar a conta e enviar o código de acceso | Único obrigatorio |
| Nome para mostrar | Trato na interface, custodia de chaves | Opcional, libre |
| Teléfono | Reservas por teléfono | Opcional |
| Ano de nacemento | Tarifas mocidade/maiores | Só o ano, opcional |
| DNI | — | **Non se garda.** Cl@ve devolve un identificador que se garda como HMAC opaco |
| Contrasinal | — | **Non existe** para a cidadanía (código dun só uso; só se garda o HMAC do código) |
| Empadroamento | Tarifa | Só «validado o día D por método M»; sen acceso ao padrón |
| Menores | Inscrición en escolas | Só nome e ano; consentimentos explícitos, revogables e con data |
| Saúde (idade, peso, actividade) | Consellos de hidratación | **Só no dispositivo** (localStorage); test E2E que comproba que non se envía nada |

## Datos que nunca saen do dispositivo

A páxina «A miña saúde» (`/saude/`) garda os datos en `localStorage`. Os campos non teñen `name` e o
formulario non ten `action`; o test `tests/e2e/test_flows.py::test_health_data_never_leaves_device`
rexistra todas as peticións de rede e comproba que ningunha contén os valores introducidos.

## Estatísticas e observatorio

- Indicadores do concello: agregados sen datos persoais.
- Datos abertos: reservas por instalación/día/hora, sen persoas.
- **Observatorio anónimo:** agregados por banda de idade; **umbral mínimo de agregación configurable**
  (`EIRA_MIN_AGGREGATION`, por defecto **n ≥ 10**); por debaixo, a cela suprímese. Tests:
  `apps/activities/tests/test_activities.py::test_observatory_threshold` (9 → oculto, 10 → visible).
- **Seudonimización:** cada inscrición ten un seudónimo HMAC-SHA256 co segredo do servidor. Os
  microdatos (só persoal administrador) levan seudónimo e banda de idade, nunca nome nin idade exacta,
  e só das bandas que superan o umbral.
- **IA opcional:** só recibe agregados; o adaptador rexeita entradas con campos persoais (test).
  Só se admiten modelos de pesos abertos aloxados polo concello.

## Dereitos

- Acceso e portabilidade: descarga JSON completa en «A miña conta».
- Supresión: eliminación da conta; as reservas pasadas quedan anonimizadas (obriga contable).
- Rectificación: edición do perfil. Revogación de consentimentos: un clic, con data.

## Medidas técnicas (ENS, RD 311/2022, categoría básica-media orientativa)

| Medida | Implementación |
|---|---|
| Identificación e autenticación [op.acc] | Código dun só uso de 6 díxitos, caduca en 10 min, máx. 5 intentos; límite de envíos por correo e por IP; Cl@ve/Chave365 previstos (nivel substancial) |
| Control de acceso [op.acc.4] | Roles por concello (`citizen`, `admin`, `maintenance`, `monitor`) e `region_admin`; decoradores `role_required`; tests de permisos e illamento |
| Rexistro de actividade [op.exp.8] | `AuditLog` con actor, concello, acción, obxecto e detalle |
| Protección das comunicacións [mp.com] | HTTPS no proxy; HSTS e cookies `Secure` configurables; CSP estrita sen `unsafe-inline`, `frame-ancestors 'none'`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` |
| Protección da información [mp.info] | CSRF en todos os formularios; validación de subidas (tamaño, formato real con Pillow, reescritura da imaxe que elimina EXIF/GPS) |
| Segredos | Ningún no repositorio: `EIRA_SECRET_KEY` e credenciais por variables de contorno; `.env` ignorado |
| Continuidade [op.cont] | Exportación íntegra e importación noutra instancia; PostgreSQL con copias da deputación |
| Desenvolvemento seguro [mp.sw] | Tests automáticos, ruff, comprobación de licenzas e SPDX en CI |

## Riscos coñecidos

- Os códigos de nivel 2 non están ligados á persoa: ver [offline-codes.md](access/offline-codes.md).
- O límite de intentos usa a caché local do proceso; nun despregamento con varios procesos convén
  `EIRA_CACHE_DIR` (caché en disco compartida) ou Redis.
- O admin técnico de Django usa contrasinal: restrinxilo por IP no proxy.

## v1.3 · Seguridade das contas de xestión

### Que había antes da v1.3 (comprobado no código)

| Comprobación | Resultado |
|---|---|
| Dobre factor nos roles de xestión (administración, deputación, DPD) | **Non existía.** Todas as contas entraban só co código ao correo ou con Cl@ve (simulada). O admin técnico de Django, con contrasinal |
| Rexistro de auditoría | **Existía** `AuditLog` (desde a v1) e xa rexistraba tarifas (`facility.tariffs`), asignación de roles (`tenant.staff_add`), exportación íntegra (`tenant.export`), acceso de soporte (`support.*`, cada páxina vista), brechas (`breach.save`) e accidentes (`accident.*`) |
| Faltaba no rexistro | A **retirada** de roles; as **descargas** de CSV/ODS/PDF/ICS do persoal (cobros, indicadores, microdatos do observatorio, limpeza…); e unha **vista** para consultalo (só se vían os usos do acceso de soporte en «Persoal e códigos») |

### Dobre factor (TOTP, RFC 6238)

- **Que é:** despois do código ao correo ou de Cl@ve, a persoa escribe o código de 6 díxitos dunha
  app de códigos do móbil (calquera compatible con TOTP: FreeOTP, Aegis…). Pasos de 30 s, SHA-1,
  6 díxitos (os valores por defecto da RFC 6238 e de todas as apps). Implementación con `pyotp`
  (MIT), que xa era dependencia de Eira para os códigos sen conexión.
- **Opcional por persoa:** *A miña conta → Seguridade da conta* (`/conta/seguridade/`). Activación:
  QR (ou clave en texto) → código de confirmación → **10 códigos de recuperación**.
- **Obrigatorio por concello:** *Xestión → Configuración → Seguridade das contas e rexistro de auditoría* (nome desde a v1.4)
  (`require_2fa_admin`, desactivado por defecto). Afecta a quen ten rol **administración** ou **DPD**
  nese concello (e á deputación cando entra nese concello). Quen non o teña activado e intente entrar
  na xestión vai á páxina para activalo. Non o pode desactivar mentres o concello o esixa.
- **Deputación:** `Region.require_2fa` (desactivado por defecto; configúrase no admin técnico porque
  a deputación non ten pantalla de configuración propia). Afecta á vista `/rexion/…`.
- **Como funciona o bloqueo:** `TwoFactorMiddleware`. Unha sesión dunha persoa co dobre factor
  activado e sen verificar só pode ver `/acceso/…` (incluída a páxina do segundo paso). Tras
  verificar, a sesión cambia de clave e queda marcada co dispositivo verificado. Ao activalo noutra
  sesión, **as demais sesións abertas desa persoa piden o segundo paso** na seguinte petición.
- **Reprodución:** un código non vale dúas veces (gárdase o último paso de tempo aceptado). Admítese
  un paso de desfase cara a diante e cara a atrás (reloxo do móbil).
- **Intentos:** 5 erros → peche da sesión e espera de 15 min (por persoa, na caché).
- **Códigos de recuperación:** 10, de 8 caracteres sen ambigüidades (sen 0/O nin 1/I/L), dun só uso;
  só se garda o HMAC-SHA256 co segredo do servidor; móstranse unha única vez (`Cache-Control:
  no-store`). Usar un avisa á persoa (app e correo) e queda no rexistro.
- **Móbil perdido sen códigos:** outra persoa **administradora do mesmo concello** pode restablecelo
  en *Persoal e códigos* (`2fa.reset`, rexistrado). Se a persoa xestiona outros concellos ou a
  deputación, non: faino o soporte técnico da instalación (admin técnico), para que un concello non
  poida quitarlle o segundo factor a alguén que xestiona outro.
- **Límites coñecidos:** desde a v1.4 o segredo TOTP gárdase **cifrado** (ver «v1.4» máis abaixo);
  os códigos de recuperación seguen dependendo de `EIRA_SECRET_KEY` (HMAC). Non hai
  WebAuthn/chaves de seguridade (proposto para a v2). O admin técnico de Django tamén pide o segundo
  paso se a conta o ten activado (está detrás do mesmo middleware).
- **Tests:** `apps/accounts/tests/test_twofactor.py` (15): vector da RFC 6238, activación,
  reprodución e xanela, recuperación dun só uso, bloqueo do acceso, aviso ao usar un código de
  recuperación, límite de intentos, obrigatoriedade por concello e por deputación, imposibilidade de
  desactivalo se é obrigatorio, restablecemento e os seus límites. E2E: `tests/e2e/test_v13.py`.

### Rexistro de auditoría

- **Onde:** *Xestión → Máis ferramentas → Rexistro de auditoría* (`/c/<concello>/xestion/privacidade/auditoria/`).
  Na barra da persoa DPD tamén.
- **Quen:** só a **administración do concello** e a **persoa DPD** (o mesmo control ca o rexistro de
  brechas, `breach_access`). A deputación **non** entra, nin sequera cun acceso de soporte. O
  superusuario técnico tampouco pola vía da app (si no admin técnico de Django).
- **Que mostra:** data, acción en linguaxe clara, categoría, persoa, obxecto e detalle. Filtros por
  categoría e datas; descarga CSV (que tamén queda rexistrada como `audit.export`). Non se pode
  editar nin borrar desde a app.
- **Categorías:**

| Categoría | Accións |
|---|---|
| Tarifas, prezos e configuración | `facility.tariffs`, `facility.rules`, `pass_type.*`, `voucher_type.*`, `tenant.settings` |
| Persoal e permisos | `tenant.staff_add`, **`tenant.staff_remove`** (novo), `tenant.invite`, `eligibility.validate`, `residency.issue`, **`2fa.reset`** (novo) |
| Exportacións e descargas | **`export.download`** (novo: toda descarga do persoal), `tenant.export`, `tenant.import`, `account.export`, **`audit.export`** (novo) |
| Acceso de soporte | `support.request`, `support.grant`, `support.revoke`, `support.view` |
| Brechas | `breach.save` |
| Accidentes e alertas | `accident.*`, `alert.*`, `closing.*` (incluído o contacto coa Policía Local) |
| Accesos e dobre factor | `auth.login`, **`auth.2fa`**, **`2fa.*`** (novos) do persoal de xestión do concello |

- **Descargas:** `ExportAuditMiddleware` rexistra calquera resposta `Content-Disposition: attachment`
  que pida unha persoa con rol de persoal no concello ou na deputación (ficheiro e ruta, nunca o
  contido). Así quedan cubertas tamén as exportacións futuras sen ter que lembralo en cada vista.
- **Os inicios de sesión** gárdanse sen concello (son da conta); na vista do concello móstranse os do
  seu persoal de xestión, nunca os da veciñanza.
- **Conservación:** desde a v1.4, 2 anos por defecto e configurable por concello (ver «v1.4» máis
  abaixo).
- **Non verificado / pendente:** protección contra a manipulación por quen ten acceso directo á base
  de datos (non hai encadeamento de hashes).
- **Tests:** `apps/accounts/tests/test_auditlog.py` (permisos por rol, deputación con acceso de
  soporte → 403, illamento entre concellos, filtros, categorías, retirada de roles, descargas, CSV
  rexistrado unha soa vez, resumo da EIPD).

## v1.4 · Segredo TOTP cifrado e conservación do rexistro de auditoría

### Segredo do dobre factor cifrado en repouso

- **Que se cifra:** o segredo TOTP de cada persoa (`TwoFactorDevice.secret`). Gárdase como
  `enc1:<token Fernet>`; o código da aplicación veo sempre en claro porque o campo
  (`EncryptedCharField`, `apps/accounts/secretbox.py`) cifra ao gardar e descifra ao ler.
- **Algoritmo:** Fernet da biblioteca `cryptography` (Apache-2.0 / BSD, compatible coa EUPL-1.2):
  AES-128-CBC con HMAC-SHA256 e IV aleatorio, así que cada gardado dá un texto cifrado distinto e
  calquera alteración detéctase.
- **Chave:**
  - `EIRA_TOTP_KEY`, se está definida (**recomendado en produción**): a chave queda fóra da base de
    datos e das súas copias, e cambiar `EIRA_SECRET_KEY` non deixa a ninguén sen dobre factor;
  - se non, derívase de `EIRA_SECRET_KEY` con HKDF-SHA256 e un contexto propio (non se usa a chave
    tal cal).
  - Con `EIRA_TOTP_KEY` definida séguense lendo os valores cifrados coa chave derivada de
    `EIRA_SECRET_KEY` (MultiFernet). Para pasalos á chave nova: `python manage.py rotate_totp_key`.
- **Migración:** `accounts/0012_v1_4` cifra os segredos que había en claro (v1.3). Mentres non se
  migra, o texto claro antigo lese tal cal, así que a actualización non bloquea a ninguén.
- **Se a chave se perde ou cambia sen rotar:** o segredo non se pode descifrar; a aplicación non
  falla, pero os códigos desa persoa deixan de valer. Pode entrar cun código de recuperación (se
  `EIRA_SECRET_KEY` non cambiou) ou que outra persoa administradora llo restableza.
  `rotate_totp_key` informa de cantos son ilexibles.
- **O que non protexe:** quen ten a base de datos **e** a chave (o servidor en execución). É unha
  defensa para as copias de seguridade e as exportacións da base de datos.
- **Tests:** `apps/accounts/tests/test_v14.py` (cifrado en repouso, texto cifrado novo en cada
  gardado, migración de ida e volta, lectura cos valores antigos e rotación cara a `EIRA_TOTP_KEY`,
  chave cambiada sen fallos, valor alterado rexeitado, a páxina de activación segue mostrando a clave).

### Prazo de conservación do rexistro de auditoría

- **Por concello:** *Xestión → Configuración → Seguridade das contas e rexistro de auditoría*
  (`audit_retention_months`). **2 anos por defecto**, entre 12 e 120 meses. A páxina do rexistro
  indica o prazo vixente.
- **Purga:** o comando de mantemento que xa existía (`python manage.py booking_maintenance`, cada
  15 minutos no cron) borra as entradas máis antigas ca o prazo de cada concello. As entradas sen
  concello (inicios de sesión e dobre factor das contas, accións da deputación) seguen o prazo por
  defecto de 2 anos.
- **Trazabilidade da purga:** cada purga que borra algo deixa unha entrada `audit.purge` («Entradas
  antigas borradas por conservación») co número de entradas e o prazo aplicado, sen datos persoais.
- **Tests:** `apps/accounts/tests/test_v14.py` (prazo por defecto, prazo distinto en cada concello,
  entradas sen concello, comando de mantemento, límites 12–120, cambio desde a configuración e aviso
  na páxina do rexistro).
