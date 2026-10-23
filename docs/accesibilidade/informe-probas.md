# Informe de probas de accesibilidade

**Data:** 2026-10-23 · **Versión:** 0.1.0 (prototipo) · **Ferramenta:** axe-core 4.12 vía
axe-playwright-python, Chromium (Playwright 1.64).

## Resultado automático

| Ámbito | Páxinas | Viewports | Violacións A/AA |
|---|---|---|---|
| Pública (sen sesión) | 13 | 390×844, 1280×900 | **0** |
| Veciña (Uxía) | 12 | 390×844, 1280×900 | **0** |
| Administración do concello | 20 | 390×844, 1280×900 | **0** |
| Operario | 2 | 390×844, 1280×900 | **0** |
| Monitora (modo tableta) | 4 | 390×844, 1280×900 | **0** |
| Deputación | 2 | 390×844, 1280×900 | **0** |
| **Total** | **53 distintas (106 análises)** | | **0** |

Comando: `python tools/tasks.py e2e` (ou `make e2e`).

### Problemas atopados e corrixidos durante a sesión

1. Contraste insuficiente nas franxas pasadas da grella (#6B7174 sobre #F1F1EE) → #505759.
2. Contraste do nivel 3 do mapa de calor (branco sobre #4E8F6E, 3,5:1) → #3A7458.
3. Días doutro mes no calendario con `opacity` (baixaba o contraste) → fondo gris sen opacidade.
4. Táboas con desprazamento horizontal non accesibles por teclado → `tabindex="0"` nos contedores.

## Probas funcionais automáticas (E2E)

- Ligazón de salto: primeiro `Tab` enfoca «Saltar ao contido» e `Enter` leva o foco a `<main>`.
- `lang="gl"` por defecto e `lang="es"` ao cambiar de idioma.
- Navegación de semanas con HTMX anuncia «Semana do …» na rexión `aria-live`.

## Pendente de verificar manualmente (non verificado)

- Lectores de pantalla reais (NVDA + Firefox, VoiceOver iOS, TalkBack).
- Zoom ao 200 % e 400 % en todas as páxinas (o deseño é fluído, pero non se revisou unha a unha).
- O mapa Leaflet con teclado (a lista equivalente si é accesible).
- Gráficos SVG en móbil: o texto escala e pode quedar pequeno; a táboa alternativa está dispoñible.
- Proba con persoas usuarias (maiores, baixa visión) antes da entrega.
