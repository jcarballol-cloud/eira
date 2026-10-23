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
