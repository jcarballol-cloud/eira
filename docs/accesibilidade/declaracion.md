<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Declaración de accesibilidade

**Versión en castelán:** [máis abaixo](#declaracion-de-accesibilidad).

Esta é a copia en texto da declaración que Eira publica na aplicación (Real Decreto 1112/2018, art.
15), seguindo a estrutura do modelo do Observatorio de Accesibilidade Web:

- **`/accesibilidade/`**: declaración das páginas comúns (portada, axuda, preferencias e conta), con
  ligazón á de cada concello.
- **`/c/<concello>/accesibilidade/`**: declaración de cada concello, coa súa canle de comunicación e
  reclamación.

Hai ligazón a «Accesibilidade» no pé de todas as pantallas: web pública, escritorio do concello, app
móbil e tableta. Compróbao `apps/tenants/tests/test_accessibility_statement.py`.

**O que configura cada concello** (Xestión → Configuración → «Declaración de accesibilidade»): a
unidade responsable, o correo e o teléfono (se se deixan baleiros, úsanse os de contacto do concello),
a ligazón para presentar reclamacións (sede electrónica ou rexistro), a data da última revisión e un
texto propio opcional. O resto vén de Eira e o concello debe revisalo antes de publicalo.

---

## Texto da declaración

O Concello de *[nome]* comprométese a facer accesible o seu sitio web e a súa aplicación de Eira, de
conformidade co Real Decreto 1112/2018, do 7 de setembro, sobre accesibilidade dos sitios web e
aplicacións para dispositivos móbiles do sector público. Esta declaración aplícase ás páxinas e á
aplicación de Eira do concello.

### Situación de cumprimento

Este sitio web e esta aplicación son **parcialmente conformes** co RD 1112/2018 debido ás excepcións e
á falta de conformidade dos aspectos que se indican a continuación. O obxectivo é o nivel AA das WCAG
2.1 (norma UNE-EN 301 549).

### Contido non accesible

**Falta de conformidade co RD 1112/2018:**

- Non se fixeron aínda probas con lectores de pantalla reais (NVDA, JAWS, TalkBack ou VoiceOver) nin
  con persoas usuarias con discapacidade. Ata facelas, a conformidade só se pode declarar parcial.
- As fotos que a veciñanza sube cos avisos de avaría poden non ter un texto alternativo descritivo.

**Contido que non entra no ámbito da lexislación aplicable:**

- Mapas en liña: o mapa de instalacións é un complemento visual. Toda a súa información está tamén na
  lista accesible e nos filtros.

### Preparación desta declaración

Esta declaración preparouse o 11 de novembro de 2026.

Método: **autoavaliación**. Probas automáticas con axe-core (regras WCAG 2.0 e 2.1, niveis A e AA) en
**175 pantallas × 3 tamaños** (móbil, tableta e escritorio) e en 81 pantallas en tema escuro, sen
violacións (`tests/e2e/test_accessibility.py` e `test_dark_theme.py`), e **revisión manual co
teclado**. Detalle en [criterios.md](criterios.md) e [informe-probas.md](informe-probas.md).

Última revisión da declaración: a que indique o concello (por defecto, a data anterior).

### Observacións e datos de contacto

Podes facer comunicacións sobre requisitos de accesibilidade (artigo 10.2.a do RD 1112/2018): informar
dun posible incumprimento, transmitir outras dificultades de acceso ao contido ou formular calquera
consulta ou suxestión de mellora.

Tamén podes presentar:

- unha queixa relativa ao cumprimento dos requisitos do RD 1112/2018;
- unha solicitude de información accesible sobre contidos excluídos do ámbito de aplicación do RD
  1112/2018 ou exentos por carga desproporcionada. Na solicitude hai que concretar os feitos, as
  razóns e a petición.

Canle: *[unidade responsable, correo e teléfono configurados polo concello]*.

### Procedemento de aplicación

Se, despois dunha solicitude de información accesible ou dunha queixa, esta fose desestimada, non
estiveses de acordo coa decisión ou a resposta non cumprise os requisitos do artigo 12.5 do RD
1112/2018, podes iniciar unha reclamación. Tamén podes facelo se pasan vinte días hábiles sen
resposta. A reclamación preséntase en *[ligazón configurada polo concello ou, se non hai, o rexistro do
concello]*.

---

<a id="declaracion-de-accesibilidad"></a>

# Declaración de accesibilidad (castellano)

Copia en texto de la declaración que Eira publica en la aplicación (Real Decreto 1112/2018, art. 15),
con la estructura del modelo del Observatorio de Accesibilidad Web: `/accesibilidade/` para las
páginas comunes y `/c/<concello>/accesibilidade/` para cada concello. Hay enlace en el pie de todas
las pantallas. Cada concello configura en «Configuración → Declaración de accesibilidad» la unidad
responsable, el correo, el teléfono, el enlace para reclamaciones, la fecha de revisión y un texto
propio opcional.

**Situación de cumplimiento.** Este sitio web y esta aplicación son **parcialmente conformes** con el
RD 1112/2018 debido a las excepciones y a la falta de conformidad de los aspectos que se indican a
continuación. El objetivo es el nivel AA de las WCAG 2.1 (norma UNE-EN 301 549).

**Contenido no accesible.** Falta de conformidad: aún no se han hecho pruebas con lectores de pantalla
reales (NVDA, JAWS, TalkBack o VoiceOver) ni con personas usuarias con discapacidad; las fotos que sube el
vecindario con los avisos de avería pueden no tener texto alternativo descriptivo. Fuera del ámbito
de la legislación aplicable: el mapa en línea es un complemento visual y toda su información está en
la lista accesible y en los filtros.

**Preparación de esta declaración.** Preparada el 11 de noviembre de 2026. Método: **autoevaluación**
con axe-core (reglas WCAG 2.0 y 2.1, niveles A y AA) en **175 pantallas × 3 tamaños** y en 81 en
tema oscuro, sin violaciones, y **revisión manual con el teclado**.

**Observaciones y datos de contacto.** Puedes hacer comunicaciones sobre requisitos de accesibilidad
(artículo 10.2.a del RD 1112/2018), presentar una queja relativa al cumplimiento del RD 1112/2018 o una
solicitud de información accesible, por el canal que configure el concello.

**Procedimiento de aplicación.** Si la solicitud o la queja se desestima, no estás de acuerdo con la
decisión o la respuesta no cumple el artículo 12.5 del RD 1112/2018, puedes presentar una reclamación;
también si pasan veinte días hábiles sin respuesta. Se presenta en el enlace que configure el concello
o, si no lo hay, en su registro.
