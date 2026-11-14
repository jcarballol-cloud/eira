<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Protocolo de brechas de seguridade dos datos persoais (arts. 33 e 34 do RXPD)

Unha **brecha** é calquera incidente que provoque a destrución, perda, alteración, comunicación ou acceso non autorizados a datos persoais: un correo enviado á lista equivocada, un portátil perdido coa exportación, unha conta de persoal usada por outra persoa, un erro que mostre datos doutro concello…

Responsable: o **concello** (responsable do tratamento). A deputación ou a empresa que aloxe Eira é encargada do tratamento e ten que avisar ao concello **sen dilación** se detecta unha brecha (art. 33.2).

## 1. Detectar e avisar (hora 0)
- Quen a detecte (persoal, empresa de soporte, veciñanza) avisa á administración do concello e á **persoa delegada de protección de datos (DPD)**.
- En Eira: **Xestión → Privacidade → Rexistro de brechas → Nova** (só administración do concello e DPD). Anótase a hora de detección: desde ela contan as **72 horas**.

## 2. Conter (primeiras horas)
- Parar a causa: revogar sesións ou accesos (incluído o acceso de soporte da deputación), cambiar segredos (`EIRA_SECRET_KEY`, `EIRA_PADRON_SECRET`, clave do TPV), retirar un ficheiro publicado, pedir a quen recibiu un correo por erro que o borre.
- Gardar as probas: `AuditLog`, rexistros do servidor, capturas.

## 3. Avaliar o risco
Valórase no rexistro con tres niveis:

| Nivel | Exemplo | Notificar á AEPD (art. 33) | Informar ás persoas (art. 34) |
|---|---|---|---|
| **Improbable que supoña un risco** | Exportación de indicadores agregados enviada por erro a outro concello | Non (documéntase o motivo) | Non |
| **Risco** | Lista de correos dunha actividade visible para outras persoas inscritas | **Si, en 72 h** | Non necesariamente |
| **Alto risco** | Datos de menores, de saúde (art. 9) ou de pagamentos expostos | **Si, en 72 h** | **Si, sen dilación** |

Agravantes: menores, saúde, gran número de persoas, datos que permitan suplantar a identidade, imposibilidade de recuperar o control.

## 4. Notificar á AEPD (art. 33)
- Sede electrónica da Axencia Española de Protección de Datos, formulario de notificación de brechas.
- Prazo: **72 horas desde a detección**. Se non se chega, notifícase igual explicando o motivo do atraso; pódese completar despois.
- No rexistro márcase «Notificada á AEPD» coa data. Eira mostra se se fixo en prazo.

## 5. Informar ás persoas afectadas (art. 34)
- Se hai alto risco, en linguaxe clara e sen dilación. Eira xera a **comunicación modelo** desde o rexistro (botón «Comunicación ás persoas afectadas»), que inclúe: que pasou, que datos, consecuencias probables, medidas tomadas, que pode facer a persoa e o contacto do DPD.
- Canle: a mesma pola que se relaciona a persoa co servizo (aviso na app e correo). Gárdase a data no rexistro.

## 6. Pechar e aprender
- Medidas para que non se repita. Pechar o rexistro coa data.
- O rexistro consérvase **5 anos** (prazo prudente: supera os 3 anos de prescrición das infraccións moi graves, art. 72 LOPDGDD; as graves prescriben aos 2, art. 73), aínda que a brecha non se notificase: o art. 33.5 obriga a documentar **todas**.

## Permisos en Eira
- **Ven e editan:** administración do concello e persoa con rol **DPD** (`dpo`) dese concello.
- **Non o ven:** veciñanza, mantemento, monitoras e **deputación** (nin sequera co acceso de soporte: a brecha pode afectar á propia deputación como encargada).
- Probas: `apps/accounts/tests/test_breaches.py`.

## Brecha de exemplo na demo
A demo inclúe unha brecha **ficticia e pechada** en Vilardeiras: un correo de avisos da escola de fútbol enviado con todos os enderezos á vista (CC en vez de CCO). Risco valorado, notificada á AEPD en 30 h, persoas informadas e medidas (avisos sempre desde Eira, que envía un correo por persoa). Ningún dato é real.
