<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Rexistro de actividades de tratamento (modelo, art. 30 RXPD)

Modelo para que cada concello o adapte. **Responsable:** o concello que presta o servizo. **Encargado:** a deputación ou a empresa que aloxe Eira, cun contrato do art. 28. DPD: o do concello ou o da deputación (campo «contacto do DPD» na configuración).

| # | Actividade | Finalidade | Base xurídica | Categorías de interesados e datos | Destinatarios | Prazo de conservación | Medidas |
|---|---|---|---|---|---|---|---|
| 1 | Contas e acceso | Identificar a quen reserva ou se inscribe | Art. 6.1.e (misión de interese público, Lei 7/1985 art. 25.2.l) | Veciñanza: correo, nome para mostrar, teléfono e ano de nacemento (opcionais) | Ningún | Mentres a conta estea activa; borrado inmediato a petición | Acceso sen contrasinal (código dun só uso con HMAC), sesións de 14 días |
| 2 | Empadroamento e tarifas | Aplicar a tarifa de veciñanza ou reducida | 6.1.e e ordenanza fiscal | Si/non empadroada, colectivo e data de validez | Ningún | Ata a revogación ou a caducidade | Non se gardan padrón nin documentos |
| 3 | Reservas e acceso ás instalacións | Xestionar o uso e abrir a porta | 6.1.e | Reservas, códigos temporais e eventos de acceso | Persoal de mantemento (só instalación e hora) | 2 anos; agregados sen prazo | Códigos sen conexión, rexistro de auditoría |
| 4 | Cobros e devolucións | Cobrar taxas e prezos públicos | 6.1.c e 6.1.e | Referencia, importe e estado | Entidade financeira (TPV) e Intervención | 6 anos (normativa tributaria) | Notificación asinada servidor a servidor; sen datos de tarxeta |
| 5 | Escolas deportivas | Inscrición, asistencia e esforzo percibido | 6.1.e; menores: consentimento da familia (art. 7 LOPDGDD) para esforzo e probas | Menores e adultos: nome, ano, asistencia, hora de entrada e RPE. **Apelidos como dato da inscrición** (achégaos o concello desde o padrón ou a folla de inscrición; non os enche a monitora) | Monitor/a do grupo: **só nome e primeiro apelido** na tableta. O nome completo só na administración do concello | Tempada + 1 ano; observatorio só agregado | Seudónimo HMAC, n ≥ 10 nas estatísticas |
| 6 | Imaxe | Fotos en actividades e comunicacións | Consentimento (6.1.a), revogable | Persoas inscritas | Comunicación municipal | Ata a revogación | Icona e filtro para o persoal |
| 7 | Incidencias e mantemento | Reparar avarías | 6.1.e | Descrición, foto sen metadatos e quen avisa | Persoal de mantemento | 2 anos | Fotos reencodadas sen EXIF/GPS |
| 8 | Valoracións | Mellorar o servizo | 6.1.e | Valoración, etiquetas e comentario | Concello (sen nome) | 2 anos | Os comentarios móstranse sen identidade |
| 9 | Saúde (opcional) | Recomendacións persoais de hidratación e enerxía | Consentimento explícito (art. 9.2.a), só se se garda na conta | Peso e idade | Ningún (nin o persoal) | Ata a revogación | Por defecto no dispositivo; excluído de exportacións e observatorio |
| 10 | Solicitudes da app | Enviar a app e o código de empadroamento | 6.1.e | Nome, correo, ano e código postal | Ningún | 12 meses | Consulta ao padrón por adaptador; só se garda si/non |

| 11 | Acceso de soporte da deputación | Asistencia técnica ao concello | 6.1.e e contrato de encargo (art. 28) | Os datos persoais do concello que consulte durante o acceso | Persoal da deputación autorizado | O acceso caduca ás 24 h; o rexistro de consultas consérvase 2 anos | Por defecto a deputación só ve agregados e anónimos. Acceso autorizado polo concello, con motivo, que caduca ás 24 h e se pode revogar. Cada páxina queda en AuditLog e o concello recibe un aviso no primeiro uso |

Transferencias internacionais: **ningunha**. Os servizos externos (correo, pasarela, teselas, IA) van detrás de adaptadores e poden aloxarse na deputación.
