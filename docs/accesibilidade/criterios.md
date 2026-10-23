# Criterios de accesibilidade (WCAG 2.1 AA · EN 301 549 · RD 1112/2018)

## Principios de deseño

- **HTML semántico renderizado no servidor**: funciona sen JavaScript (agás o modo tableta e a cola
  sen conexión, que son melloras). HTMX só para cambios parciais, con anuncios `aria-live`.
- **A lista é a vista principal**; o mapa é un complemento e repite a mesma información.
- **Nunca só cor**: cada estado da grella leva símbolo (○ ★ ◔ ● ✕ ✓) e texto para lectores de pantalla.
- **Alvos táctiles ≥ 44 px**; no modo tableta, ≥ 56 px e nomes grandes.
- **Preferencias de lectura** no servidor (cookie, sen JS): texto grande, alto contraste e movemento
  reducido; ademais respéctanse `prefers-reduced-motion`, `prefers-contrast` e `forced-colors`.

## Criterios e como se cumpren

| Criterio WCAG 2.1 | Implementación |
|---|---|
| 1.1.1 Contido non textual | Iconas decorativas con `aria-hidden`; fotos de instalacións con texto alternativo obrigatorio no alta; gráficos SVG con `role="img"`, `<title>` e `<desc>` |
| 1.3.1 Información e relacións | Táboas con `caption` e `scope`; formularios con `label`, `fieldset/legend` para grupos; estrutura de encabezados |
| 1.3.5 Propósito dos campos | `autocomplete="email"`, `one-time-code`, `tel` |
| 1.4.1 Uso da cor | Símbolos e texto nos estados; badges con texto |
| 1.4.3 Contraste | Paleta comprobada (≥ 4,5:1 en texto); verificado con axe |
| 1.4.4 / 1.4.10 Redimensionar e reflow | Unidades rem, deseño fluído a 320 px; a grella semanal convértese nunha lista por días en móbil |
| 1.4.11 Contraste non textual | Bordes de campos #8A9590 sobre branco (3,3:1); foco con dobre anel |
| 1.4.13 Contido en hover | Sen tooltips dependentes de hover |
| 2.1.1 Teclado | Todo operable con teclado; regións desprazables con `tabindex="0"`; o menú pecha con Escape |
| 2.4.1 Saltar bloques | Ligazón «Saltar ao contido» (primeiro elemento enfocable; test E2E) |
| 2.4.2 Título | `<title>` por páxina co nome do concello |
| 2.4.3 / 2.4.7 Orde e foco visible | Orde DOM lóxica; `:focus-visible` con anel millo + granito |
| 2.5.5 Tamaño do alvo (AAA, aplicado) | Botóns ≥ 44 px |
| 3.1.1 / 3.1.2 Idioma | `lang` correcto (gl/es) e `lang` nos botóns de idioma |
| 3.3.1 / 3.3.3 Identificación de erros | Erros asociados con `aria-describedby`, `aria-invalid`, resumo con foco |
| 3.3.2 Etiquetas | Toda entrada con etiqueta visible; obrigatorios marcados |
| 4.1.2 Nome, función, valor | Botóns de asistencia con `aria-pressed`; pasos con `aria-current="step"` |
| 4.1.3 Mensaxes de estado | Rexión `aria-live` global; mensaxes con `role="status"` |

## Ferramentas

- `tests/e2e/test_accessibility.py`: axe-core (reglas `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`) en
  53 páxinas × móbil e escritorio con todos os perfís de demostración.
- Test que impide `<script>` e `style=` en liña (compatibilidade con CSP e mantemento).
