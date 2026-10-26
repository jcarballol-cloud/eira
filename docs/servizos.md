<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Modelo de servizos arredor de Eira

Eira é software libre (EUPL-1.2): calquera concello, deputación ou empresa pode descargalo, instalalo e modificalo sen pagar licenzas. O modelo de sustentabilidade non vende o software: vende **servizos profesionais** arredor del, que tamén pode prestar calquera outra empresa (sen dependencia dun único provedor).

## Catálogo

| Servizo | Que inclúe | Para quen | Entregable |
|---|---|---|---|
| **Implantación** | Instalación na infraestrutura do concello ou da deputación (Docker ou servidor propio), dominio, TPV da entidade bancaria, correo, Cl@ve, padrón, carga das instalacións e tarifas, migración desde follas de cálculo | Concello ou deputación | Eira funcionando e cos datos cargados |
| **Formación** | Sesións curtas por perfil: persoal de oficina (modo básico), coordinación deportiva (modo avanzado), mantemento (app do operario), monitoras (tableta) e DPD (rexistro de brechas e privacidade) | Persoal municipal | Guías e gravacións propias |
| **Revisión de seguridade inicial de instalacións** | Visita a cada instalación co checklist «Revisión de seguridade inicial Eira» (pavimento, ancoraxes de porterías e canastras, iluminación, valado, sinalización, botiquín, DEA, vías de evacuación, accesibilidade física e protocolo na porta). Queda rexistrada en Eira como orde de mantemento pechada e a ficha mostra «Revisada o ‹data›» | Concello | Informe por instalación, ordes de traballo para o que hai que corrixir e cartel da porta impreso |
| **Asesoría de seguridade para clubs e eventos municipais** | Plan de autoprotección sinxelo, aforos, protocolo de accidentes e DEA, coordinación co 112, revisión antes de eventos (carreiras populares, torneos, festas) | Concello e clubs | Plan e checklist do evento |
| **Soporte** | Actualizacións de seguridade, copias, incidencias técnicas, axuda ao persoal. Por niveis de resposta | Concello ou deputación | Acordo de nivel de servizo |
| **Análise de datos** | Informes periódicos coa ocupación, o índice de vida activa e o observatorio (sempre agregados, n ≥ 10), propostas de horarios e de investimento, apoio para subvencións | Concello e deputación | Informe trimestral ou anual |

## Principios

- **Sen dependencia:** o código, a documentación e os formatos de exportación son abertos. Un concello pode cambiar de empresa de soporte ou facelo con medios propios.
- **Deputación como provedora:** o modelo pensado para concellos pequenos é que a deputación aloxe Eira para a súa rede e contrate (ou preste) estes servizos de forma agregada.
- **Os datos son do concello:** ningún servizo precisa acceso aos datos persoais salvo o soporte técnico, que usa o **acceso de soporte** de 24 h autorizado polo concello e rexistrado (ver `docs/rxpd/matriz.md`).
- **A revisión de seguridade non substitúe** as inspeccións obrigatorias nin os mantementos regulamentarios (DEA, instalacións eléctricas, piscinas). Axuda a telos ao día e a deixalos rexistrados.

## Relación co produto

| Servizo | Onde se apoia en Eira |
|---|---|
| Implantación | Alta asistida de concello e instalacións con plantillas, carga do padrón por CSV, portabilidade (exportar e importar) |
| Formación | Modo básico / avanzado da administración, botón de axuda «?» en cada pantalla, guía completa |
| Revisión de seguridade | Plantilla de mantemento «Revisión de seguridade inicial Eira», ficha de seguridade da instalación, cartel imprimible |
| Asesoría de seguridade | Protocolo de accidentes, DEA máis próximo, botón «Incidencia ou seguridade» con chamada ao 112 |
| Soporte | Acceso de soporte con caducidade e rexistro, rexistro de brechas |
| Análise de datos | Indicadores, observatorio, índice de vida activa, datos abertos |
