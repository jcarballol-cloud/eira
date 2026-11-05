# Interoperabilidade e estándares abertos

| Ámbito | Estándar | Onde en Eira | Estado |
|---|---|---|---|
| API | **OpenAPI 3.1** | `/api/v1/`, esquema en `/api/schema/` e [`docs/api/openapi.yaml`](api/openapi.yaml) (validado con `drf-spectacular --validate --fail-on-warn`) | Implementado |
| Calendarios | **iCalendar RFC 5545** | `.ics` por reserva e de todas as reservas; exportación do concello | Implementado (liñas pregadas a 75 octetos, testado) |
| Códigos de acceso | **HOTP RFC 4226** (familia TOTP RFC 6238) | Nivel 2, [offline-codes.md](access/offline-codes.md) | Implementado |
| Notificacións push | **Web Push RFC 8030** + VAPID RFC 8292 | `PushAdapter`, endpoint de subscrición, service worker con `push` | Esqueleto (envío simulado) |
| Xeodatos | **GeoJSON RFC 7946** | Mapa de instalacións; `geo/instalacions.geojson` na exportación | Implementado |
| Datos tabulares | **CSV RFC 4180** (UTF-8) | Indicadores, datos abertos, exportación | Implementado |
| Folla de cálculo | **ODS** (OpenDocument, ISO/IEC 26300) | Indicadores do concello (`?ods=…`), escritor propio sen dependencias | Implementado |
| Datos abertos | **DCAT-AP** (JSON-LD) | `/c/<slug>/datos-abertos/dcat.jsonld` | Básico implementado |
| Catálogo de software público | **publiccode.yml** 0.4 | Raíz do repositorio | Validado con `publiccode-parser` 5.4.3 (`python tools/tasks.py publiccode`, sen comprobacións de rede ata publicar o repositorio) |
| Identidade | **SAML 2.0** (Cl@ve) · **OpenID Connect** (Chave365) | `IdentityAdapter`: simulado + esqueletos `ClaveSamlAdapter`, `Chave365OidcAdapter` | Previsto |
| Pagos | Redsys (HMAC-SHA256) | `PaymentAdapter`: `FakeRedsysAdapter` + esqueleto `RedsysAdapter` | Previsto |
| Pechaduras | MQTT / HTTP | `LockAdapter`: mock MQTT (`eira/<concello>/<dispositivo>/cmd`) | Simulado |
| Meteoroloxía | API MeteoSIX (MeteoGalicia) | `WeatherAdapter`: simulado + esqueleto `MeteoSixAdapter` | Previsto |
| IA | API compatible con OpenAI (servidor local) | `AIAdapter`: `FakeAIAdapter` e `OpenAICompatibleAdapter` (llama.cpp, Ollama, vLLM) | Opcional |
| Accesibilidade | WCAG 2.1 AA · EN 301 549 · RD 1112/2018 | Toda a interface; probas axe-core | Implementado |
| PWA | Web App Manifest · Service Workers | `manifest.webmanifest`, `sw.js` | Implementado |
| Licenzas | **SPDX** | Cabeceira en cada ficheiro | Implementado |

## Portabilidade íntegra

`/c/<slug>/xestion/portabilidade/` xera un ZIP co formato `eira-municipality-export/1`:

```
eira.json                 todos os obxectos do concello (identificadores remapeables)
csv/reservas.csv          reservas
csv/instalacions.csv      instalacións
ical/reservas.ics         calendario completo (RFC 5545)
geo/instalacions.geojson  localizacións (RFC 7946)
media/…                   fotos e ficheiros subidos
LEME.txt                  descrición e aviso de contido sensible
```

A importación (`import_municipality`) crea un concello novo noutra instancia remapeando todas as
chaves foráneas e conservando datas e segredos das pechaduras (os códigos seguen funcionando). O
test `apps/tenants/tests/test_portability.py` fai a ida e volta completa.

A persoa usuaria pode descargar todos os seus datos en JSON (`/conta/os-meus-datos.json`, art. 20
RXPD) e eliminar a súa conta.

## v1.5 · Datos novos na exportación

O ZIP de portabilidade inclúe `v15.json`: versións dos documentos legais, aceptacións e marcas de
acreditación (só quen e cando). A importación aínda non os restaura: consta en `docs/PLAN_V2.md`.
