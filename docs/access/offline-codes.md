# Códigos de acceso temporais sen conexión (nivel 2)

## O problema

Moitas instalacións dun concello pequeno (unha pista nunha parroquia, un ximnasio nun baixo
municipal) non teñen conserxe nin conexión a internet fiable. Queremos que a persoa que reservou
poida abrir **só durante a súa franxa**, sen chaves físicas e sen que a pechadura teña que
consultar ningún servidor.

## O esquema

A plataforma e a pechadura comparten un **segredo** `K` (160 bits, base32) que se grava no teclado
ao instalalo. A pechadura ten un reloxo propio. O código depende só de `K` e da franxa reservada:

```
S  = minutos por bloque (por defecto 30)            T = tolerancia (por defecto ±10 min)
b  = floor(inicio_unix / (S·60))                     bloque horario no que empeza a reserva
d  = duración en bloques (1 ≤ d ≤ D_MAX, D_MAX = 8)   franxa de 90 min → d = 3
C  = b · 16 + d                                      contador (4 bits para a duración)
código = HOTP(K, C)                                  RFC 4226: HMAC-SHA1, truncado a 6 díxitos
```

**Validación na pechadura** á hora `t` do seu reloxo: para cada duración posible `d` e cada bloque
`b` tal que `b·S − T ≤ t ≤ (b+d)·S + T`, calcula `HOTP(K, b·16 + d)` e compárao (en tempo
constante) co código tecleado. Se coincide algún, abre e rexistra o par `(b, d)`.

Así, unha reserva de 18:00 a 19:30 produce un código válido **de 17:50 a 19:40** e en ningún outro
momento: nin antes, nin despois, nin o mesmo día da semana seguinte. Como a duración forma parte do
contador, o código dunha franxa de 30 minutos non serve para estenderse ás seguintes.

Implementación de referencia: [`apps/access/offline_codes.py`](../../apps/access/offline_codes.py)
(sen dependencias de Django, para levala tal cal ao firmware). Os mesmos cálculos úsanse na
plataforma (para mostrar o código) e no simulador [`/dev/lock-simulator`](../../apps/integrations/views_dev.py).

### Parámetros por dispositivo (`LockDevice`)

| Campo | Defecto | Notas |
|---|---|---|
| `step_minutes` | 30 | As reservas deben estar aliñadas ao bloque (as franxas de 60 e 90 min o están). |
| `tolerance_minutes` | 10 | Absorbe a deriva do reloxo e a puntualidade humana. |
| `digits` | 6 | 8 para instalacións de maior risco (ver forza bruta). |
| `max_blocks` | 8 | Reserva máxima de 4 h con bloques de 30 min (límite do esquema: 15 bloques). |

## Probas

[`apps/access/tests/test_offline_codes.py`](../../apps/access/tests/test_offline_codes.py) cobre:
os bordos exactos da xanela (`inicio − T` válido, un segundo antes inválido; `fin + T` válido, un
segundo despois inválido), a mesma hora noutro día, códigos doutra franxa, a duración como parte do
código, segredo distinto, entradas mal formadas, reservas non aliñadas, tolerancia cero e unha proba
de propiedade con 300 reservas aleatorias. [`test_access_levels.py`](../../apps/access/tests/test_access_levels.py)
proba o bloqueo por intentos, o bloqueo exponencial e o aviso ao concello. Un test E2E fai o
percorrido completo no navegador: reserva → código → simulador ABERTO → hora fóra da xanela → DENEGADO.

## Limitacións (honestamente)

1. **Non está ligado á persoa.** O código é da franxa, non de quen reserva. Quen o coñeza pode
   entrar durante esa franxa. *Mitigación:* a interface avisa de non compartilo fóra do grupo; a
   reserva rexistra quen a fixo e o checklist de peche e as incidencias permiten detectar abusos.
   Para o uso habitual (unha pista que reserva un grupo de amigos) é precisamente o desexado.
2. **Reutilizable dentro da franxa.** A pechadura non sabe se o código xa se usou porque non ten
   rede. *Mitigación:* a xanela é curta (franxa ± 10 min). Un teclado con memoria pode rexistrar
   os usos e subilos cando teña conexión (ou ao pasar o operario) para conciliar co uso real.
3. **Deriva do reloxo.** Un RTC barato pode derivar uns segundos ao día. *Mitigación:* a tolerancia
   de ±10 min absorbe meses de deriva; o operario resincroniza a hora nas revisións de mantemento
   preventivo (pódese engadir como tarefa do plan). Unha pechadura con GNSS ou DCF77 elimina o problema.
4. **Forza bruta.** En cada instante a pechadura acepta uns 44 códigos distintos (todas as
   combinacións de bloque e duración que inclúen a hora actual; `candidate_count()`), polo que un
   intento ao chou acerta con probabilidade ≈ 44/10⁶ = 4,4·10⁻⁵ con 6 díxitos.
   *Mitigacións implementadas:* bloqueo tras 5 fallos **exponencial** (5, 10, 20, 40… min ata 24 h),
   que limita un ataque persistente a ~45 intentos o primeiro día e ~5 diarios despois
   (≈ 0,2 % o primeiro día; ≈ 0,02 % cada día seguinte), e **aviso ao concello** tras 3 bloqueos
   seguidos. *Recomendación:* 8 díxitos en instalacións de maior valor (probabilidade por intento
   4,4·10⁻⁷). Compromiso: un atacante pode bloquear o teclado e impedir a entrada lexítima (DoS);
   por iso o nivel 2 sempre debe ter un plan B (teléfono do concello ou chave custodiada).
5. **Compromiso do segredo.** Quen extraia `K` dun teclado pode xerar códigos dese dispositivo
   (só dese: cada pechadura ten o seu segredo). *Mitigación:* rotación do segredo na revisión
   anual; a exportación de datos marca os segredos como sensibles.
6. **Sen revogación inmediata.** Se se cancela unha reserva, o seu código segue sendo válido na
   pechadura. *Mitigación:* as cancelacións tardías son raras e a franxa queda libre igualmente; un
   teclado con conexión ocasional pode recibir unha lista de contadores revogados.

## Por que non outras opcións

- **TOTP estándar (30 s):** obriga a ter o móbil con conexión no intre de abrir e non expresa a
  duración da reserva.
- **Códigos asinados (p. ex. HMAC de 12+ caracteres con inicio e fin):** máis fortes pero
  incómodos de teclear nun teclado numérico, sobre todo para persoas maiores.
- **Pechadura conectada (nivel 3):** mellor control, pero require electricidade e rede estables;
  Eira ofrécea como nivel 3 co mesmo adaptador (`LockAdapter`).

## Estándares

HOTP — [RFC 4226](https://www.rfc-editor.org/rfc/rfc4226) (implementación `pyotp`, MIT). O
contador é un enteiro de 8 bytes big-endian como no RFC; calquera biblioteca HOTP compatible pode
reproducir os códigos.
