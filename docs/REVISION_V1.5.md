<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Revisión final da v1.5: funcións de v1.0 a v1.5

**Como se comprobou.** «Recorrido» significa que `tests/e2e/test_recorrido_v15.py` abriu a pantalla co
navegador, co perfil indicado, sobre a demo: responde 200, mostra o texto esperado e non dá erros de
consola. «Tests» significa probas unitarias ou E2E do seu fluxo. **O recorrido é automático: non
substitúe a revisión dunha persoa**, sobre todo en usabilidade e en lectores de pantalla.

## Comprobado

| Versión | Función | Perfil | Como |
|---|---|---|---|
| v1.0 | Consulta sen rexistro, mapa, ficha e grella semanal | Público | Recorrido |
| v1.0 | Reserva, pagamento simulado, código e pechadura simulada | Veciñanza | Tests E2E (`test_flows`) |
| v1.0 | Reservas, historial, recibos e cancelación | Veciñanza | Recorrido e tests |
| v1.0 | Incidencia con foto, avisos multicanle | Veciñanza | Recorrido e tests |
| v1.0 | Unidade familiar e consentimentos | Veciñanza | Recorrido e tests |
| v1.0 | Saúde persoal no dispositivo | Veciñanza | Recorrido e tests |
| v1.0 | Ordes de traballo sen cobertura e calendario | Mantemento | Recorrido e `test_service_worker` |
| v1.0 | Tableta: sesións, rexistro con esforzo, asistencia e estatísticas | Monitora | Recorrido e `test_kiosk` |
| v1.0 | Observatorio anónimo e datos abertos | Administración, público | Recorrido e tests |
| v1.0 | Panel do día, axenda, reservar por alguén, cobros, indicadores | Administración | Recorrido |
| v1.0 | Comparativa da rede e alta de concellos | Deputación | Recorrido e tests |
| v1.0 | Portabilidade e API OpenAPI | Administración | Recorrido e tests |
| v1.0 | Brechas e «Quen custodia os datos» | Administración, público | Recorrido e tests |
| v1.1 | Limpeza: tarefas, zonas con QR e rexistro | Limpeza, administración | Recorrido e tests |
| v1.2 | Aviso e alerta, protocolo de accidente, rexistro de accidentes | Veciñanza, administración | Recorrido e tests |
| v1.2 | Peche sen confirmar e escalado | Administración | Tests |
| v1.2 | Valoracións, NPS e enquisas | Administración | Recorrido e tests |
| v1.2 | Rendemento e índice de vida activa | Administración | Recorrido e tests |
| v1.2 | Lista de espera | Veciñanza | Tests |
| v1.2 | Partidas abertas | Veciñanza | Recorrido e tests |
| v1.2 | Carné municipal e abonos | Veciñanza, administración | Recorrido e tests |
| v1.3 | Ordenanza modelo, EIPD e goberno | Documentos | Ficheiros e resumo público no recorrido |
| v1.3 | Dobre factor e rexistro de auditoría | Administración | Recorrido e `test_v13` |
| v1.4 | Segredo TOTP cifrado e conservación da auditoría | Administración | Tests |
| v1.5 | A · «Escoitar» | Veciñanza | `test_listen` (voz simulada) e `test_listen_core` |
| v1.5 | B · Alerta en todos os perfís, persoal de servizo, DESA e 112 | Persoal | Recorrido, `test_v15` e `test_alert_profiles` |
| v1.5 | C · Procedencia e mobilidade agregadas | Administración, deputación, veciñanza | Recorrido, `test_v15` e `test_provenance` |
| v1.5 | D · Documentos legais versionados | Todos | Recorrido, `test_v15` e `test_legal` |
| v1.5 | E · Acreditación con menores | Administración | Recorrido, `test_v15` e `test_accreditation` |
| v1.5 | F · LEEME en galego e castelán | Administración | Recorrido e `test_leeme` |

## Non comprobado

| Función | Por que |
|---|---|
| «Escoitar» cunha voz real (galego ou castelán) e sen conexión | As probas usan unha voz simulada |
| «Escoitar» con TalkBack e VoiceOver | Sen dispositivos nin lectores de pantalla reais |
| Lectura automática do código nun móbil real | Depende do navegador |
| Canles reais de aviso nas alertas (correo, Telegram e push) | Só adaptadores simulados |
| Pechadura, TPV, Cl@ve, lector de carné, Telegram e SVDR reais | Só adaptadores simulados, sen contas externas |
| Validez legal dos modelos | **Non son documentos legais válidos**: precisan revisión xurídica e do DPD |
| Accesibilidade con persoas usuarias | axe só detecta parte dos problemas |
