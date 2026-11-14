<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Información por capas (arts. 13 e 14 RXPD; art. 11 LOPDGDD)

> **MODELO DE EXEMPLO — require revisión do DPD e dos servizos xurídicos do concello.**

O art. 11 LOPDGDD permite dar primeiro unha **información básica** (responsable, finalidade e como
exercer os dereitos) e un medio sinxelo para ver o resto. Estes textos **son os que mostra Eira**:
se o concello os cambia na app, debe cambialos tamén aquí. As partes entre `[corchetes]` son do
concello.

## Onde aparece cada capa en Eira

| Capa | Onde se ve | Plantilla |
|---|---|---|
| Primeira (ao pedir a app) | «Que facemos con estes datos», despregable no formulario | `templates/app/request.html` |
| Primeira (ao dar un consentimento) | Texto xunto a cada casilla (imaxe, saúde, menores, partidas abertas) | `apps/accounts/forms.py`, `templates/core/health.html`, `templates/bookings/game_publish.html` |
| Segunda | Páxina «Privacidade» do concello (`/c/[concello]/privacidade/`) | `templates/core/privacy.html` |
| Terceira | «Quen custodia os teus datos» (`/c/[concello]/privacidade/datos/`): que dato ve cada perfil, xerado da matriz | `templates/core/custody.html` |
| Documentos | «Documentos legais do concello»: política de privacidade completa, versionada | módulo `legal` |

## Primeira capa: solicitude da app (datos que dá a persoa, art. 13)

> **Que facemos con estes datos**
> - **Responsable:** [Concello de X].
> - **Para que:** comprobar o empadroamento e enviarche a app. Contrastamos só o DNI/NIE e a data
>   de nacemento cun resumo criptográfico (HMAC) do padrón que carga o concello: nin o padrón nin o
>   teu DNI se gardan en claro, e o nome non se usa para comprobar.
> - **Base:** misión de interese público (art. 6.1.e RXPD): servizo municipal de deportes e tarifa de
>   veciñanza da ordenanza.
> - **Canto tempo:** o DNI/NIE, a data e o enderezo bórranse en canto se resolve a solicitude (ao
>   momento se figuras). O resto da solicitude, aos 12 meses.
> - **Se non figuras:** unha persoa do concello revisa a solicitude e respóndeche por correo.
> - **Dereitos:** acceso, rectificación, supresión e oposición desde a túa conta ou no concello.
>   [Máis información]

## Segunda capa: páxina «Privacidade»

> **Responsable:** Concello de [X]. [correo de contacto]
>
> **Finalidade:** xestionar as reservas, o acceso e o mantemento das instalacións deportivas
> municipais e as inscricións en actividades.
>
> **Base xurídica:** exercicio de poderes públicos e prestación do servizo público de deportes
> (art. 6.1.e RXPD; Lei 7/1985 de bases de réxime local, art. 25.2.l). O consentimento só se usa
> para o que é opcional (imaxe, rexistro de esforzo).
>
> **Que datos:** correo, nome para mostrar, teléfono opcional e ano de nacemento opcional (para
> tarifas). O DNI/NIE só se usa para comprobar o empadroamento e bórrase ao resolver a solicitude;
> non hai contrasinais. Dos menores, só nome e ano de nacemento, con consentimento da persoa
> responsable.
>
> **Datos que non saen do teu dispositivo:** os da páxina «A miña saúde» (idade, peso, actividade)
> gárdanse só no navegador.
>
> **Estatísticas:** os indicadores públicos e o observatorio só mostran datos agregados de grupos de
> polo menos [10] persoas.
>
> **Conservación:** as reservas, 2 anos despois de usalas; despois quedan sen o teu nome para a
> contabilidade e as estatísticas. Ao eliminar a conta quedan anonimizadas ao momento. Os demais
> prazos están na política de conservación do concello.
>
> **Destinatarios:** ningún fóra do concello, agás quen aloxa Eira por encargo do concello (contrato
> do art. 28 RXPD). Os teus datos non saen da Unión Europea, salvo se vinculas Telegram para
> recibir avisos. O mapa das instalacións só se carga se pulsas «Ver mapa»; entón o servidor de
> mapas (OpenStreetMap por defecto) ve o enderezo IP do teu navegador.
>
> **Persoa delegada de protección de datos:** [contacto do DPD] (sae se o concello o enche en
> «Configuración»).
>
> **Os teus dereitos:** acceso, rectificación, supresión, portabilidade, oposición e limitación.
> Podes descargar e borrar os teus datos desde «A miña conta». Tamén podes reclamar ante a Axencia
> Española de Protección de Datos.

**O que debe engadir o concello** no seu «texto de privacidade» (Configuración), porque Eira non o
pode saber: o enderezo postal do responsable, o contacto do DPD se non o enche no campo propio, os
encargados concretos (deputación ou empresa) e a ligazón ao inventario de actividades que publica
o concello (art. 31.2 LOPDGDD).

## Primeira capa: consentimentos

| Onde | Texto que mostra Eira |
|---|---|
| Saúde (art. 9.2.a) | «Consinto expresamente que o concello garde o meu peso, idade e minutos de actividade só para calcular as miñas recomendacións. Ninguén do persoal pode velos e non se usan para estatísticas. Podo borralos cando queira.» |
| Imaxe (persoas adultas) | «O concello pode usar fotos onde apareza (actividades e comunicacións)» |
| Menores (art. 7 LOPDGDD) | «Autorizo o tratamento dos datos necesarios para a súa inscrición en actividades» (obrigatorio) · «Autorizo o uso da súa imaxe en comunicacións municipais» · «Autorizo rexistrar o esforzo percibido e as probas físicas da actividade» · con 14 ou máis: «Ten 14 anos ou máis e está de acordo con estes consentimentos» |
| Avisos informativos | Consentimento nas preferencias de avisos, revogable por categoría e canle |
| Partidas abertas | Consentimento ao publicar e ao unirse para que se vexa o nome de pila e a inicial |

Os textos completos dos consentimentos e os documentos legais modelo están en
[../textos-modelo.md](../textos-modelo.md) e [../../legal/modelos/](../../legal/modelos/README.md).

## Datos que non veñen da persoa (art. 14)

| Dato | De onde vén | Como se informa |
|---|---|---|
| Empadroado/a si ou non, e parroquia | Padrón do concello (só o HMAC) | Primeira capa da solicitude e páxina «Privacidade» |
| Apelidos dos menores inscritos | O concello (folla de inscrición) | Documento de inscrición do concello |
| Nome e posto do persoal nas alertas | O concello | Información ao persoal (non é veciñanza) |

O art. 14.3.a pide informar como máximo nun mes; en Eira estes datos só aparecen ao usar o servizo,
onde xa se mostra a primeira capa.
