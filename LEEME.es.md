<!-- SPDX-License-Identifier: EUPL-1.2 -->
# LÉEME: uso y requisitos legales de Eira

**Versión en gallego:** [LEEME.md](LEEME.md).

Eira es software libre (EUPL-1.2) para la gestión deportiva municipal. Este documento explica cómo
usarla, qué debe hacer un concello para desplegarla legalmente y qué responsabilidad asume quien
la modifica.

> **Este documento es orientativo y no es asesoramiento jurídico.** El concello debe revisar con sus
> servicios jurídicos y con su DPD todo lo que aquí se describe.

## 1. Cómo usar

### Perfiles

| Perfil | Herramienta | Para qué |
|---|---|---|
| Vecindario | App móvil | Reservar, pagar, entrar, avisar, «Escoitar», aceptar documentos y ver lo que aceptó |
| Mantenimiento | App móvil | Órdenes de trabajo sin cobertura y botón «Alerta» |
| Limpieza | App móvil | Tareas y zonas con QR y botón «Alerta» |
| Persona monitora | Tableta o móvil | Asistencia, esfuerzo, pruebas físicas y botón «Alerta» |
| Administración del concello | Escritorio | Panel del día, instalaciones, cobros, «Procedencia», documentos legales, acreditaciones y botón «Alerta» |
| Persona delegada de protección de datos (DPD) | Escritorio | Brechas, accidentes, auditoría y registro de aceptaciones |
| Diputación o mancomunidad | Escritorio | Comparar concellos, modelos de documentos legales y movilidad entre concellos, siempre con datos agregados |

### Primeros pasos para un concello

1. Crear el concello (la diputación, en «Novo concello», o el admin técnico) e invitar a la primera
   persona administradora.
2. En «Configuración»: datos de contacto, DPD, módulos, formas de pago y plazos.
3. Dar de alta las instalaciones con las plantillas: horarios, tarifas, normas, DESA y forma de acceso.
4. En «Documentos legales»: adoptar o adaptar los modelos, rellenar los datos del concello y publicar
   **después de revisarlos con los servicios jurídicos y el DPD**.
5. En «Personal y códigos»: añadir mantenimiento, limpieza y monitoras. Para actividades con menores,
   marcar la acreditación (ver más abajo).
6. En «Alertas y cierres»: designar a las personas responsables y sus horarios.
7. En «Altas de la app»: cargar el padrón (CSV) y empezar a dar de alta al vecindario.

### Demo en 5 minutos

Sin instalar nada: <https://eira.engramlab.es> (datos ficticios que se restauran cada noche). En tu
ordenador:

```bash
docker compose up --build           # con Docker
python tools/tasks.py dev           # sin Docker (Python 3.12+)
```

Abre <http://127.0.0.1:8000> y elige concello y perfil. La primera vez con cada perfil sale una guía
paso a paso (también en «?» → «Ver la guía»; si marcas «No volver a mostrar la guía», ya no sale sola; en una instalación real, la activa el concello en «Configuración»). No hay contraseñas: los concellos, las
personas y los datos son ficticios. Prueba:

1. *Uxía:* reserva el pádel, paga en el TPV simulado, mira el código y pulsa «Escoitar».
2. *Concello de Vilardeiras:* panel del día, «Procedencia», «Documentos legales» y el grupo con una
   monitora pendiente de acreditación.
3. *Brais* (mantenimiento) y *Noela* (limpieza): botón «Alerta».
4. *Diputación:* «Movilidad» y «Documentos legales».

El guion completo está en [docs/demo/guion-demo.md](docs/demo/guion-demo.md) y los pasos de la demo en
[README.md](README.md).

## 2. Requisitos legales para desplegarla

Eira aporta herramientas, pero **no cumple las obligaciones por el concello**.

| Requisito | Quién y qué | Dónde ayuda Eira |
|---|---|---|
| **Responsable del tratamiento** | El concello es el responsable (art. 4.7 RGPD). Si la diputación o una empresa presta el servicio, hace falta un contrato de encargo (art. 28 RGPD) | [Matriz de datos](docs/rxpd/matriz.md), «Quien custodia los datos» |
| **DPD** | Las administraciones públicas deben designarlo (art. 37 RGPD y art. 34 LOPDGDD) y comunicarlo a la AEPD | Campo de contacto en «Configuración», perfil DPD |
| **Registro de actividades** | El concello debe llevarlo y mantenerlo (art. 30 RGPD) | [Modelo de RAT](docs/rxpd/rat.md) |
| **EIPD** | Debe evaluarse y aprobarse antes de usar los tratamientos de mayor riesgo (art. 35 RGPD) | [Plantilla](docs/rxpd/eipd-plantilla.md) y resumen público |
| **Documentos legales** | Privacidad, condiciones, menores, imagen, normas y salud: revisarlos y adaptarlos | [Modelos de ejemplo](docs/legal/modelos/), versiones y registro de aceptaciones |
| **Ordenanza** | Precios públicos o tasa: debe aprobarse por el procedimiento que corresponda | [Modelo](docs/concello/ordenanza-modelo.md) |
| **Accesibilidad** | Declaración y canal de quejas (RD 1112/2018). Las pruebas automáticas no sustituyen una revisión con personas | [Declaración](docs/accesibilidade/declaracion.md) (en la app, en «Accesibilidade», en el pie de todas las pantallas) y [criterios](docs/accesibilidade/criterios.md); canal y reclamación en «Configuración» |
| **ENS** | Categorizar el sistema y aplicar las medidas (RD 311/2022). No incluye certificación | [Seguridad y RGPD](docs/seguridade-rxpd.md), [despliegue](docs/despregamento.md) |
| **Acreditación de monitoras con menores** | El concello comprueba en la contratación el certificado del Registro Central de Delincuentes Sexuales (LO 1/1996, art. 13.5; LOPIVI). **Eira no lo guarda ni lo sube** (art. 10 RGPD): solo quién marcó la comprobación y la fecha | [Documentación](docs/rxpd/acreditacion-menores.md) |

## 3. Si modificas Eira

La EUPL-1.2 permite usar, modificar y redistribuir Eira, pero **sin ninguna garantía (art. 7) y sin
responsabilidad de quien la licencia, dentro de lo que permite la ley (art. 8)**.

Quien modifica Eira, o despliega una versión modificada, **asume la responsabilidad del resultado**,
especialmente en protección de datos y accesibilidad. Antes de ponerla en servicio debe:

1. Revisar la EIPD, la matriz de datos y el registro de actividades.
2. Revisar los documentos legales si cambian los datos, las finalidades o los destinatarios.
3. Mantener las pruebas en verde: `python tools/tasks.py test`, `e2e` (con axe en tema claro y oscuro),
   `lint` y `licenses`.
4. Publicar las modificaciones bajo EUPL-1.2 cuando las distribuya o preste como servicio, en los
   términos de la licencia.

## 4. Modelos de ejemplo

**Ningún documento incluido en Eira es un documento legal válido.** Son modelos de ejemplo: los
documentos legales, la ordenanza, la EIPD, el registro de actividades y los textos de privacidad. El
concello debe revisarlos con sus servicios jurídicos y su DPD antes de usarlos.
