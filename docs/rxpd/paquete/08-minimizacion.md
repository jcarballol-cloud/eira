<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Que non garda Eira, e por que

> **MODELO DE EXEMPLO — require revisión do DPD e dos servizos xurídicos do concello.**

Pensado para calquera persoa: veciñanza, persoal do concello ou quen avalíe Eira. A regra é
sinxela: **o dato que non se garda non se pode perder, nin roubar, nin usar para outra cousa**
(principio de minimización, art. 5.1.c RXPD, e protección de datos desde o deseño, art. 25).

## O que Eira non garda

| Non garda | Que fai no seu lugar | Por que abonda | Como se comproba |
|---|---|---|---|
| **O padrón municipal** | Garda só unha «pegada» (HMAC-SHA256) de «concello · DNI/NIE · data de nacemento» de cada persoa empadroada. O ficheiro do padrón lese en memoria e descártase | Para saber se alguén está empadroado abonda con comparar pegadas; coa pegada non se pode reconstruír o padrón | Tests `test_padron.py::test_import_keeps_only_hmac_and_logs` e `test_original_csv_is_not_kept` |
| **O DNI/NIE** de quen pide a app | Úsao para comparar co padrón e **bórrao ao resolver a solicitude** | Despois só fai falta saber «empadroada: si/non» | `test_padron.py::test_resolution_forgets_identity` |
| **O certificado de delitos sexuais** das monitoras | Só garda **quen** marcou que o comprobou e **cando** | Comprobalo é tarefa da contratación do concello (LOPIVI, art. 57); gardalo sería tratar datos penais (art. 10 RXPD) sen necesidade | `test_accreditation.py::test_allowed_after_confirm_and_only_who_and_when_stored` |
| **Datos de saúde no servidor** | Os consellos de auga e enerxía calcúlanse **no teu móbil**. Só se gardan na túa conta se o pides cun consentimento explícito, que podes retirar | Os consellos non precisan que o concello saiba o teu peso | `test_health.py::test_health_page_works_without_account_and_sends_nothing` |
| **Diagnósticos de accidentes** | O rexistro de accidentes leva tipo xeral, gravidade percibida e se se chamou ao 112. Sen texto libre | Abonda para mellorar a seguridade da instalación | `test_alert_profiles.py::test_accident_register_is_unchanged_no_free_text` |
| **GPS nin a túa localización** | Para as estatísticas de procedencia só se usa a parroquia ou o concello, se queres indicalo. As fotos gárdanse sen localización | Planificar transporte non require saber onde estás | `test_provenance.py::test_no_gps_fields_or_browser_geolocation`; `test_incidents.py::test_report_with_photo_strips_exif` |
| **Seguimento das aperturas de correo** | Os correos non levan píxeles nin ligazóns de seguimento | O concello non precisa saber se liches un aviso | Revisión do código (non hai test específico) |
| **Analítica de terceiros** (Google Analytics, píxeles de redes) | Ningunha. As estatísticas fanse cos propios datos do servizo, agregados | Non se envía a túa navegación a empresas de fóra | `test_privacy.py::test_only_technical_cookies`; a portada non fai peticións externas (`check_demo_online.py`) |
| **Cookies publicitarias** | Só cookies técnicas: sesión, seguridade, idioma e preferencias de accesibilidade | Non hai nada que consentir porque non hai seguimento | `test_privacy.py::test_only_technical_cookies` |
| **Datos de tarxeta ou conta bancaria** | O pagamento faise na pasarela da entidade financeira; Eira só garda referencia, importe e estado | Para conciliar abonda coa referencia | `test_payments.py::test_payments_conciliation_export` |
| **Contrasinais** | Entras cun código dun só uso enviado ao teu correo (ou con Cl@ve) | Un contrasinal que non existe non se pode filtrar | Deseño do acceso (`apps/accounts`) |
| **Apelidos dos menores na tableta** | A monitora ve nome e primeiro apelido | Abonda para pasar lista | `test_activities.py::test_minor_enrollment_requires_surnames` |
| **Teléfono ou correo nas partidas abertas** | Só nome de pila e inicial; mensaxes predefinidas, sen chat libre | Así non se poden intercambiar contactos pola app | `test_v12_open_games.py::test_list_shows_no_contact_data_and_price_split` |
| **Nomes nas valoracións** | O concello le os comentarios sen saber quen os escribiu | Para mellorar o servizo non importa quen | `test_ratings.py::test_admin_ratings_view_hides_names_and_ranks` |
| **Datos persoais na IA** | O asistente opcional só recibe cifras agregadas; se lle chega un campo persoal, négase | O resumo semanal non precisa persoas | `apps/integrations/ai.py` (`_check_aggregates`) |

## O que si garda, só o tempo necesario

Eira garda o imprescindible para cada servizo e bórrao ou anonimízao cando deixa de facer falta
(ver [05-conservacion.md](05-conservacion.md)). Exemplos:
- **As túas reservas:** 2 anos; despois quedan sen o teu nome para as estatísticas e a contabilidade.
- **Os códigos para entrar:** caducan en 10 minutos e bórranse ao día seguinte.
- **As fotos das incidencias:** sen localización; ao cabo de 2 anos de pechada a incidencia, bórrase a foto.

## O que debe coñecer o concello

- **Telegram** é un servizo de fóra da Unión Europea. Só se usa se a persoa o vincula; sempre hai
  app e correo.
- **O mapa** só se carga se a persoa pulsa «Ver mapa». Entón pide as imaxes a OpenStreetMap (Reino
  Unido), que ve o enderezo IP do navegador; o aviso dío xusto ao lado do botón. O concello pode usar
  o seu servidor de teselas en «Configuración → Mapa».
- **Os textos libres** (notas, comentarios) levan un aviso para non escribir datos de saúde, pero
  Eira non pode impedir que alguén o faga.
