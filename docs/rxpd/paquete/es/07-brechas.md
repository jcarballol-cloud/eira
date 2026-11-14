<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Protocolo de brechas de seguridad (arts. 33 y 34 RGPD)

> **MODELO DE EJEMPLO — requiere revisión del DPD y de los servicios jurídicos del concello.**

Conectado con el **registro de brechas de Eira** (*Gestión → Privacidad → Registro de brechas*). Cada
paso indica qué se hace en la app.

Una **brecha** (art. 4.12 RGPD) es cualquier incidente que provoque la destrucción, pérdida, alteración, comunicación o acceso no autorizados a datos personales: un correo enviado a la lista equivocada, un portátil perdido con la exportación, una cuenta de personal usada por otra persona, un error que muestre datos de otro concello…

Responsable: el **concello** (responsable del tratamiento). La diputación o la empresa que aloje Eira es encargada del tratamiento y tiene que avisar al concello **sin dilación** si detecta una brecha (art. 33.2).

## 1. Detectar y avisar (hora 0)
- Quien la detecte (personal, empresa de soporte, vecindad) avisa a la administración del concello y a la **persona delegada de protección de datos (DPD)**.
- En Eira: **Gestión → Privacidad → Registro de brechas → Nueva** (solo administración del concello y DPD). Se anota la hora de detección: desde ella cuentan las **72 horas**.

## 2. Contener (primeras horas)
- Detener la causa: revocar sesiones o accesos (incluido el acceso de soporte de la diputación), cambiar secretos (`EIRA_SECRET_KEY`, `EIRA_PADRON_SECRET`, clave del TPV), retirar un fichero publicado, pedir a quien recibió un correo por error que lo borre.
- Guardar las pruebas: `AuditLog`, registros del servidor, capturas.

## 3. Evaluar el riesgo
Se valora en el registro con tres niveles:

| Nivel | Ejemplo | Notificar a la AEPD (art. 33) | Informar a las personas (art. 34) |
|---|---|---|---|
| **Improbable que suponga un riesgo** | Exportación de indicadores agregados enviada por error a otro concello | No (se documenta el motivo) | No |
| **Riesgo** | Lista de correos de una actividad visible para otras personas inscritas | **Sí, en 72 h** | No necesariamente |
| **Alto riesgo** | Datos de menores, de salud (art. 9) o de pagos expuestos | **Sí, en 72 h** | **Sí, sin dilación** |

Agravantes: menores, salud, gran número de personas, datos que permitan suplantar la identidad, imposibilidad de recuperar el control.

## 4. Notificar a la AEPD (art. 33)
- Sede electrónica de la Agencia Española de Protección de Datos, formulario de notificación de brechas.
- Plazo: **72 horas desde la detección**. Si no se llega, se notifica igualmente explicando el motivo del retraso; se puede completar después.
- En el registro se marca «Notificada a la AEPD» con la fecha. Eira muestra si se hizo en plazo.

## 5. Informar a las personas afectadas (art. 34)
- Si hay alto riesgo, en lenguaje claro y sin dilación. Eira genera la **comunicación modelo** desde el registro (botón «Comunicación a las personas afectadas»), que incluye: qué pasó, qué datos, consecuencias probables, medidas tomadas, qué puede hacer la persona y el contacto del DPD.
- Canal: el mismo por el que se relaciona la persona con el servicio (aviso en la app y correo). Se guarda la fecha en el registro.

## 6. Cerrar y aprender
- Medidas para que no se repita. Cerrar el registro con la fecha.
- El registro se conserva **5 años** (plazo prudente: supera los 3 años de prescripción de las infracciones muy graves, art. 72 LOPDGDD; las graves prescriben a los 2, art. 73), aunque la brecha no se haya notificado: el art. 33.5 obliga a documentar **todas**.

## Qué hace el registro de Eira en cada paso

| Paso | En la app | Comprobado por |
|---|---|---|
| Detectar | «Nueva brecha» guarda la hora de detección y la de ocurrencia | `test_breaches.py::test_admin_and_dpo_can_use_the_register` |
| Evaluar | El nivel de riesgo es obligatorio; si hay riesgo, pide notificar a la AEPD o un motivo para no hacerlo, y muestra el plazo de 72 h | `test_breaches.py::test_risk_requires_aepd_or_a_reason_and_72h_deadline` |
| Informar a las personas | Botón «Comunicación a las personas afectadas» con texto modelo | `apps/accounts/breaches.py` |
| Documentar todas (art. 33.5) | También las no notificadas, con el motivo | Mismo test |
| Quién lo ve | Solo administración y DPD del concello; nunca la diputación | `test_breaches.py::test_region_never_sees_it_even_with_support_access` |

**Contención con herramientas de Eira:** revocar el acceso de soporte de la diputación (*Personal y
códigos*), restablecer el doble factor de una cuenta (*Seguridad*), retirar un rol, cambiar los
secretos de la instalación; el **registro de auditoría** (*Gestión → Registro de auditoría*, con
exportación CSV) indica quién hizo qué y cuándo.

**Si la brecha la detecta el encargado** (diputación o empresa que aloja Eira): avisa al concello sin
dilación (art. 33.2), como establece el contrato ([04-contrato-encargado.md](04-contrato-encargado.md)).

## Permisos en Eira
- **Ven y editan:** administración del concello y persona con rol **DPD** (`dpo`) de ese concello.
- **No lo ven:** vecindad, mantenimiento, monitoras y **diputación** (ni siquiera con el acceso de soporte: la brecha puede afectar a la propia diputación como encargada).
- Pruebas: `apps/accounts/tests/test_breaches.py`.

## Brecha de ejemplo en la demo
La demo incluye una brecha **ficticia y cerrada** en Vilardeiras: un correo de avisos de la escuela de fútbol enviado con todas las direcciones a la vista (CC en vez de CCO). Riesgo valorado, notificada a la AEPD en 30 h, personas informadas y medidas (avisos siempre desde Eira, que envía un correo por persona). Ningún dato es real.
