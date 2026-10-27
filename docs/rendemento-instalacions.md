<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Rendemento das instalacións (v1.2 · D)

Panel «Rendemento» de cada instalación (`Xestión → Instalacións → ‹instalación› → Rendemento`) e resumo de todas (`Xestión → Rendemento`). Na comparativa da deputación só van **agregados por concello**.

Código: `apps/analytics/performance.py`. Probas: `apps/analytics/tests/test_performance.py` (contas feitas á man).

> **O consumo é sempre unha estimación orientativa.** Calcúlase cos datos que Eira xa ten e co inventario que introduce o concello; non é unha lectura do contador. Para comparar, o concello pode anotar as lecturas reais das facturas.

Non confundir con `docs/rendemento.md`, que trata do rendemento do software (RAM, tempos de resposta).

## Datos de partida

| Dato | De onde sae |
|---|---|
| Horas dispoñibles | Horario real de apertura de cada día do período (con tempadas), descontando os peches (da instalación ou de todo o concello). |
| Horas reservadas | Reservas confirmadas, usadas ou non presentadas que empezan no período (duración da franxa). |
| Horas de uso real | Reservas **usadas** con entrada rexistrada (QR, código, apertura remota ou chave). |
| Horas «con reserva en uso» | Unión no tempo das reservas que se usaron (con check-in; no nivel 0, tamén as confirmadas sen QR, porque alí o QR é voluntario). As non presentadas non contan: o equipo non se acende. |
| Horas con luz | Unión das anteriores que levaban suplemento de luz (ou «necesito luz»). |
| Inventario de equipos | Tipo (iluminación, calefacción/climatización, auga quente, bombas/depuración, outros), potencia (kW), modo de uso e factor de uso (0–1). |

Nas instalacións de uso compartido (ximnasio, piscina) as horas «con reserva en uso» son a **unión** dos intervalos: catro persoas á vez acenden o equipo unha soa hora.

## Fórmulas

- **Ocupación (reservada)** = horas reservadas ÷ (horas dispoñibles × prazas simultáneas) × 100.
- **Uso real** = horas de uso real ÷ (horas dispoñibles × prazas) × 100.
- **Tempo medio de uso** = media de (fin − máx(inicio, hora de entrada)) nas reservas usadas, en minutos.
- **Consumo estimado (kWh)** = Σ equipos de potencia × factor de uso × horas segundo o modo:
  - *durante a apertura* → horas dispoñibles;
  - *só con reserva* → horas con reserva en uso;
  - *só con suplemento de luz* → horas con luz;
  - *continuo* → 24 h × días do período.
- **Coste estimado (€)** = kWh × prezo da enerxía do concello (Configuración → Rendemento; por defecto 0,18 €/kWh).
- **CO₂ estimado (kg)** = kWh × factor de emisión do concello (por defecto 0,150 kg/kWh; cada concello pon o da súa comercializadora).
- **kWh e € por hora de uso** = consumo (ou coste) ÷ horas de uso real. Sen usos rexistrados non se calcula.
- **Estimado fronte a real**: para cada lectura de factura calcúlase a estimación do mesmo período; diferenza = (estimado − real) ÷ real × 100.

Períodos do panel: últimos 7, 30 e 365 días, e tendencia mensual (dende o primeiro mes con reservas, ata 12 meses).

## Perfil das persoas usuarias

Persoas distintas con reservas usadas no último ano: porcentaxe por franxa de idade (0–17, 18–34, 35–54, 55–64, 65+), empadroadas e doutros concellos da rede. **Só se mostra con n ≥ 10** (o mesmo umbral ca o observatorio e o índice de vida activa). Nunca se mostra quen.

## Limitacións coñecidas

- Nas instalacións abertas (nivel 0) o QR de entrada é voluntario: o uso real pode quedar por debaixo do verdadeiro.
- A calidade da estimación depende do inventario: potencias de placa e factores de uso aproximados. Por iso se ofrece a comparación coas facturas.
- Os equipos «durante a apertura» suman todas as horas de apertura aínda que a instalación estea baleira (é o que pasa na realidade se non hai detector de presenza).
