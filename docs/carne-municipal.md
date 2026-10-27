<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Carné municipal único e abonos (v1.2 · H)

## Que hai en Eira

- **Abonos** (`apps/members`): tipos configurables por concello (xeral, mocidade, maiores, familiar, outro) con prezo, validez e **desconto nas tarifas**. Alta e renovación co **TPV** (desde o carné na app) ou na **oficina** (efectivo ou tarxeta, desde «Xestión → Abonos e carné»). Unha renovación empeza cando remata o abono activo.
- **Desconto:** aplícase despois da tarifa (empadroada ou non) e do desconto das franxas tranquilas; súmase a eles, non os substitúe. O suplemento de luz non leva desconto. Vese no desglose do prezo antes de pagar («−10 % co teu abono»).
- **Carné dixital** na app (`/c/‹concello›/carne/`): nome, foto opcional, abono e validez, número e un **QR dinámico asinado** que caduca aos 3 minutos e se renova só cada minuto (HTMX). Unha captura de pantalla deixa de valer.
- **Carné imprimible** (PDF etiquetado, tamaño tarxeta ID-1, 85,6 × 54 mm) para quen non usa o móbil. O seu QR non pode caducar en minutos (é papel): leva a versión do carné e a data de fin do abono. Se se perde, o concello **anúlao** (sobe a versión) e o impreso deixa de valer.
- **Usos do QR:**
  - entrada nas instalacións: «Xestión → Abonos e carné → Ler un carné» (persoal do concello ou de mantemento) rexistra a entrada da reserva que a persoa ten agora (ou nos próximos 30 min);
  - asistencia na tableta da persoa monitora: campo «Ler carné (QR)» enriba da lista por nome, que se mantén. Marca á persoa ou, se non está inscrita, ás crianzas da súa unidade familiar inscritas nese grupo;
  - bonos: o lector mostra os bonos activos e os usos que quedan.

## Seguridade do QR

- Asinado co segredo da instalación (`django.core.signing`, HMAC-SHA256), con sal distinto para o dixital e o impreso.
- O QR só leva o identificador interno do carné e a versión (e a data de fin no impreso): **ningún dato persoal**.
- Un carné doutro concello non vale (o lector filtra polo concello).

## Vínculo cun carné xa existente (adaptador `municipal_card`)

Moitos concellos xa teñen un carné (biblioteca, piscina). Eira inclúe **só o adaptador e esta documentación, sen integración real**:

- Interface: `apps/integrations/municipal_card.MunicipalCardAdapter` con `lookup(concello, número)` → `{external_id, service, valid}` (nunca datos persoais) e `link(carné, número)`.
- Implementación simulada: `FakeMunicipalCardAdapter`, cun CSV ficticio (`apps/integrations/data/carnes_demo.csv`).
- Selección por configuración: `EIRA_MUNICIPAL_CARD_ADAPTER`.
- Unha implementación real consultaría o sistema do concello (API do xestor da biblioteca, padrón de usuarios da piscina…) **só co número**, sen copiar a base de datos. Antes de facela hai que revisar o encargo do tratamento e a base xurídica.

## Non verificado

- Lectores de QR físicos: o lector da xestión e a tableta aceptan o código como texto (os lectores USB/Bluetooth teclean o contido). Non se probou con ningún modelo concreto.
- O PDF usa as fontes estándar sen incrustar e non está validado con PAC nin veraPDF (como o cartel da v5).
