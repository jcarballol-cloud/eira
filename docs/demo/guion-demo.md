# Guión da demostración (3 minutos)

**Preparación (antes do pitch):** `docker compose up` (ou `python tools/tasks.py dev`) e abrir
<http://localhost:8000>. A demo recárgase con `make seed` (datos ficticios; as reservas créanse
arredor da hora actual). Ter dúas xanelas: unha en móbil (DevTools 390 px) para a veciñanza e outra
en escritorio para o concello.

| Tempo | Pantalla | Que facer | Que dicir |
|---|---|---|---|
| 0:00 | Portada | Mostrar o lema e o ciclo de 8 pasos | «Reservar é o fácil. O difícil é abrir a porta nunha parroquia sen conserxe.» |
| 0:15 | Portada → **Entrar como Uxía** (móbil) | Instalacións → «Pista de pádel da Pereira» | «Lista accesible ou mapa. A grella di que está libre, ocupada ou recomendada (★ pouca demanda).» |
| 0:30 | Grella → franxa ★ → Confirmar | Marcar «Lin e acepto as normas» → Pagar → TPV simulado «Pagar» | «Normas versionadas: queda gardado que versión aceptou e cando. Tempo previsto e consellos de abrigo/UV.» |
| 0:50 | Detalle da reserva | Ensinar o **código de 6 díxitos** e «Válido de 19:20 a 21:10» | «A pechadura non ten internet. O código só vale na túa franxa.» |
| 1:00 | **Probalo no simulador de pechadura** | Teclear o código → **ABERTO**. Despois «+1 h» → mesmo código → **DENEGADO** | «Mesmo segredo, mesmo algoritmo (HOTP, RFC 4226), sen rede. Fóra da franxa, non abre.» |
| 1:25 | As miñas reservas → aviso «Acabas de usar…» → **Checklist de peche** | Responder «Non» a «Deixaches a porta pechada?» | «Pechar e avisar: se algo vai mal, créase unha incidencia soa.» |
| 1:40 | Cambiar de perfil → **Concello de Vilardeiras** (escritorio) | Panel do día → «Incidencias por validar» → abrir a nova | «O concello véo no panel do día, xunto ás chaves que hai que entregar hoxe.» |
| 1:55 | Incidencia | «Validar» → «Crear orde» asignada a Brais | «A veciña recibe un aviso en cada paso.» |
| 2:10 | Cambiar de perfil → **Brais** (móbil) | Abrir a orde → marcar checklist → «Pechar orde» (opcional: DevTools → Offline, pechar, volver online) | «A app do operario funciona sen cobertura: garda e envía ao volver a rede.» |
| 2:30 | **Concello** → Indicadores | Ocupación por instalación, non presentadas, mapa de calor, infrauso, CSV | «Cada gráfico ten a súa táboa e o seu CSV. Por fin o concello ten datos de uso.» |
| 2:45 | **Deputación das Marismas** | Comparativa de concellos → «Dar de alta un concello» | «Unha deputación desprega unha vez e dá servizo a todos os concellos. Software libre EUPL, datos exportables enteiros.» |
| 3:00 | — | Peche | «Eira: da reserva á porta, e da porta aos datos.» |

## Plan B

- Se falla a rede: todo funciona en local (sen CDN; o mapa de OSM é o único recurso externo e é
  opcional: usar a vista de lista).
- Se a franxa ★ xa non está libre: calquera franxa verde serve.
- Reserva de Uxía no ximnasio xa creada (nivel 2): «As miñas reservas» → ximnasio → código → simulador.

## Capturas

Todas as pantallas do guión están en [`docs/capturas/`](../capturas/) (móbil e escritorio),
xeradas con `python tools/tasks.py screenshots`.
