<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Contrato de encargado do tratamento (art. 28 RXPD; art. 33 LOPDGDD)

> **MODELO DE EXEMPLO — require revisión do DPD e dos servizos xurídicos do concello.**

Para cando Eira non a aloxa o propio concello, senón **a deputación, unha mancomunidade, unha
empresa ou engram**. O concello segue sendo o responsable; quen aloxa é o encargado e só pode
tratar os datos seguindo as instrucións do concello. Se o encargado é outra administración, o
contrato pode ser un convenio ou outro acto xurídico que vincule do mesmo xeito (art. 28.3).

As cláusulas seguen as letras a–h do art. 28.3. O que vai entre `‹ ›` complétao o concello.

---

**Entre** o Concello de ‹nome› (en diante, «o responsable»), con NIF ‹›, representado por ‹›,
**e** ‹entidade› (en diante, «o encargado»), con NIF ‹›, representado por ‹›.

### 1. Obxecto e duración
O encargado presta o servizo de **aloxamento, mantemento e soporte técnico da plataforma Eira**
para o servizo municipal de deportes, desde ‹data› ata ‹data› ou ata o fin do contrato principal
‹referencia›.

### 2. Natureza, finalidade e tratamentos
- **Operacións:** almacenamento, copia de seguridade, actualización do software, consulta só cando
  o pida o responsable para resolver unha incidencia, e supresión ao finalizar.
- **Tratamentos:** os do rexistro de actividades ([01-rexistro-actividades.md](01-rexistro-actividades.md)).
- **Categorías de datos:** identificativos e de contacto; reservas e pagamentos (sen datos de
  tarxeta); menores; **saúde só se a persoa a garda na súa conta** (art. 9.2.a); rexistro de
  accidentes sen diagnósticos.
- **Interesados:** veciñanza usuaria, menores e persoas titoras, persoal do concello e de empresas
  contratadas (limpeza, mantemento).

### 3. Instrucións documentadas (art. 28.3.a)
O encargado trata os datos **só seguindo as instrucións documentadas do responsable**, tamén para
transferencias internacionais. Instrucións mínimas:
1. Non acceder aos datos persoais agás para resolver unha incidencia pedida polo responsable.
   **Se o encargado é a deputación, usa o «acceso de soporte» de Eira**: autorízao o concello, con
   motivo, caduca ás 24 h, é só de lectura e cada páxina queda no rexistro de auditoría do concello.
2. **Non transferir datos fóra da Unión Europea.** Servidores e copias en ‹país da UE›.
3. Manter activada a purga automática (`booking_maintenance`) cos prazos que fixe o responsable
   ([05-conservacion.md](05-conservacion.md)).
4. Non activar adaptadores externos (correo, pasarela, Telegram, IA, teselas do mapa) sen instrución
   escrita do responsable.
Se unha instrución infrinxe a normativa, o encargado avisa ao responsable de inmediato.

### 4. Confidencialidade (art. 28.3.b)
As persoas autorizadas polo encargado comprométense por escrito á confidencialidade ou están
suxeitas a unha obriga legal de confidencialidade.

### 5. Seguridade (art. 28.3.c e art. 32)
O encargado aplica as medidas do Esquema Nacional de Seguridade (RD 311/2022) que correspondan ao
servizo (disposición adicional 1.ª LOPDGDD), como mínimo:
- cifrado en tránsito (HTTPS) e das copias de seguridade; segredos (`EIRA_SECRET_KEY`,
  `EIRA_TOTP_KEY`, `EIRA_PADRON_SECRET`) fóra da base de datos e do repositorio;
- control de acceso ao servidor con dobre factor e rexistro;
- copias de seguridade ‹periodicidade› e proba de restauración ‹periodicidade›;
- actualizacións de seguridade de Eira e do sistema en ‹prazo›;
- rotación dos rexistros do servidor (levan enderezos IP).

### 6. Subencargados (art. 28.2 e 28.3.d)
O encargado non recorre a outro encargado sen **autorización previa por escrito** ‹específica /
xeral› do responsable. Lista autorizada: ‹provedor de servidores (UE)›, ‹provedor de correo›. Se é
xeral, avisa dos cambios para que o responsable poida oporse. O subencargado asume as mesmas
obrigas por contrato.

### 7. Axuda cos dereitos das persoas (art. 28.3.e)
O encargado axuda ao responsable a atender os dereitos. Eira xa permite atendelos desde a propia
aplicación ([06-dereitos.md](06-dereitos.md)); se unha persoa se dirixe ao encargado, este reenvía a
solicitude ao responsable en ‹2 días hábiles›.

### 8. Axuda cos arts. 32 a 36 (art. 28.3.f)
O encargado axuda co cumprimento da seguridade, as brechas, a EIPD e a consulta previa.
**Brechas:** avisa ao responsable **sen dilación indebida** e en todo caso en ‹24 horas› desde que
a coñeza (art. 33.2), con toda a información dispoñible, para que o responsable poida notificar á
AEPD dentro das 72 horas ([07-brechas.md](07-brechas.md)).

### 9. Fin do servizo (art. 28.3.g)
Ao rematar, segundo elixa o responsable:
- **devolución:** a exportación íntegra do concello (Eira → Configuración → «Exportar / importar datos»,
  ficheiro ZIP) e despois supresión das copias; ou
- **supresión** de todos os datos, incluídas as copias, salvo obriga legal de conservación.
O encargado certifica por escrito a supresión en ‹prazo›.

### 10. Información e auditorías (art. 28.3.h)
O encargado pon á disposición do responsable toda a información necesaria para demostrar o
cumprimento e permite auditorías e inspeccións do responsable ou dun auditor autorizado por el.

### 11. Rexistro do encargado (art. 30.2)
O encargado leva o rexistro das categorías de tratamento que fai por conta do responsable.

### 12. Responsabilidade
Se o encargado trata os datos para fins propios ou incumpre as instrucións, é considerado
responsable dese tratamento (art. 28.10 RXPD, cita **non verificada** no contraste do 14/11/2026).

Asinado en ‹lugar›, o ‹data›.

| Polo responsable | Polo encargado |
|---|---|
| ‹nome, cargo e sinatura› | ‹nome, cargo e sinatura› |
