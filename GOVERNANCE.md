<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Goberno do proxecto Eira

**Versión en castelán:** [máis abaixo](#gobierno-del-proyecto-eira).

Eira é software libre (EUPL-1.2) pensado para que o usen, o paguen e o melloren as administracións
públicas, sen depender dunha única empresa. Este documento explica quen decide, como se aceptan
contribucións e como se fai a folla de ruta.

## 1. Quen mantén o proxecto

- **Agora (prototipo, candidatura ao I Certame GOBTEC 2026):** o **Equipo Eira** é o equipo mantedor.
  Revisa e acepta os cambios, publica as versións e atende os avisos de seguridade
  ([SECURITY.md](SECURITY.md)).
- **Cando haxa concellos usándoo:** proponse un **comité de persoas usuarias** cunha persoa por cada
  entidade que o despregue (concello, deputación ou mancomunidade). O comité non escribe código:
  prioriza a folla de ruta e decide as cuestións que afectan ao servizo público (accesibilidade,
  protección de datos, idiomas, licenza).
- **Persoas mantedoras:** calquera persoa ou empresa con contribucións continuadas e de calidade pode
  ser proposta como mantedora. Decide o equipo mantedor por consenso e publícao no repositorio.
- **Obxectivo a medio prazo:** que o proxecto o custodie unha entidade pública ou sen ánimo de lucro
  (deputación, consorcio, asociación de software libre), para que ningunha empresa sexa
  imprescindible. Mentres non exista, o nome «Eira» e o repositorio principal quedan no Equipo Eira.

## 2. Como se decide

- **Consenso perezoso:** unha proposta sen obxeccións en 7 días naturais considérase aceptada.
- **Cambios grandes** (novos módulos, cambios no modelo de datos, novas dependencias, cambios de
  licenza ou de política de datos): abrir antes unha incidencia cunha proposta escrita. Se non hai
  consenso, decide o equipo mantedor e motívao por escrito.
- **Decisións técnicas e de deseño:** quedan en [docs/DECISIONS.md](docs/DECISIONS.md), co motivo.
- **Principios que non se negocian:** software libre; accesibilidade WCAG 2.1 AA; galego como idioma
  por defecto e castelán completo; datos persoais mínimos; integracións externas sempre detrás dun
  adaptador con implementación simulada; ningunha dependencia que obrigue a pagar a un provedor.

## 3. Contribucións de concellos e empresas

Todas as contribucións seguen [CONTRIBUTING.md](CONTRIBUTING.md) e o
[código de conduta](CODE_OF_CONDUCT.md). Ademais:

| Quen | Como | Que se pide |
|---|---|---|
| **Concello, deputación ou mancomunidade** | Incidencias (erros, necesidades), propostas de mellora, textos legais e de uso, probas con persoas usuarias reais | Que as necesidades se describan como problema («a veciñanza non sabe se…»), non como solución pechada. Nada de datos persoais nas incidencias |
| **Empresa** (desenvolvemento, implantación, mantemento) | Pull requests; adaptadores para servizos reais (TPV, pechaduras, padrón, carné…) | Código baixo EUPL-1.2 sen excepcións; tests, E2E e axe en verde; sen funcións que só funcionen cun provedor concreto; o adaptador simulado sempre ao día |
| **Persoa voluntaria** | Calquera das anteriores; traducións; revisión de accesibilidade | O mesmo |

- **Licenza de entrada = licenza de saída:** quen contribúe acepta publicar a súa achega baixo
  EUPL-1.2. Non hai CLA nin cesión de dereitos; recoméndase asinar cada commit con
  `Signed-off-by` (Developer Certificate of Origin).
- **Empresas:** poden ofrecer servizos de implantación, aloxamento, formación e mantemento de Eira sen
  permiso de ninguén. O que non se acepta no repositorio principal: código pechado, telemetría,
  dependencias de pago obrigatorias, ou funcións que só se activen cun contrato.
- **Contratación pública:** os pregos que inclúan desenvolvementos sobre Eira deberían esixir que o
  código se entregue ao repositorio público baixo EUPL-1.2 (recomendación do Esquema Nacional de
  Interoperabilidade e do art. 157 da Lei 40/2015 sobre reutilización).
- **Revisión:** polo menos unha persoa mantedora distinta da autora. Os cambios en seguridade, datos
  persoais ou accesibilidade precisan unha revisión específica dese aspecto.

## 4. Folla de ruta pública

- A folla de ruta está en [docs/PLAN_V2.md](docs/PLAN_V2.md) e móvese ás incidencias do repositorio
  cando se publique, cunha etiqueta por versión.
- **Como entra algo:** proposta nunha incidencia → valoración do comité de persoas usuarias (cando
  exista) → prioridade na seguinte versión. As necesidades de varias entidades teñen preferencia
  sobre as dunha soa.
- **Versións:** etiquetas `vX.Y` con notas en galego e castelán. Unha versión só se publica con tests,
  E2E e axe en verde e coa demo funcionando.
- **Seguridade:** as correccións de seguridade publícanse canto antes, aínda fóra do calendario.

## 5. Cambios neste documento

Este documento cámbiase coma o código (pull request) e precisa o acordo do equipo mantedor e, cando
exista, do comité de persoas usuarias.

---

<a id="gobierno-del-proyecto-eira"></a>

# Gobierno del proyecto Eira

Eira es software libre (EUPL-1.2) pensado para que lo usen, lo paguen y lo mejoren las
administraciones públicas, sin depender de una única empresa.

## 1. Quién mantiene el proyecto

- **Ahora (prototipo, candidatura al I Certamen GOBTEC 2026):** el **Equipo Eira** es el equipo
  mantenedor: revisa y acepta los cambios, publica las versiones y atiende los avisos de seguridad
  ([SECURITY.md](SECURITY.md)).
- **Cuando haya ayuntamientos usándolo:** se propone un **comité de personas usuarias** con una persona
  por cada entidad que lo despliegue (ayuntamiento, diputación o mancomunidad). Prioriza la hoja de
  ruta y decide las cuestiones que afectan al servicio público (accesibilidad, protección de datos,
  idiomas, licencia).
- **Personas mantenedoras:** cualquier persona o empresa con contribuciones continuadas puede ser
  propuesta; decide el equipo mantenedor por consenso.
- **Objetivo a medio plazo:** que custodie el proyecto una entidad pública o sin ánimo de lucro, para
  que ninguna empresa sea imprescindible.

## 2. Cómo se decide

- **Consenso perezoso:** una propuesta sin objeciones en 7 días naturales se considera aceptada.
- **Cambios grandes** (módulos, modelo de datos, dependencias, licencia o política de datos): primero
  una incidencia con propuesta escrita. Sin consenso, decide el equipo mantenedor de forma motivada.
- Las decisiones quedan en [docs/DECISIONS.md](docs/DECISIONS.md).
- **Principios no negociables:** software libre; WCAG 2.1 AA; gallego por defecto y castellano
  completo; datos personales mínimos; integraciones detrás de un adaptador con simulación; ninguna
  dependencia que obligue a pagar a un proveedor.

## 3. Contribuciones de ayuntamientos y empresas

- **Ayuntamientos, diputaciones y mancomunidades:** incidencias, propuestas, textos legales y pruebas
  con personas usuarias reales. Sin datos personales en las incidencias.
- **Empresas:** pull requests y adaptadores para servicios reales, siempre bajo EUPL-1.2, con tests,
  E2E y axe en verde, sin funciones atadas a un proveedor y con el adaptador simulado al día. Pueden
  ofrecer implantación, alojamiento, formación y mantenimiento sin pedir permiso. No se acepta en el
  repositorio principal código cerrado, telemetría, dependencias de pago obligatorias ni funciones que
  solo se activen con un contrato.
- **Licencia de entrada = licencia de salida (EUPL-1.2)**; sin CLA. Se recomienda `Signed-off-by` (DCO).
- **Contratación pública:** los pliegos deberían exigir que el código se entregue al repositorio
  público bajo EUPL-1.2 (art. 157 de la Ley 40/2015 sobre reutilización).
- **Revisión:** al menos una persona mantenedora distinta de la autora; revisión específica en
  seguridad, datos personales y accesibilidad.

## 4. Hoja de ruta pública

- En [docs/PLAN_V2.md](docs/PLAN_V2.md); pasará a las incidencias del repositorio cuando se publique.
- Entrada: propuesta → valoración del comité de personas usuarias → prioridad en la siguiente versión.
  Las necesidades compartidas por varias entidades tienen preferencia.
- Versiones `vX.Y` con notas en gallego y castellano, solo con tests, E2E y axe en verde.
- Las correcciones de seguridad se publican cuanto antes.

## 5. Cambios en este documento

Se cambia como el código (pull request), con el acuerdo del equipo mantenedor y, cuando exista, del
comité de personas usuarias.
