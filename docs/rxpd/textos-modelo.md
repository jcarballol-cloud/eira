<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Textos modelo

Textos para que cada concello os revise co seu DPD. As partes entre `[corchetes]` son do concello.

## 1. Información por capas (alta e solicitude da app)

**Primeira capa** (a que se ve ao pedir a app; está en `templates/app/request.html`):
- **Responsable:** [Concello de X].
- **Para que:** comprobar o empadroamento e enviarche a app. O padrón non se copia: só se garda se figuras ou non.
- **Base:** misión de interese público (servizo municipal de deportes).
- **Canto tempo:** a solicitude bórrase aos 12 meses.
- **Dereitos:** acceso, rectificación, supresión e oposición desde a túa conta ou no concello. Máis información en `/c/[slug]/privacidade/`.

**Segunda capa:** a páxina de privacidade do concello (campo «texto de privacidade»), co rexistro de actividades (`rat.md`), o DPD e o dereito a reclamar ante a AEPD.

## 2. Consentimento para menores
> Como [nai/pai/titor/a] de [nome], autorizo:
> ☐ o tratamento dos datos necesarios para a súa inscrición (obrigatorio para inscribir);
> ☐ o uso da súa imaxe en actividades e comunicacións municipais;
> ☐ o rexistro do esforzo percibido e das probas físicas da actividade.
> Podo retirar cada autorización en calquera momento desde «Unidade familiar», sen que afecte ao tratamento anterior.

Con 14 anos ou máis: «[Nome] está de acordo con estes consentimentos» (art. 7 LOPDGDD).

**En papel** (persoas apuntadas polo monitor na pista): a mesma folla asinada. O concello márcaa ao validar a inscrición e queda rexistrada como `text_version = "papel"`.

## 3. Imaxe (persoas adultas)
> ☐ O concello pode usar fotos onde apareza, tomadas nas actividades, para comunicacións municipais. Podo retiralo no centro de privacidade.

## 4. Saúde (art. 9 RXPD)
> As túas recomendacións calcúlanse no teu dispositivo. Se queres velas tamén noutros dispositivos, podes gardar o teu peso e a túa idade na conta.
> ☐ Consinto expresamente que [Concello de X] garde estes datos de saúde **só** para calcular as miñas recomendacións. Ninguén do persoal pode velos e non se usan para estatísticas. Podo borralos cando queira.

## 5. Cookies
> Só usamos cookies técnicas, necesarias para que a web funcione (sesión, seguridade dos formularios, idioma e preferencias de lectura). Non hai cookies de seguimento nin de publicidade, e por iso non pedimos aceptalas.
