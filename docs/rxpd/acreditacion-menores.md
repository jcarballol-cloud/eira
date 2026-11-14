<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Acreditación das persoas monitoras e voluntarias con menores

**Versión en castelán:** [máis abaixo](#acreditación-de-las-personas-monitoras-y-voluntarias-con-menores).

> Documento orientativo. O concello debe revisalo cos seus servizos xurídicos e o seu DPD.

**Eira non garda nin sube o certificado do Rexistro Central de Delincuentes Sexuais.** Son datos
penais (art. 10 RGPD) e a comprobación corresponde á contratación do concello (LO 8/2021, LOPIVI,
art. 57; o art. 13.5 da LO 1/1996 foi suprimido pola LOPIVI). O rexistro chámase agora «Rexistro Central de
Delincuentes Sexuais e de Trata de Seres Humanos».

## Que fai Eira

1. A administración do concello marca en *Acreditacións (menores)*: **«Acreditación verificada na
   contratación (LO 8/2021, LOPIVI, art. 57)»**.
2. **Só se garda quen o marcou e a data.** Non hai campo para a data do certificado, o resultado nin
   ningún documento (`MinorsAccreditation`).
3. Ata marcalo, **a asignación a un grupo con menores queda bloqueada** cunha mensaxe clara. É un
   grupo con menores o que admite menores de 18 anos ou xa ten menores inscritos.
4. **Revisión configurable** (12 meses por defecto, *Configuración*): `booking_maintenance` avisa unha
   vez á administración. Mentres non se confirme de novo, non hai novas asignacións.
5. Permisos: **só o rol de administración do concello**. Nin o DPD, nin a deputación (tampouco co
   acceso de soporte), nin mantemento nin monitoras. Cada marca, retirada e bloqueo queda no rexistro
   de auditoría, sen datos penais.

## Límites coñecidos

- A marca é unha declaración do concello: Eira non pode comprobar que o certificado exista.
- As asignacións anteriores á v1.5 non se desfán soas: a ficha do grupo mostra o aviso ata marcalo.
- O bloqueo está na interface da xestión e no admin técnico (`Group.clean`). Quen escriba directamente
  na base de datos ou modifique o código queda fóra deste control.

---

# Acreditación de las personas monitoras y voluntarias con menores

> Documento orientativo. El concello debe revisarlo con sus servicios jurídicos y su DPD.

**Eira no guarda ni sube el certificado del Registro Central de Delincuentes Sexuales.** Son datos
penales (art. 10 RGPD) y la comprobación corresponde a la contratación del concello (LO 8/2021,
LOPIVI, art. 57).

- La administración del concello marca la casilla «Acreditación verificada na contratación».
- **Solo se guarda quién la marcó y la fecha**, sin fecha del certificado, resultado ni documento.
- Hasta entonces, **la asignación a un grupo con menores queda bloqueada** con un mensaje claro.
- **Revisión configurable** (12 meses por defecto): aviso a la administración; sin nueva confirmación
  no hay nuevas asignaciones.
- Solo el rol de administración del concello. Todo queda en el registro de auditoría, sin datos penales.
- La marca es una declaración del concello: Eira no puede comprobar que el certificado exista. Las
  asignaciones anteriores a la v1.5 no se deshacen solas: la ficha del grupo muestra el aviso.
