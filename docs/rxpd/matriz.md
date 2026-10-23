<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Matriz de visibilidade de datos por perfil

Que dato ve cada perfil e onde se comproba. As probas en `apps/*/tests/test_privacy*.py`, `apps/tenants/tests/test_roles.py` e `apps/accounts/tests/test_privacy.py` verifican esta matriz.

Lenda: **✔** ve o dato · **—** non o ve · **agr.** só agregado (n ≥ 10) · **seud.** seudonimizado.

| Dato | Veciña (propio) | Operario/a | Monitor/a | Concello | Deputación | Observatorio público | Exportacións |
|---|---|---|---|---|---|---|---|
| Correo e teléfono | ✔ | — | — | ✔ (reservas, altas) | como o concello, só lectura | — | — |
| Nome para mostrar | ✔ | — | ✔ (participantes dos seus grupos) | ✔ | como o concello, só lectura | — | — |
| Empadroamento (si/non) | ✔ | — | — | ✔ | como o concello, só lectura | — | — |
| Colectivo de tarifa reducida | ✔ | — | — | ✔ (sen documentos) | como o concello, só lectura | — | — |
| Reservas | ✔ | só instalación e hora na orde | — | ✔ | como o concello, só lectura | agr. (datos abertos) | agregados (CSV/ODS) |
| Pagamentos | ✔ | — | — | ✔ (referencia, importe e estado) | como o concello, só lectura | — | conciliación (sen datos bancarios) |
| Menores: nome e ano | ✔ (os seus) | — | ✔ (nome nos seus grupos) | ✔ | como o concello, só lectura | — | — |
| Consentimento de imaxe | ✔ | — | ✔ (icona de cámara) | ✔ (icona e filtro) | como o concello, só lectura | — | — |
| Asistencia e esforzo (RPE) | — | — | ✔ (os seus grupos, se hai consentimento) | ✔ | como o concello, só lectura | agr. por banda de idade | seud. (só concello) |
| Valoracións «Que tal foi?» | ✔ | — | — | ✔ **sen nome** | como o concello, só lectura | — | agregados sen comentarios |
| Incidencias que comunica | ✔ | ✔ (sen datos de contacto) | — | ✔ | como o concello, só lectura | — | agregados |
| Saúde (peso, idade para recomendacións) | ✔ no dispositivo; na conta só con consentimento art. 9 | — | — | — | — | — | — |
| Padrón | — (Eira non o garda) | — | — | só o resultado si/non da consulta | como o concello, só lectura | — | — |

## Principios
- **Minimización:** non se piden DNI, enderezo nin apelidos dos menores. O pago faise na pasarela da entidade.
- **Saúde (art. 9 RXPD):** os datos quedan no dispositivo por defecto. Só se gardan na conta con consentimento explícito e revogable. Nunca os ve o persoal, nin van ás exportacións nin ao observatorio (ver `docs/health/recomendacions.md`).
- **Menores:** por debaixo dos 14 anos consente a familia (art. 7 LOPDGDD). Con 14 ou máis, a familia confirma que o menor está de acordo.
- **Imaxe:** consentimento separado, por persoa e revogable. O monitor e o concello ven unha cámara verde ou riscada en vermello.
- **Deputación:** entra no concello en modo consulta. Ve o mesmo ca o concello, pero non pode cambiar nada (403 en calquera escritura) e na cabeceira aparece o aviso «Estás vendo… como Deputación». O único que pode facer é a acción de soporte «Reenviar invitación».
- **Sen seguimento:** só hai cookies técnicas (`sessionid`, `csrftoken`, `django_language`, `eira_prefs` e, na demo, `eira_marco`). Unha proba falla se aparece outra.
