<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Contrato de encargado del tratamiento (art. 28 RGPD; art. 33 LOPDGDD)

> **MODELO DE EJEMPLO — requiere revisión del DPD y de los servicios jurídicos del concello.**

Para cuando Eira no la aloja el propio concello, sino **la diputación, una mancomunidad, una
empresa o engram**. El concello sigue siendo el responsable; quien aloja es el encargado y solo puede
tratar los datos siguiendo las instrucciones del concello. Si el encargado es otra administración, el
contrato puede ser un convenio u otro acto jurídico que vincule del mismo modo (art. 28.3).

Las cláusulas siguen las letras a–h del art. 28.3. Lo que va entre `‹ ›` lo completa el concello.

---

**Entre** el Concello de ‹nombre› (en adelante, «el responsable»), con NIF ‹›, representado por ‹›,
**y** ‹entidad› (en adelante, «el encargado»), con NIF ‹›, representado por ‹›.

### 1. Objeto y duración
El encargado presta el servicio de **alojamiento, mantenimiento y soporte técnico de la plataforma Eira**
para el servicio municipal de deportes, desde ‹fecha› hasta ‹fecha› o hasta el fin del contrato principal
‹referencia›.

### 2. Naturaleza, finalidad y tratamientos
- **Operaciones:** almacenamiento, copia de seguridad, actualización del software, consulta solo cuando
  lo pida el responsable para resolver una incidencia, y supresión al finalizar.
- **Tratamientos:** los del registro de actividades ([01-registro-actividades.md](01-registro-actividades.md)).
- **Categorías de datos:** identificativos y de contacto; reservas y pagos (sin datos de
  tarjeta); menores; **salud solo si la persona la guarda en su cuenta** (art. 9.2.a); registro de
  accidentes sin diagnósticos.
- **Interesados:** vecindad usuaria, menores y personas tutoras, personal del concello y de empresas
  contratadas (limpieza, mantenimiento).

### 3. Instrucciones documentadas (art. 28.3.a)
El encargado trata los datos **solo siguiendo las instrucciones documentadas del responsable**, también para
transferencias internacionales. Instrucciones mínimas:
1. No acceder a los datos personales salvo para resolver una incidencia pedida por el responsable.
   **Si el encargado es la diputación, usa el «acceso de soporte» de Eira**: lo autoriza el concello, con
   motivo, caduca a las 24 h, es solo de lectura y cada página queda en el registro de auditoría del concello.
2. **No transferir datos fuera de la Unión Europea.** Servidores y copias en ‹país de la UE›.
3. Mantener activada la purga automática (`booking_maintenance`) con los plazos que fije el responsable
   ([05-conservacion.md](05-conservacion.md)).
4. No activar adaptadores externos (correo, pasarela, Telegram, IA, teselas del mapa) sin instrucción
   escrita del responsable.
Si una instrucción infringe la normativa, el encargado avisa al responsable de inmediato.

### 4. Confidencialidad (art. 28.3.b)
Las personas autorizadas por el encargado se comprometen por escrito a la confidencialidad o están
sujetas a una obligación legal de confidencialidad.

### 5. Seguridad (art. 28.3.c y art. 32)
El encargado aplica las medidas del Esquema Nacional de Seguridad (RD 311/2022) que correspondan al
servicio (disposición adicional 1.ª LOPDGDD), como mínimo:
- cifrado en tránsito (HTTPS) y de las copias de seguridad; secretos (`EIRA_SECRET_KEY`,
  `EIRA_TOTP_KEY`, `EIRA_PADRON_SECRET`) fuera de la base de datos y del repositorio;
- control de acceso al servidor con doble factor y registro;
- copias de seguridad ‹periodicidad› y prueba de restauración ‹periodicidad›;
- actualizaciones de seguridad de Eira y del sistema en ‹plazo›;
- rotación de los registros del servidor (contienen direcciones IP).

### 6. Subencargados (art. 28.2 y 28.3.d)
El encargado no recurre a otro encargado sin **autorización previa por escrito** ‹específica /
general› del responsable. Lista autorizada: ‹proveedor de servidores (UE)›, ‹proveedor de correo›. Si es
general, avisa de los cambios para que el responsable pueda oponerse. El subencargado asume las mismas
obligaciones por contrato.

### 7. Ayuda con los derechos de las personas (art. 28.3.e)
El encargado ayuda al responsable a atender los derechos. Eira ya permite atenderlos desde la propia
aplicación ([06-derechos.md](06-derechos.md)); si una persona se dirige al encargado, este reenvía la
solicitud al responsable en ‹2 días hábiles›.

### 8. Ayuda con los arts. 32 a 36 (art. 28.3.f)
El encargado ayuda con el cumplimiento de la seguridad, las brechas, la EIPD y la consulta previa.
**Brechas:** avisa al responsable **sin dilación indebida** y en todo caso en ‹24 horas› desde que
tenga conocimiento de ella (art. 33.2), con toda la información disponible, para que el responsable pueda notificar a la
AEPD dentro de las 72 horas ([07-brechas.md](07-brechas.md)).

### 9. Fin del servicio (art. 28.3.g)
Al finalizar, según elija el responsable:
- **devolución:** la exportación íntegra del concello (Eira → Configuración → «Exportar / importar datos»,
  fichero ZIP) y después supresión de las copias; o
- **supresión** de todos los datos, incluidas las copias, salvo obligación legal de conservación.
El encargado certifica por escrito la supresión en ‹plazo›.

### 10. Información y auditorías (art. 28.3.h)
El encargado pone a disposición del responsable toda la información necesaria para demostrar el
cumplimiento y permite auditorías e inspecciones del responsable o de un auditor autorizado por él.

### 11. Registro del encargado (art. 30.2)
El encargado lleva el registro de las categorías de tratamiento que realiza por cuenta del responsable.

### 12. Responsabilidad
Si el encargado trata los datos para fines propios o incumple las instrucciones, es considerado
responsable de ese tratamiento (art. 28.10 RGPD, cita **no verificada** en el contraste del 14/11/2026).

Firmado en ‹lugar›, el ‹fecha›.

| Por el responsable | Por el encargado |
|---|---|
| ‹nombre, cargo y firma› | ‹nombre, cargo y firma› |
