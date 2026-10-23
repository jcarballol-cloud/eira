# Recomendacións de saúde (páxina «A miña saúde»)

**Carácter:** educativo e orientativo, **non clínico**. Móstrase sempre o aviso «Información
educativa e xeral, non é consello clínico». Os datos (idade, peso, minutos de actividade, duración da
sesión) quedan só no navegador.

## Fórmulas e fontes

| Consello | Regra en Eira | Fonte |
|---|---|---|
| Hidratación antes do exercicio | 5–7 ml por kg de peso, polo menos 4 h antes (redondeado a 50 ml) | American College of Sports Medicine. *Exercise and Fluid Replacement* (Position Stand). Med Sci Sports Exerc. 2007;39(2):377–390 |
| Hidratación durante | Cualitativo: «bebe pequenos grolos a miúdo; en sesións de máis de 60 min ou con calor, repón tamén sales». Sen cifras, porque dependen da suor individual | ACSM 2007 (recomenda individualizar e evitar perdas > 2 % do peso) |
| Auga diaria total | Mencionada como contexto (2,0 l/día mulleres, 2,5 l/día homes adultos, bebida + alimentos, en clima temperado) | EFSA Panel on Dietetic Products, Nutrition and Allergies. *Scientific Opinion on Dietary Reference Values for water*. EFSA Journal 2010;8(3):1459 |
| Actividade física adultos | 150 min/semana de actividade moderada (150–300) | OMS. *Directrices sobre actividade física e comportamentos sedentarios*, 2020 |
| Actividade física menores (5–17) | Media de 60 min/día | OMS 2020 |
| Maiores de 65 | Equilibrio e forza 3 días/semana | OMS 2020 |

## O que non facemos

- Non calculamos calorías, IMC nin «peso ideal».
- Non damos cifras de auga durante o exercicio (varían moito entre persoas).
- Os consellos meteorolóxicos da reserva (abrigo, auga, UV) son cualitativos e baséanse en limiares
  simples (≤ 8 °C, ≥ 20/27 °C, UV ≥ 3/6, chuvia ≥ 60 %, vento ≥ 35 km/h) documentados en
  `apps/integrations/weather.py`.

## v2: recomendacións dentro de cada reserva

O motor (`static/js/health-engine.js`) execútase **no navegador**. Usa o perfil gardado no dispositivo (`localStorage`, clave `eira-health-v1`) ou, só se a persoa o decidiu co consentimento do art. 9, o gardado na conta. Combina os datos da sesión: hora de inicio, duración, se é cuberta e a previsión.

| # | Recomendación | Cando | Cantidade | Fonte |
|---|---|---|---|---|
| 1 | Auga antes | Adultos con peso | 5–7 ml/kg (redondeado a 50 ml), á hora concreta **inicio − 4 h** | ACSM 2007, *Exercise and Fluid Replacement* |
| 2 | Durante | Adultos, sesión > 60 min ou calor (≥ 27 °C ao aire libre) | 0,4–0,8 l/h × duración, presentado como **punto de partida** | ACSM 2007 |
| 2b | Durante (cualitativo) | Sesión curta, ou menores | Sen cifra: «bebe se tes sede» / «nos descansos» | ACSM 2007 |
| 3 | Sales | ≥ 120 min, ou > 60 min con calor | Bebida con electrólitos | ACSM 2007 |
| 4 | Non bebas de máis (hiponatremia) | Adultos, ≥ 90 min | Aviso destacado | ACSM 2007 |
| 5 | Enerxía | Adultos, > 75 min | 30–60 g de hidratos/h × duración | Thomas, Erdman e Burke 2016 (ACSM/AND/DC, *Nutrition and Athletic Performance*) |
| 6 | Despois | Adultos, ≥ 45 min | ~1,5 l por kg perdido (se se pesa) | ACSM 2007 |
| 7 | Calor, tempo morno, frío, UV e chuvia | Segundo a previsión e se é descuberta | Temperatura e índice UV | Limiares de `apps/integrations/weather.py`; OMS (índice UV) |
| 8 | 65 anos ou máis | Idade ≥ 65 | Beber sen esperar á sede; equilibrio e forza 3 días/semana | OMS 2020; EFSA 2010 |
| 8b | Menores | Idade < 18 | 60 min/día; **sen cantidades de auga por peso** | OMS 2020 |
| 9 | A túa semana | Adultos con minutos semanais | (minutos + esta sesión)/150 | OMS 2020 |

**Por que non se dan cantidades a menores:** as referencias por kg do ACSM son para persoas adultas.

**Por que non hai unha taxa de suor estimada:** non hai ningunha fórmula publicada que funcione sen pesarse. Ver `docs/APRENDIZAXES.md`: a heurística de LifeGuarPro non se copiou.

### Privacidade
- Por defecto o peso e a idade nunca saen do navegador. Hai un E2E que comproba que ningunha petición leva o peso.
- Gardar na conta é opcional e esixe un consentimento explícito e versionado (`HealthProfile.CONSENT_VERSION`); queda no rexistro de auditoría. Bórrase cun botón.
- O persoal non o ve; non aparece no admin técnico nin na exportación do concello nin no observatorio. Si vai na exportación persoal (dereito de acceso). Probas en `apps/accounts/tests/test_health.py`.

## v3: formato breve co tempo real da franxa

En cada reserva, e na tarxeta da próxima reserva da app, amósanse **de 2 a 4 consellos dunha liña**, con cifra e acción. «Ver máis» desprega o detalle e a fonte. O cálculo segue no dispositivo (`recommendBrief` en `static/js/health-engine.js`).

| Orde | Consello breve | Datos | Fonte |
|---|---|---|---|
| 1 | «26 °C · UV 7 → crema e gorra» / «Sensación 30 °C → auga extra e sombra» / «6 °C → capas e 10 min de quecemento» | Temperatura, **sensación térmica** (índice de calor NOAA/Rothfusz con calor e humidade; sensación por vento NWS 2001 con frío), humidade, UV, vento e chuvia **da instalación para o día e a hora da reserva** (`WeatherAdapter`) | Limiares de `apps/integrations/weather.py`; OMS (índice UV) |
| 2 | «Bebe 300–450 ml entre as 15:00 e as 17:00» (5–7 ml/kg entre 4 e 2 h antes). Se iso cae antes das 7:00: «Ao espertar: bebe 200–300 ml» (3–5 ml/kg, 2 h antes) | Peso (só persoas adultas) e hora | ACSM 2007 |
| 3 | «Durante: 100–250 ml cada 15–20 min» (0,4–0,8 l/h), só se a sesión pasa de 60 min ou hai calor | Duración e sensación | ACSM 2007 |
| 4 | «90 min: hidratos e non beber de máis», ou a semana OMS, ou 65+ | Duración, minutos semanais e idade | Thomas, Erdman e Burke 2016; ACSM 2007; OMS 2020 |

- **Previsión:** `FakeWeatherAdapter` (desenvolvemento) é coherente co mes e a hora (medias mensuais de Galicia, ciclo diario, UV nulo de noite). `MeteoSixAdapter.parse` le temperatura, humidade, vento, precipitación e estado do ceo de MeteoSIX v5. O UV non vén nesa consulta e estímase. *Non verificado contra a API real (precisa clave).*
- **Privacidade:** o peso segue sen saír do teléfono (E2E `test_booking_shows_personal_recommendations_computed_on_device`).
