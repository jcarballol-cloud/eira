<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Información por capas (arts. 13 y 14 RGPD; art. 11 LOPDGDD)

> **MODELO DE EJEMPLO — requiere revisión del DPD y de los servicios jurídicos del concello.**

El art. 11 LOPDGDD permite dar primero una **información básica** (responsable, finalidad y cómo
ejercer los derechos) y un medio sencillo para ver el resto. Estos textos **son los que muestra Eira**:
si el concello los cambia en la app, debe cambiarlos también aquí. Las partes entre `[corchetes]` son del
concello.

## Dónde aparece cada capa en Eira

| Capa | Dónde se ve | Plantilla |
|---|---|---|
| Primera (al pedir la app) | «Qué hacemos con estos datos», desplegable en el formulario | `templates/app/request.html` |
| Primera (al dar un consentimiento) | Texto junto a cada casilla (imagen, salud, menores, partidas abiertas) | `apps/accounts/forms.py`, `templates/core/health.html`, `templates/bookings/game_publish.html` |
| Segunda | Página «Privacidad» del concello (`/c/[concello]/privacidade/`) | `templates/core/privacy.html` |
| Tercera | «Quién custodia tus datos» (`/c/[concello]/privacidade/datos/`): qué dato ve cada perfil, generado a partir de la matriz | `templates/core/custody.html` |
| Documentos | «Documentos legales del concello»: política de privacidad completa, versionada | módulo `legal` |

## Primera capa: solicitud de la app (datos que da la persona, art. 13)

> **Qué hacemos con estos datos**
> - **Responsable:** [Concello de X].
> - **Para qué:** comprobar el empadronamiento y enviarte la app. Contrastamos solo el DNI/NIE y la fecha
>   de nacimiento con un resumen criptográfico (HMAC) del padrón que carga el ayuntamiento: ni el padrón ni
>   tu DNI se guardan en claro, y el nombre no se usa para comprobar.
> - **Base:** misión de interés público (art. 6.1.e RGPD): servicio municipal de deportes y tarifa de
>   vecindario de la ordenanza.
> - **Cuánto tiempo:** el DNI/NIE, la fecha y la dirección se borran en cuanto se resuelve la solicitud (al
>   momento si figuras). El resto de la solicitud, a los 12 meses.
> - **Si no figuras:** una persona del ayuntamiento revisa la solicitud y te responde por correo.
> - **Derechos:** acceso, rectificación, supresión y oposición desde tu cuenta o en el ayuntamiento.
>   [Más información]

## Segunda capa: página «Privacidad»

> **Responsable:** Ayuntamiento de [X]. [correo de contacto]
>
> **Finalidad:** gestionar las reservas, el acceso y el mantenimiento de las instalaciones deportivas
> municipales y las inscripciones en actividades.
>
> **Base jurídica:** ejercicio de poderes públicos y prestación del servicio público de deportes
> (art. 6.1.e RGPD; Ley 7/1985 de bases de régimen local, art. 25.2.l). El consentimiento solo se usa
> para lo que es opcional (imagen, registro de esfuerzo).
>
> **Qué datos:** correo, nombre para mostrar, teléfono opcional y año de nacimiento opcional (para
> tarifas). El DNI/NIE solo se usa para comprobar el empadronamiento y se borra al resolver la solicitud;
> no hay contraseñas. De los menores, solo nombre y año de nacimiento, con consentimiento de la persona
> responsable.
>
> **Datos que no salen de tu dispositivo:** los de la página «Mi salud» (edad, peso, actividad)
> se guardan solo en el navegador.
>
> **Estadísticas:** los indicadores públicos y el observatorio solo muestran datos agregados de grupos de
> al menos [10] personas.
>
> **Conservación:** las reservas, 2 años después de usarlas; después quedan sin tu nombre para la
> contabilidad y las estadísticas. Al eliminar la cuenta quedan anonimizadas al momento. Los demás
> plazos están en la política de conservación del concello.
>
> **Destinatarios:** ninguno fuera del concello, salvo quien aloja Eira por encargo del concello (contrato
> del art. 28 RGPD). Tus datos no salen de la Unión Europea, salvo si vinculas Telegram para
> recibir avisos. El mapa de las instalaciones carga imágenes de un servidor de mapas, que ve la dirección IP
> de tu navegador.
>
> **Persona delegada de protección de datos:** [contacto del DPD] (aparece si el concello lo rellena en
> «Configuración»).
>
> **Tus derechos:** acceso, rectificación, supresión, portabilidad, oposición y limitación.
> Puedes descargar y borrar tus datos desde «Mi cuenta». También puedes reclamar ante la Agencia
> Española de Protección de Datos.

**Lo que debe añadir el concello** en su «texto de privacidad» (Configuración), porque Eira no lo
puede saber: la dirección postal del responsable, el contacto del DPD si no lo rellena en el campo propio, los
encargados concretos (diputación o empresa) y el enlace al inventario de actividades que publica
el concello (art. 31.2 LOPDGDD).

## Primera capa: consentimientos

| Dónde | Texto que muestra Eira |
|---|---|
| Salud (art. 9.2.a) | «Consiento expresamente que el ayuntamiento guarde mi peso, edad y minutos de actividad solo para calcular mis recomendaciones. Nadie del personal puede verlos y no se usan para estadísticas. Puedo borrarlos cuando quiera.» |
| Imagen (personas adultas) | «El ayuntamiento puede usar fotos donde aparezca (actividades y comunicaciones)» |
| Menores (art. 7 LOPDGDD) | «Autorizo el tratamiento de los datos necesarios para su inscripción en actividades» (obligatorio) · «Autorizo el uso de su imagen en comunicaciones municipales» · «Autorizo registrar el esfuerzo percibido y las pruebas físicas de la actividad» · con 14 o más: «Tiene 14 años o más y está de acuerdo con estos consentimientos» |
| Avisos informativos | Consentimiento en las preferencias de avisos, revocable por categoría y canal |
| Partidas abiertas | Consentimiento al publicar y al unirse para que se vea el nombre de pila y la inicial |

Los textos completos de los consentimientos y los documentos legales modelo están en
[../../textos-modelo.md](../../textos-modelo.md) y [../../../legal/modelos/](../../../legal/modelos/README.md).

## Datos que no proceden de la persona (art. 14)

| Dato | De dónde procede | Cómo se informa |
|---|---|---|
| Empadronado/a sí o no, y parroquia | Padrón del concello (solo el HMAC) | Primera capa de la solicitud y página «Privacidad» |
| Apellidos de los menores inscritos | El concello (hoja de inscripción) | Documento de inscripción del concello |
| Nombre y puesto del personal en las alertas | El concello | Información al personal (no es vecindad) |

El art. 14.3.a pide informar como máximo en un mes; en Eira estos datos solo aparecen al usar el servicio,
donde ya se muestra la primera capa.
