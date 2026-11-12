<!-- SPDX-License-Identifier: EUPL-1.2 -->
# LEEME: uso e requisitos legais de Eira

**Versión en castelán:** [LEEME.es.md](LEEME.es.md).

Eira é software libre (EUPL-1.2) para a xestión deportiva municipal. Este documento explica como
usala, que ten que facer un concello para despregala legalmente e que responsabilidade asume quen
a modifica.

> **Este documento é orientativo e non é asesoramento xurídico.** O concello debe revisar cos seus
> servizos xurídicos e co seu DPD todo o que se describe aquí.

## 1. Como usar

### Perfís

| Perfil | Ferramenta | Para que |
|---|---|---|
| Veciñanza | App móbil | Reservar, pagar, entrar, avisar, «Escoitar», aceptar documentos e ver o que aceptou |
| Mantemento | App móbil | Ordes de traballo sen cobertura e botón «Alerta» |
| Limpeza | App móbil | Tarefas e zonas con QR e botón «Alerta» |
| Persoa monitora | Tableta ou móbil | Asistencia, esforzo, probas físicas e botón «Alerta» |
| Administración do concello | Escritorio | Panel do día, instalacións, cobros, «Procedencia», documentos legais, acreditacións e botón «Alerta» |
| Persoa delegada de protección de datos (DPD) | Escritorio | Brechas, accidentes, auditoría e rexistro de aceptacións |
| Deputación ou mancomunidade | Escritorio | Comparar concellos, modelos de documentos legais e mobilidade entre concellos, sempre con datos agregados |

### Primeiros pasos para un concello

1. Crear o concello (a deputación, en «Novo concello», ou o admin técnico) e invitar a primeira
   persoa administradora.
2. En «Configuración»: datos de contacto, DPD, módulos, formas de pagamento e prazos.
3. Dar de alta as instalacións coas plantillas: horarios, tarifas, normas, DESA e forma de acceso.
4. En «Documentos legais»: adoptar ou adaptar os modelos, cubrir os datos do concello e publicar
   **despois de revisalos cos servizos xurídicos e o DPD**.
5. En «Persoal e códigos»: engadir mantemento, limpeza e monitoras. Para actividades con menores,
   marcar a acreditación (ver máis abaixo).
6. En «Alertas e peches»: designar as persoas responsables e os seus horarios.
7. En «Altas da app»: cargar o padrón (CSV) e empezar a dar de alta a veciñanza.

### Demo en 5 minutos

Sen instalar nada: <https://eira.engramlab.es> (datos ficticios que se restauran cada noite). No teu
ordenador:

```bash
docker compose up --build           # con Docker
python tools/tasks.py dev           # sen Docker (Python 3.12+)
```

Abre <http://127.0.0.1:8000> e escolle concello e perfil. A primeira vez con cada perfil sae unha guía
paso a paso (tamén en «?» → «Ver a guía»; se marcas «Non volver amosar a guía», xa non sae soa; nunha instalación real, actívaa o concello en «Configuración»). Non hai contrasinais: os concellos, as
persoas e os datos son ficticios. Proba:

1. *Uxía:* reserva o pádel, paga no TPV simulado, mira o código e pulsa «Escoitar».
2. *Concello de Vilardeiras:* panel do día, «Procedencia», «Documentos legais» e o grupo cunha
   monitora pendente de acreditación.
3. *Brais* (mantemento) e *Noela* (limpeza): botón «Alerta».
4. *Deputación:* «Mobilidade» e «Documentos legais».

Tes o guión completo en [docs/demo/guion-demo.md](docs/demo/guion-demo.md) e os pasos da demo en
[README.md](README.md).

## 2. Requisitos legais para despregala

Eira achega ferramentas, pero **non cumpre as obrigas polo concello**.

| Requisito | Quen e que | Onde axuda Eira |
|---|---|---|
| **Responsable do tratamento** | O concello é o responsable (art. 4.7 RGPD). Se a deputación ou unha empresa presta o servizo, fai falta un contrato de encargo (art. 28 RGPD) | [Matriz de datos](docs/rxpd/matriz.md), «Quen custodia os datos» |
| **DPD** | As administracións públicas deben designalo (art. 37 RGPD e art. 34 LOPDGDD) e comunicalo á AEPD | Campo de contacto en «Configuración», perfil DPD |
| **Rexistro de actividades** | O concello debe levalo e mantelo (art. 30 RGPD) | [Modelo de RAT](docs/rxpd/rat.md) |
| **EIPD** | Debe avaliarse e aprobarse antes de usar os tratamentos de maior risco (art. 35 RGPD) | [Plantilla](docs/rxpd/eipd-plantilla.md) e resumo público |
| **Documentos legais** | Privacidade, condicións, menores, imaxe, normas e saúde: revisalos e adaptalos | [Modelos de exemplo](docs/legal/modelos/), versións e rexistro de aceptacións |
| **Ordenanza** | Prezos públicos ou taxa: debe aprobarse polo procedemento que corresponda | [Modelo](docs/concello/ordenanza-modelo.md) |
| **Accesibilidade** | Declaración e canle de queixas (RD 1112/2018). As probas automáticas non substitúen unha revisión con persoas | [Declaración](docs/accesibilidade/declaracion.md) (na app, en «Accesibilidade», no pé de todas as pantallas) e [criterios](docs/accesibilidade/criterios.md); canle e reclamación en «Configuración» |
| **ENS** | Categorizar o sistema e aplicar as medidas (RD 311/2022). Non hai certificación incluída | [Seguridade e RGPD](docs/seguridade-rxpd.md), [despregamento](docs/despregamento.md) |
| **Acreditación de monitoras con menores** | O concello comproba na contratación o certificado do Rexistro Central de Delincuentes Sexuais (LO 1/1996, art. 13.5; LOPIVI). **Eira non o garda nin o sube** (art. 10 RGPD): só quen marcou a comprobación e a data | [Documentación](docs/rxpd/acreditacion-menores.md) |

## 3. Se modificas Eira

A EUPL-1.2 permite usar, modificar e redistribuír Eira, pero **sen ningunha garantía (art. 7) e sen
responsabilidade de quen a licenza, dentro do que permite a lei (art. 8)**.

Quen modifica Eira, ou desprega unha versión modificada, **asume a responsabilidade do resultado**,
especialmente en protección de datos e accesibilidade. Antes de poñela en servizo debe:

1. Revisar a EIPD, a matriz de datos e o rexistro de actividades.
2. Revisar os documentos legais se cambian os datos, as finalidades ou os destinatarios.
3. Manter as probas en verde: `python tools/tasks.py test`, `e2e` (con axe en tema claro e escuro),
   `lint` e `licenses`.
4. Publicar as modificacións baixo EUPL-1.2 cando as distribúa ou preste como servizo, nos termos da
   licenza.

## 4. Modelos de exemplo

**Ningún documento incluído en Eira é un documento legal válido.** Son modelos de exemplo: os
documentos legais, a ordenanza, a EIPD, o rexistro de actividades e os textos de privacidade. O
concello debe revisalos cos seus servizos xurídicos e o seu DPD antes de usalos.
