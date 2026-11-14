<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Política de conservación

> **MODELO DE EXEMPLO — require revisión do DPD e dos servizos xurídicos do concello.**

Os datos persoais só se conservan o tempo necesario para a finalidade (art. 5.1.e RXPD). Eira
aplica os prazos **automaticamente**: a orde `python manage.py booking_maintenance` (programada
cada 15 minutos, ver `docs/despregamento.md`) borra ou anonimiza o que caducou e deixa constancia
das cifras no rexistro de auditoría (`retention.purge`, `audit.purge`). O concello debe **confirmar
ou cambiar** estes prazos co seu DPD (punto 6 de «Protección de datos: primeiros pasos»).

**Anonimizar** = quitar a persoa e os textos libres e deixar o resto (data, instalación, importe)
para a contabilidade e as estatísticas. **Bloqueo** (art. 32 LOPDGDD): se o concello ten que
conservar algo para atender responsabilidades legais, debe facelo fóra do uso ordinario; Eira non
ten un estado de bloqueo propio (ver `docs/PLAN_V2.md`).

## Prazos que aplica Eira

| Datos | Prazo | Que pasa | Regra (`EIRA_RETENTION`) ou orixe |
|---|---|---|---|
| Reservas (persoa, nomes, teléfono, notas, foto do estado) | 24 meses despois de rematar | Anonimízase; as partidas abertas desa reserva bórranse | `bookings` |
| Eventos de acceso (porta, códigos) | 24 meses | Bórranse | `access_events` |
| Incidencias resoltas | 24 meses despois de resolver | Quítanse quen avisou e a foto; queda a descrición da avaría | `incidents` |
| Comentarios das valoracións | 24 meses | Bórrase o comentario; a nota segue contando | `ratings` |
| Respostas das enquisas anuais | 24 meses | Quítanse a persoa e o comentario | `surveys` |
| Rexistro de limpeza (persoal) | 24 meses | Bórrase, coa foto | `cleaning` |
| Denuncias de partidas abertas | 12 meses | Bórranse | `game_reports` |
| Altas pendentes da tableta (nome, ano e correo da familia) | 3 meses | Bórranse | `pending_participants` |
| Códigos de empadroamento sen usar | 1 mes despois de caducar | Bórranse | `invitations` |
| Correo e mensaxes simuladas (só cos adaptadores de proba) | 1 mes | Bórranse | `simulated` |
| Códigos para entrar (levan o correo) | Caducan aos 10 minutos; bórranse ao día seguinte | Bórranse | `purge_login_codes` |
| Sesións caducadas (14 días) | Ao caducar | Bórranse | `purge_sessions` |
| Solicitudes da app | 12 meses (o DNI/NIE, a data e o enderezo bórranse ao resolver) | Bórranse | `purge_app_requests` |
| Avisos recibidos | 12 meses | Bórranse | `notifications.notices.purge` |
| Códigos de vinculación de Telegram | 1 día (caducan aos 30 minutos) | Bórranse | `notifications.notices.purge` |
| Rexistro de accidentes | 24 meses despois de pechado (configurable polo concello) | Bórrase | `accident_retention_months` |
| Rexistro de auditoría | 24 meses (configurable, 12–120) | Bórrase | `audit_retention_months` |
| Resumos do padrón (HMAC) | Ata a seguinte carga | Substitúense | Carga do padrón |
| Conta, preferencias, saúde gardada, carné e procedencia | Mentres a persoa teña a conta | Bórranse coa conta; as reservas quedan anonimizadas | Supresión (art. 17) |
| Aceptacións de documentos legais | A que fixe o concello | Ao eliminar a conta quedan sen persoa | Módulo «Documentos legais» |
| Rexistro de brechas | 5 anos (máis que os 3 de prescrición das infraccións moi graves, art. 72 LOPDGDD) | Manual | `brechas.md` |

Para cambiar un prazo na instalación: `EIRA_RETENTION = {"bookings": 36}` en `eira/settings.py`
(ou na configuración de despregamento). Os prazos de accidentes e auditoría cámbiaos o concello
en «Configuración».

## Prazos sen purga automática (pendentes)

| Datos | Prazo previsto | Por que non se purga aínda |
|---|---|---|
| Pagamentos | 6 anos (normativa tributaria) | Depende da contabilidade de cada concello; ver `PLAN_V2.md` |
| Asistencia, esforzo (RPE) e probas físicas | Tempada + 1 ano | As tempadas non teñen data de fin común; ver `PLAN_V2.md` |
| Rexistro de brechas | 5 anos | Pouco volume; bórrao o concello |

## Como comprobalo

- Tests: `apps/accounts/tests/test_retention.py` (unha proba por regra e unha que comproba que cada
  regra está nesta táboa).
- Na instalación: `python manage.py booking_maintenance` escribe «Conservación: {…}» co que
  borrou; no rexistro de auditoría aparece «Datos antigos borrados ou anonimizados por conservación».
