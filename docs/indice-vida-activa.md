<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Índice de vida activa por instalación (v5)

Unha cifra de **0 a 100** que resume canto e como se usa unha instalación. Vese na ficha pública da instalación (icona e cifra), no panel do día do concello e na comparativa da deputación.

**Engádese ao observatorio, non o substitúe.** O observatorio segue igual: esforzo, asistencia, probas físicas e referencia OMS. O índice só reutiliza datos que Eira xa ten; non recolle nada novo.

Código: `apps/analytics/vitality.py`. Probas: `apps/analytics/tests/test_vitality.py`.

## Compoñentes

Cada compoñente vai de 0 a 100. Período: as últimas **8 semanas** (a satisfacción, 90 días).

| Compoñente | De onde sae | Cálculo | Datos de persoas? |
|---|---|---|---|
| **Ocupación real** | Reservas co uso rexistrado (entrada por QR, código, apertura ou chave) | usos ÷ prazas-franxa ofertadas (descontando peches). Un **60 %** de uso real xa puntúa 100: `min(100, uso% × 100 / 60)` | Si (n = usos) |
| **Diversidade de idades** | Ano de nacemento das contas que usaron a instalación | Persoas distintas repartidas en 5 franxas (0–17, 18–34, 35–54, 55–64, 65+). Entropía de Shannon normalizada: `100 × H / ln 5`. Todas nunha franxa = 0; repartidas por igual = 100 | Si (n = persoas distintas) |
| **Satisfacción** | «Que tal foi?» | Media con ben = 100, regular = 50, mal = 0 | Si (n = valoracións) |
| **Accesibilidade física** | Ficha da instalación | Elementos declarados ÷ 7 × 100 | Non |
| **Mantemento ao día** | Última orde de mantemento pechada («Última supervisión») | ≤ 30 días = 100; baixa en liña recta ata 0 aos 180 días; sen ningunha = 0. −20 se hai ordes atrasadas | Non |

## Pesos (configurables)

Por defecto:

| Ocupación | Diversidade | Satisfacción | Accesibilidade | Mantemento |
|---|---|---|---|---|
| 30 | 15 | 25 | 15 | 15 |

Cada concello pódeos cambiar en **Configuración → Índice de vida activa** (0–100, pesos relativos: non teñen que sumar 100). Un peso 0 quita o compoñente.

**Índice** = media ponderada dos compoñentes con datos: `Σ valor × peso / Σ peso`.

## Umbral e «sen datos suficientes»

- Os compoñentes con datos de persoas (ocupación, diversidade e satisfacción) só se calculan con **n ≥ 10**, o mesmo umbral ca o observatorio. Por debaixo, ese compoñente queda «sen datos suficientes» e non se mostra ningunha cifra del.
- Se hai **menos de dous** compoñentes de persoas con datos, o índice enteiro mostra **«sen datos suficientes»**. Así unha instalación case sen uso non recibe unha nota que dependa só da accesibilidade e do mantemento.
- Os compoñentes sen datos non contan: o resto repártese o peso.
- Nunca se mostra quen usou a instalación: a diversidade só conta persoas por franxa de idade e descarta a lista.

## Icona

- **≥ 67:** alta (icona chea) · **40–66:** media · **< 40:** baixa · sen cifra: «sen datos suficientes».
- A cor nunca é a única pista: sempre vai a cifra e o texto («Índice de vida activa: 72 de 100»).

## Limitacións coñecidas

- A ocupación real depende de que se rexistre a entrada. Nas instalacións abertas (nivel 0) o QR é voluntario, así que a cifra pode quedar por debaixo do uso real.
- A diversidade só ve as persoas con conta e ano de nacemento; os menores inscritos polas familias non contan aquí (contan no observatorio).
