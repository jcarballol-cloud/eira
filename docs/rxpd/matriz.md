<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Matriz de visibilidade de datos por perfil

Que dato ve cada perfil e onde se comproba. As probas en `apps/*/tests/test_privacy*.py`, `apps/tenants/tests/test_roles.py` e `apps/accounts/tests/test_privacy.py` verifican esta matriz.

Lenda: **✔** ve o dato · **—** non o ve · **agr.** só agregado (n ≥ 10) · **seud.** seudonimizado.

| Dato | Veciña (propio) | Operario/a | Monitor/a | Concello | Deputación | Observatorio público | Exportacións |
|---|---|---|---|---|---|---|---|
| Correo e teléfono | ✔ | — | — | ✔ (reservas, altas) | só con acceso de soporte (24 h) | — | — |
| Nome para mostrar | ✔ | — | ✔ (nome e primeiro apelido dos seus grupos) | ✔ | só con acceso de soporte (24 h) | — | — |
| Empadroamento (si/non) | ✔ | — | — | ✔ | só con acceso de soporte (24 h) | — | — |
| Colectivo de tarifa reducida | ✔ | — | — | ✔ (sen documentos) | só con acceso de soporte (24 h) | — | — |
| Reservas | ✔ | só instalación e hora na orde | — | ✔ | agr.; detalle só con acceso de soporte (24 h) | agr. (datos abertos) | agregados (CSV/ODS) |
| Pagamentos | ✔ | — | — | ✔ (referencia, importe e estado) | só con acceso de soporte (24 h) | — | conciliación (sen datos bancarios) |
| Menores: nome e ano | ✔ (os seus) | — | ✔ (nome e primeiro apelido nos seus grupos) | ✔ | só con acceso de soporte (24 h) | — | — |
| Consentimento de imaxe | ✔ | — | ✔ (icona de cámara) | ✔ (icona e filtro) | só con acceso de soporte (24 h) | — | — |
| Asistencia e esforzo (RPE) | — | — | ✔ (os seus grupos, se hai consentimento) | ✔ | só con acceso de soporte (24 h) | agr. por banda de idade | seud. (só concello) |
| Valoracións «Que tal foi?» | ✔ | — | — | ✔ **sen nome** | só con acceso de soporte (24 h) | — | agregados sen comentarios |
| Incidencias que comunica | ✔ | ✔ (sen datos de contacto) | — | ✔ | só con acceso de soporte (24 h) | — | agregados |
| Saúde (peso, idade para recomendacións) | ✔ no dispositivo; na conta só con consentimento art. 9 | — | — | — | — | — | — |
| Padrón | — (Eira non o garda) | — | — | só o resultado si/non da consulta | só con acceso de soporte (24 h) | — | — |

## Principios
- **Minimización:** non se piden DNI, enderezo nin apelidos dos menores. O pago faise na pasarela da entidade.
- **Saúde (art. 9 RXPD):** os datos quedan no dispositivo por defecto. Só se gardan na conta con consentimento explícito e revogable. Nunca os ve o persoal, nin van ás exportacións nin ao observatorio (ver `docs/health/recomendacions.md`).
- **Menores:** por debaixo dos 14 anos consente a familia (art. 7 LOPDGDD). Con 14 ou máis, a familia confirma que o menor está de acordo.
- **Imaxe:** consentimento separado, por persoa e revogable. O monitor e o concello ven unha cámara verde ou riscada en vermello.
- **Deputación:** por defecto ve só datos agregados e anónimos: indicadores, comparativa, instalacións, peches e plans de mantemento (`@aggregate_view`). Para os datos persoais precisa un **acceso de soporte** que autoriza o concello en «Persoal e códigos», con motivo. Caduca ás 24 h, pódese revogar, cada páxina vista queda en AuditLog (`support.view`) e o concello recibe un aviso no primeiro uso. Mesmo co acceso, é só lectura. Tests: `apps/tenants/tests/test_support_access.py` (403 → 200 → 403 ao caducar).
- **Apelidos:** son un dato da inscrición que achega o concello. A tableta só recibe nome e primeiro apelido (o segundo nin sequera chega ao navegador); o nome completo só se ve na administración.
- **Sen seguimento:** só hai cookies técnicas (`sessionid`, `csrftoken`, `django_language`, `eira_prefs` e, na demo, `eira_marco`). Unha proba falla se aparece outra.
