<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Qué no guarda Eira, y por qué

> **MODELO DE EJEMPLO — requiere revisión del DPD y de los servicios jurídicos del concello.**

Pensado para cualquier persona: vecindad, personal del concello o quien evalúe Eira. La regla es
sencilla: **el dato que no se guarda no se puede perder, ni robar, ni usar para otra cosa**
(principio de minimización, art. 5.1.c RGPD, y protección de datos desde el diseño, art. 25).

## Lo que Eira no guarda

| No guarda | Qué hace en su lugar | Por qué basta | Cómo se comprueba |
|---|---|---|---|
| **El padrón municipal** | Guarda solo una «huella» (HMAC-SHA256) de «concello · DNI/NIE · fecha de nacimiento» de cada persona empadronada. El fichero del padrón se lee en memoria y se descarta | Para saber si alguien está empadronado basta con comparar huellas; con la huella no se puede reconstruir el padrón | Tests `test_padron.py::test_import_keeps_only_hmac_and_logs` y `test_original_csv_is_not_kept` |
| **El DNI/NIE** de quien pide la app | Lo usa para comparar con el padrón y **lo borra al resolver la solicitud** | Después solo hace falta saber «empadronada: sí/no» | `test_padron.py::test_resolution_forgets_identity` |
| **El certificado de delitos sexuales** de las monitoras | Solo guarda **quién** marcó que lo había comprobado y **cuándo** | Comprobarlo es tarea de la contratación del concello (LOPIVI, art. 57); guardarlo sería tratar datos penales (art. 10 RGPD) sin necesidad | `test_accreditation.py::test_allowed_after_confirm_and_only_who_and_when_stored` |
| **Datos de salud en el servidor** | Los consejos de agua y energía se calculan **en tu móvil**. Solo se guardan en tu cuenta si lo pides con un consentimiento explícito, que puedes retirar | Los consejos no necesitan que el concello sepa tu peso | `test_health.py::test_health_page_works_without_account_and_sends_nothing` |
| **Diagnósticos de accidentes** | El registro de accidentes contiene tipo general, gravedad percibida y si se llamó al 112. Sin texto libre | Basta para mejorar la seguridad de la instalación | `test_alert_profiles.py::test_accident_register_is_unchanged_no_free_text` |
| **GPS ni tu localización** | Para las estadísticas de procedencia solo se usa la parroquia o el concello, si quieres indicarlo. Las fotos se guardan sin localización | Planificar el transporte no requiere saber dónde estás | `test_provenance.py::test_no_gps_fields_or_browser_geolocation`; `test_incidents.py::test_report_with_photo_strips_exif` |
| **Seguimiento de las aperturas de correo** | Los correos no llevan píxeles ni enlaces de seguimiento | El concello no necesita saber si has leído un aviso | Revisión del código (no hay test específico) |
| **Analítica de terceros** (Google Analytics, píxeles de redes) | Ninguna. Las estadísticas se hacen con los propios datos del servicio, agregados | No se envía tu navegación a empresas de fuera | `test_privacy.py::test_only_technical_cookies`; la portada no hace peticiones externas (`check_demo_online.py`) |
| **Cookies publicitarias** | Solo cookies técnicas: sesión, seguridad, idioma y preferencias de accesibilidad | No hay nada que consentir porque no hay seguimiento | `test_privacy.py::test_only_technical_cookies` |
| **Datos de tarjeta o cuenta bancaria** | El pago se hace en la pasarela de la entidad financiera; Eira solo guarda referencia, importe y estado | Para conciliar basta con la referencia | `test_payments.py::test_payments_conciliation_export` |
| **Contraseñas** | Entras con un código de un solo uso enviado a tu correo (o con Cl@ve) | Una contraseña que no existe no se puede filtrar | Diseño del acceso (`apps/accounts`) |
| **Apellidos de los menores en la tableta** | La monitora ve nombre y primer apellido | Basta para pasar lista | `test_activities.py::test_minor_enrollment_requires_surnames` |
| **Teléfono o correo en las partidas abiertas** | Solo nombre de pila e inicial; mensajes predefinidos, sin chat libre | Así no se pueden intercambiar contactos por la app | `test_v12_open_games.py::test_list_shows_no_contact_data_and_price_split` |
| **Nombres en las valoraciones** | El concello lee los comentarios sin saber quién los escribió | Para mejorar el servicio no importa quién | `test_ratings.py::test_admin_ratings_view_hides_names_and_ranks` |
| **Datos personales en la IA** | El asistente opcional solo recibe cifras agregadas; si le llega un campo personal, se niega | El resumen semanal no necesita personas | `apps/integrations/ai.py` (`_check_aggregates`) |

## Lo que sí guarda, solo el tiempo necesario

Eira guarda lo imprescindible para cada servicio y lo borra o anonimiza cuando deja de hacer falta
(ver [05-conservacion.md](05-conservacion.md)). Ejemplos:
- **Tus reservas:** 2 años; después quedan sin tu nombre para las estadísticas y la contabilidad.
- **Los códigos para entrar:** caducan en 10 minutos y se borran al día siguiente.
- **Las fotos de las incidencias:** sin localización; al cabo de 2 años de cerrada la incidencia, se borra la foto.

## Lo que debe conocer el concello

- **Telegram** es un servicio de fuera de la Unión Europea. Solo se usa si la persona lo vincula; siempre hay
  app y correo.
- **El mapa** solo se carga si la persona pulsa «Ver mapa». Entonces pide las imágenes a OpenStreetMap
  (Reino Unido), que ve la dirección IP del navegador; el aviso lo dice justo al lado del botón. El
  concello puede usar su propio servidor de teselas en «Configuración → Mapa».
- **Los textos libres** (notas, comentarios) llevan un aviso para no escribir datos de salud, pero
  Eira no puede impedir que alguien lo haga.
