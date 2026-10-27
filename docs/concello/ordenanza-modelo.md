<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Modelo de ordenanza reguladora do prezo público polo uso das instalacións deportivas municipais

> **Aviso:** modelo orientativo; require informe dos servizos xurídicos e de Intervención do concello.
> Non é asesoramento xurídico. Hai que adaptalo á situación do concello: estudo económico de custos,
> ordenanza xeral de prezos públicos ou fiscal e regulamento de uso das instalacións, se os hai.

**Versión en castelán:** [máis abaixo](#versión-en-castellano).

**Como ler este modelo:**

- Os textos entre `‹ ›` hai que encher ou escoller (importes, prazos, colectivos).
- Entre corchetes **[Eira: …]** vai o **campo de configuración de Eira** que aplica ese artigo. Así a
  ordenanza aprobada e a configuración da aplicación din o mesmo. Os campos do concello están en
  *Xestión → Configuración*; os da instalación, en *Xestión → Instalacións → ‹instalación›*.
- Se algo **non o fai Eira**, dise: **[Eira: non o fai]**. Nese caso o concello xestiónao fóra da aplicación.
- A **variante de taxa** está ao final de cada artigo cando cambia algo, e completa na sección 3.

### Prezo público ou taxa?

| | Prezo público (arts. 41 a 47 TRLRHL) | Taxa (arts. 20 e seguintes TRLRHL) |
|---|---|---|
| Cando | Servizo de solicitude voluntaria **e** que tamén presta o sector privado no municipio (art. 41 en relación co 20.1.B) | Se falta algunha desas dúas condicións, ou se o concello prefire a figura tributaria |
| Natureza | Ingreso de dereito público non tributario | Tributo |
| Aprobación | Pleno (pode delegar na Xunta de Goberno Local, art. 47 TRLRHL) | Pleno, con aprobación provisional, exposición pública de 30 días hábiles, aprobación definitiva e publicación no BOP (arts. 15 a 19 TRLRHL) |
| Contía | Cubrir como mínimo o custo do servizo; pode ser menor por razóns sociais, benéficas, culturais ou de interese público, consignando a diferenza no orzamento (art. 44) | Non pode superar o custo real ou previsible do servizo (art. 24.2); pode ter en conta a capacidade económica (art. 24.4) |
| Cobro forzoso | Vía de constrinximento (art. 46.3) | Vía de constrinximento |

Para Eira **é igual**: as tarifas, descontos, prazos e devolucións configúranse da mesma maneira. Só
cambian os textos legais (os recibos din «prezo público» ou «taxa» segundo o modelo que se aprobe).

---

## 1. Texto da ordenanza (prezo público)

### Artigo 1. Fundamento e obxecto

1. Ao abeiro do disposto nos artigos 41 a 47 do Real decreto lexislativo 2/2004, do 5 de marzo, polo
   que se aproba o texto refundido da Lei reguladora das facendas locais (TRLRHL), e no artigo 25.2.l)
   da Lei 7/1985, do 2 de abril, reguladora das bases do réxime local, o Concello de ‹nome› establece
   o prezo público polo uso das instalacións deportivas municipais.
2. É obxecto desta ordenanza a utilización das instalacións deportivas relacionadas no anexo I, por
   franxas horarias, mediante reserva previa.
3. As normas de uso de cada instalación (horarios, material, comportamento) regúlanse no regulamento
   de uso ou nas normas aprobadas para cada instalación, que a persoa acepta ao reservar.
   [Eira: *Instalación → Normas* (versionadas; cada reserva garda a versión aceptada)]

*Taxa:* «… establece a taxa pola utilización privativa ou o aproveitamento especial das instalacións
deportivas municipais (art. 20.3 TRLRHL) / pola prestación do servizo de instalacións deportivas
(art. 20.4.o TRLRHL)».

### Artigo 2. Persoas obrigadas ao pagamento

1. Están obrigadas ao pagamento as persoas físicas ou xurídicas que soliciten e reserven o uso das
   instalacións, ou que as utilicen sen reserva cando esta sexa obrigatoria.
2. Cando a reserva se faga en nome dunha persoa menor ou dun grupo, responde do pagamento a persoa
   que a fai. [Eira: a persoa titular da reserva (`Booking.user`); *Xestión → Reservar por alguén* para as feitas no mostrador ou por teléfono]

*Taxa:* «Son suxeitos pasivos, en concepto de contribuíntes, as persoas físicas e xurídicas e as
entidades do art. 35.4 da Lei 58/2003, xeral tributaria, que soliciten ou resulten beneficiadas…» (art. 23 TRLRHL).

### Artigo 3. Tarifas

1. As contías son as do anexo II, por franxa horaria e instalación.
2. Distínguense as tarifas para:
   a) **persoas empadroadas** no Concello de ‹nome›;
   b) **persoas non empadroadas**.
   [Eira: *Instalación → Tarifas*: colectivos `resident` e `non_resident` (`Tariff.audience`)]
3. O empadroamento acredítase coa validación do concello (código de empadroamento, consulta ao
   padrón ou comprobación no mostrador). Ata que se valide aplícase a tarifa de non empadroada.
   [Eira: `Residency` (método e data, sen gardar o padrón); *Xestión → Persoal e códigos → Códigos de empadroamento*; *Xestión → Altas da app*]
4. ‹Opcional› As persoas empadroadas noutros concellos da ‹deputación/mancomunidade› con convenio
   pagan a tarifa de non empadroada. [Eira: *Configuración → Concellos próximos* (`network_open`, `network_max_active`, `network_advance_days`)]
5. As tarifas inclúen o IVE cando proceda. ‹Comprobar con Intervención a suxeición ao IVE.›

### Artigo 4. Suplemento de iluminación

1. Nas instalacións exteriores con iluminación artificial, as franxas que precisen luz levan un
   suplemento de ‹importe› € por franxa.
2. Considérase que unha franxa precisa luz ‹escoller›: a) cando comeza despois do solpor ou remata
   antes do amencer, segundo as táboas astronómicas para ‹localidade›; ou b) entre as ‹21:00› e as
   ‹08:00› horas.
3. A persoa usuaria pode pedir a luz noutras franxas, co mesmo suplemento.
   [Eira: *Instalación → Datos → Reserva e pagamento* (`lighting_supplement_cents`); *Configuración → Suplemento de iluminación* (`lighting_rule`: `sunset` ou `fixed`, `lighting_from`, `lighting_until`); a reserva garda se se pediu luz (`needs_light`)]

### Artigo 5. Abonos e bonos

1. **Abono:** dá dereito, durante o seu período de validez, a un desconto do ‹%› sobre a tarifa que
   corresponda. Tipos e prezos no anexo III (xeral, mocidade, maiores, familiar…).
   [Eira: *Xestión → Abonos e carné → Tipos de abono* (`PassType`: `price_cents`, `valid_days`, `discount_pct`)]
2. **Bono:** conxunto de ‹10› usos dunha instalación ou de calquera instalación que o admita, cunha
   validez de ‹365› días desde a compra. [Eira: *Xestión → Cobros → Bonos* (`VoucherType`: `uses`, `price_cents`, `valid_days`, instalación opcional)]
3. Os abonos e bonos son persoais e intransferibles e acredítanse co carné municipal (dixital ou
   impreso). [Eira: carné con QR dinámico; *Xestión → Abonos e carné → Lector*]
4. Os usos dun bono que non se consuman dentro do prazo de validez non se reembolsan, agás que a
   instalación pechase por causa imputable ao concello.

### Artigo 6. Exencións e bonificacións

1. **Colectivos.** Aplicaranse as tarifas reducidas do anexo II a:
   a) mocidade ata ‹25› anos empadroada; [Eira: colectivo `youth`]
   b) persoas maiores de ‹65› anos empadroadas; [Eira: colectivo `senior`]
   c) persoas con discapacidade igual ou superior ao 33 %, persoas en desemprego e familias
      numerosas ou monoparentais, acreditándoo ante o concello. [Eira: colectivo `reduced` + validación do persoal en *Persoal e códigos → Tarifa reducida* (`Eligibility`: colectivo e data de fin; **non se garda a documentación**)]
2. **Franxas de baixa demanda.** Nas franxas que o concello sinale como de baixa demanda aplicarase
   un desconto do ‹20› % para favorecer o uso repartido das instalacións.
   [Eira: *Configuración → Regras de reserva* (`low_demand_discount_pct`); as franxas aparecen marcadas con ★ na grella]
3. Os descontos non son acumulables entre si agás ‹o do abono, que se aplica despois da tarifa e do desconto de baixa demanda›.
   [Eira: orde de cálculo fixa: tarifa do colectivo → baixa demanda → abono; suplemento de luz á parte]
4. **Exencións.** Quedan exentas: a) as actividades organizadas polo propio concello e as escolas
   deportivas municipais; b) ‹os centros educativos públicos do municipio en horario lectivo›;
   c) ‹as entidades deportivas inscritas no rexistro municipal, segundo convenio›.
   [Eira: a) o concello reserva sen custo desde a xestión ou as actividades bloquean a franxa; b) e c) **[Eira: non hai un campo de «entidade exenta»]**: faise como reserva no mostrador coa forma de pagamento «Gratuíta» (`free`) ou cunha tarifa 0 no colectivo `reduced`]
5. De acordo co art. 44.2 TRLRHL, cando as contías queden por debaixo do custo do servizo, o
   orzamento consignará a diferenza.

*Taxa:* as exencións e bonificacións en tributos locais só poden ser as previstas en normas con
rango de lei ou en tratados internacionais (art. 9 TRLRHL); pódese ter en conta a capacidade
económica (art. 24.4). Revisar con Intervención os apartados 1.c e 4.

### Artigo 7. Nacemento da obriga (devengo) e pagamento

1. A obriga de pagar nace co inicio da utilización da instalación. De acordo co art. 46.1 TRLRHL,
   esíxese o depósito previo do importe íntegro no momento de facer a reserva.
2. Formas de pagamento:
   a) **en liña** mediante TPV virtual no momento de reservar; [Eira: forma `tpv`]
   b) **na oficina** ‹enderezo e horario›, dentro das ‹48› horas seguintes á reserva e sempre antes do
      inicio da franxa. Se non se paga nese prazo, a reserva anúlase e a franxa queda libre;
      [Eira: forma `office`; *Configuración → Formas de pagamento* (`office_payment_hours`)]
   c) con **bono**, descontando un uso. [Eira: forma `voucher`]
   ‹Opcional› d) **aprazado** para ‹entidades›, mediante liquidación ‹mensual›. [Eira: forma `deferred`, desactivada por defecto]
   [Eira: formas admitidas en `payment_methods` do concello; cada instalación pode restrinxilas]
3. O xustificante de pagamento é o recibo que emite o sistema. [Eira: recibo PDF de cada reserva]
4. As débedas non pagadas poderán esixirse pola vía de constrinximento (art. 46.3 TRLRHL).
   [Eira: non o fai; o concello tramítao co seu servizo de recadación]

*Taxa:* «A taxa devéngase cando se presenta a solicitude de reserva, que non se tramitará sen o
pagamento previo (art. 26.1.b TRLRHL). Esíxese en réxime de autoliquidación (art. 27.1)».

### Artigo 8. Reservas

1. As reservas poden facerse con ‹14› días de antelación como máximo. [Eira: `max_advance_days`]
2. Cada persoa pode ter ‹4› reservas activas como máximo. [Eira: `max_active_bookings`]
3. A reserva pode requirir a confirmación da asistencia ‹120› minutos antes do inicio; se non se
   confirma e hai persoas en lista de espera, a franxa ofrécese a estas.
   [Eira: *Configuración → Confirmación e lista de espera* (`confirm_release_enabled`, `confirm_release_minutes`, `waitlist_offer_minutes`)]

### Artigo 9. Devolucións e cancelacións

1. **Por causa non imputable á persoa usuaria** (peche, avaría, condicións meteorolóxicas que impidan
   o uso, actos organizados polo concello…) devolverase o importe íntegro (art. 46.2 TRLRHL), ou o uso
   do bono. [Eira: *Xestión → Peches*: ao aplicar un peche, as reservas afectadas anúlanse con devolución íntegra e aviso]
2. **Cancelación pola persoa usuaria:**
   a) con ‹24› horas ou máis de antelación: devolución íntegra; [Eira: `cancellation_hours`]
   b) con menos antelación: devolverase o importe menos unha penalización do ‹50› %;
      [Eira: `late_cancel_penalty_pct`]
   c) se a franxa cancelada fóra de prazo se volve reservar a través da lista de espera, devolverase
      tamén a penalización. [Eira: lista de espera (v1.2), devolución automática da penalización]
3. Non se devolve nada unha vez comezada a franxa.
4. As devolucións fanse pola mesma vía do pagamento (TPV ou oficina) no prazo de ‹15› días.
   [Eira: devolución no TPV simulado/adaptador `payments`; na oficina, rexístraa o persoal]

### Artigo 10. Non presentación

1. Se a persoa non se presenta nin cancela, non procede devolución ningunha, por ser a causa
   imputable a ela. Considérase non presentada se non rexistra o acceso nos ‹15› minutos seguintes ao
   inicio. [Eira: estado «Non presentada» (`no_show`); `no_show_grace_minutes`; nas instalacións de nivel 0 (QR voluntario) non se marca]
2. ‹Opcional› Se hai lista de espera, a franxa poderá liberarse ‹15› minutos despois do inicio sen
   rexistro de acceso. [Eira: `checkin_release_minutes` (só niveis 0, 2 e 3)]
3. ‹Opcional› A reiteración de non presentacións (‹3› nun período de ‹60› días) poderá levar a
   suspensión do dereito de reserva en liña durante ‹30› días, previa audiencia, conforme ao
   regulamento de uso. **[Eira: non o fai]** — Eira rexistra as non presentacións e o concello pode
   consultalas, pero non bloquea reservas automaticamente. Esta medida é unha norma de uso, non un
   elemento do prezo: recoméndase regulala no regulamento de uso e non na ordenanza fiscal.

### Artigo 11. Xestión

1. A xestión e o cobro corresponden ao servizo municipal de deportes, en coordinación coa Tesouraría.
2. O concello poderá utilizar medios electrónicos para a reserva, o pagamento, o acceso e os avisos.
   O tratamento de datos persoais rexerase polo Regulamento (UE) 2016/679 e a Lei orgánica 3/2018.
   [Eira: *Configuración → Textos legais*; «Quen custodia os teus datos»]

### Disposición derrogatoria

Queda derrogada a ‹ordenanza anterior› e cantas disposicións municipais se opoñan a esta.

### Disposición derradeira

Esta ordenanza entrará en vigor ‹o día seguinte ao da súa publicación íntegra no Boletín Oficial da
Provincia› e permanecerá vixente ata a súa modificación ou derrogación expresa.

*Taxa:* aprobación provisional polo Pleno, exposición pública de 30 días hábiles, aprobación definitiva
e publicación do texto íntegro no BOP (art. 17 TRLRHL).

### Anexo I. Instalacións

| Instalación | Enderezo | Tipo | Franxa |
|---|---|---|---|
| ‹Pavillón municipal› | ‹…› | ‹pavillón› | ‹60› min |

[Eira: *Xestión → Instalacións* (nome, enderezo, tipo, `slot_minutes`)]

### Anexo II. Tarifas por franxa (€)

| Instalación | Empadroada | Non empadroada | Mocidade | Maiores | Colectivos (6.1.c) | Suplemento de luz |
|---|---|---|---|---|---|---|
| ‹Pista de pádel› | ‹4,00› | ‹8,00› | ‹3,00› | ‹3,00› | ‹2,00› | ‹2,00› |

[Eira: *Instalación → Tarifas* (`resident`, `non_resident`, `youth`, `senior`, `reduced`) e *Instalación → Datos* (`lighting_supplement_cents`)]

### Anexo III. Abonos e bonos

| Tipo | Prezo | Validez | Desconto ou usos |
|---|---|---|---|
| ‹Abono xeral› | ‹60,00 €› | ‹365 días› | ‹10 %› |
| ‹Bono 10 usos pádel› | ‹35,00 €› | ‹365 días› | ‹10 usos› |

---

## 2. Táboa de correspondencia ordenanza → Eira

| Artigo | Campo de Eira | Onde |
|---|---|---|
| 1.3 Normas de uso | `RulesVersion` | Instalación → Normas |
| 3 Tarifas | `Tariff.audience` + `price_cents` | Instalación → Tarifas |
| 3.3 Empadroamento | `Residency` | Persoal e códigos; Altas da app |
| 3.4 Rede | `network_open`, `network_max_active`, `network_advance_days` | Configuración → Concellos próximos |
| 4 Luz | `lighting_supplement_cents`, `lighting_rule`, `lighting_from`, `lighting_until` | Instalación → Datos; Configuración → Suplemento de iluminación |
| 5.1 Abonos | `PassType` (`price_cents`, `valid_days`, `discount_pct`) | Abonos e carné |
| 5.2 Bonos | `VoucherType` (`uses`, `price_cents`, `valid_days`) | Cobros → Bonos |
| 6.1 Colectivos | `Tariff.audience` (`youth`, `senior`, `reduced`) + `Eligibility` | Instalación → Tarifas; Persoal e códigos |
| 6.2 Baixa demanda | `low_demand_discount_pct` | Configuración → Regras de reserva |
| 6.4 Exencións | forma de pagamento `free` ou tarifa 0 | Configuración → Formas de pagamento |
| 7 Pagamento | `payment_methods`, `office_payment_hours` | Configuración → Formas de pagamento |
| 8 Reservas | `max_advance_days`, `max_active_bookings`, `confirm_release_*`, `waitlist_offer_minutes` | Configuración |
| 9 Devolucións | `cancellation_hours`, `late_cancel_penalty_pct`; peches con devolución íntegra | Configuración; Peches |
| 10 Non presentación | `no_show_grace_minutes`, `checkin_release_minutes` | Configuración |
| 10.3 Suspensión | — | **Non o fai Eira** |
| 7.4 Constrinximento | — | **Non o fai Eira** (recadación) |

## 3. Variante de taxa (resumo dos cambios)

1. **Título:** «Ordenanza fiscal reguladora da taxa pola utilización das instalacións deportivas municipais».
2. **Fundamento (art. 1):** arts. 15 a 19 e 20 a 27 TRLRHL; art. 20.4.o (servizos de instalacións
   deportivas) ou 20.3 (utilización privativa ou aproveitamento especial do dominio público).
3. **Suxeitos pasivos (art. 2):** art. 23 TRLRHL e art. 35.4 da Lei 58/2003, xeral tributaria.
4. **Cota (art. 3):** a contía non pode exceder o custo real ou previsible do servizo (art. 24.2);
   precisa **informe técnico-económico** (art. 25).
5. **Exencións e bonificacións (art. 6):** só as previstas en lei (art. 9 TRLRHL); os criterios de
   capacidade económica (art. 24.4) son os que permiten as tarifas reducidas para colectivos.
6. **Devengo e pagamento (art. 7):** devengo coa solicitude e pagamento previo (art. 26.1.b),
   autoliquidación (art. 27.1). Devolución se o servizo non se presta por causas non imputables ao
   suxeito pasivo (art. 26.3).
7. **Infraccións e sancións:** remisión á Lei xeral tributaria (arts. 178 e seguintes).
8. **Tramitación:** aprobación provisional, exposición pública de 30 días hábiles con anuncio no BOP
   e nun diario de maior difusión (se o concello ten máis de 10 000 habitantes), aprobación definitiva
   e publicación íntegra (art. 17).

Na configuración de Eira **non cambia nada**; revisar só os textos legais e o recibo.

---

<a id="versión-en-castellano"></a>

# Versión en castellano: Modelo de ordenanza reguladora del precio público por el uso de las instalaciones deportivas municipales

> **Aviso:** modelo orientativo; requiere informe de los servicios jurídicos y de Intervención del ayuntamiento.
> No es asesoramiento jurídico. Hay que adaptarlo a la situación del ayuntamiento: estudio económico de
> costes, ordenanza general de precios públicos o fiscal y reglamento de uso de las instalaciones, si existen.

**Cómo leer este modelo:** los textos entre `‹ ›` se rellenan o eligen. Entre corchetes **[Eira: …]**
va el **campo de configuración de Eira** que aplica cada artículo (los del ayuntamiento, en
*Xestión → Configuración*; los de la instalación, en *Xestión → Instalacións*). Si algo **no lo hace
Eira**, se indica: **[Eira: no lo hace]**. La variante de **tasa** va al final de cada artículo cuando
cambia algo, y completa en la sección 3.

### ¿Precio público o tasa?

| | Precio público (arts. 41 a 47 TRLRHL) | Tasa (arts. 20 y siguientes TRLRHL) |
|---|---|---|
| Cuándo | Servicio de solicitud voluntaria **y** que también presta el sector privado en el municipio (art. 41 en relación con el 20.1.B) | Si falta alguna de esas condiciones, o si el ayuntamiento prefiere la figura tributaria |
| Naturaleza | Ingreso de derecho público no tributario | Tributo |
| Aprobación | Pleno (puede delegar en la Junta de Gobierno Local, art. 47 TRLRHL) | Pleno, con aprobación provisional, exposición pública de 30 días hábiles, aprobación definitiva y publicación en el BOP (arts. 15 a 19 TRLRHL) |
| Cuantía | Cubrir como mínimo el coste del servicio; puede ser menor por razones sociales, benéficas, culturales o de interés público, consignando la diferencia en el presupuesto (art. 44) | No puede superar el coste real o previsible del servicio (art. 24.2); puede tener en cuenta la capacidad económica (art. 24.4) |
| Cobro forzoso | Vía de apremio (art. 46.3) | Vía de apremio |

Para Eira **es igual**: tarifas, descuentos, plazos y devoluciones se configuran de la misma manera.

## 1. Texto de la ordenanza (precio público)

### Artículo 1. Fundamento y objeto

1. Al amparo de los artículos 41 a 47 del Real Decreto Legislativo 2/2004, de 5 de marzo, por el que
   se aprueba el texto refundido de la Ley Reguladora de las Haciendas Locales (TRLRHL), y del artículo
   25.2.l) de la Ley 7/1985, de 2 de abril, reguladora de las Bases del Régimen Local, el Ayuntamiento
   de ‹nombre› establece el precio público por el uso de las instalaciones deportivas municipales.
2. Es objeto de esta ordenanza la utilización de las instalaciones del anexo I, por franjas horarias,
   mediante reserva previa.
3. Las normas de uso de cada instalación se regulan en el reglamento de uso o en las normas aprobadas
   para cada instalación, que la persona acepta al reservar. [Eira: *Instalación → Normas* (versionadas)]

*Tasa:* «… establece la tasa por la utilización privativa o el aprovechamiento especial de las
instalaciones deportivas municipales (art. 20.3 TRLRHL) / por la prestación del servicio de
instalaciones deportivas (art. 20.4.o TRLRHL)».

### Artículo 2. Personas obligadas al pago

1. Están obligadas al pago las personas físicas o jurídicas que soliciten y reserven el uso de las
   instalaciones, o que las utilicen sin reserva cuando esta sea obligatoria.
2. Cuando la reserva se haga en nombre de una persona menor o de un grupo, responde del pago la
   persona que la hace. [Eira: titular de la reserva (`Booking.user`); *Xestión → Reservar por alguén*]

*Tasa:* sujetos pasivos contribuyentes del art. 23 TRLRHL y art. 35.4 de la Ley 58/2003, General Tributaria.

### Artículo 3. Tarifas

1. Las cuantías son las del anexo II, por franja horaria e instalación.
2. Se distinguen tarifas para: a) **personas empadronadas** en el municipio; b) **personas no
   empadronadas**. [Eira: *Instalación → Tarifas*: colectivos `resident` y `non_resident`]
3. El empadronamiento se acredita con la validación del ayuntamiento (código de empadronamiento,
   consulta al padrón o comprobación en el mostrador). Hasta que se valide, se aplica la tarifa de no
   empadronada. [Eira: `Residency` (método y fecha, sin guardar el padrón)]
4. ‹Opcional› Las personas empadronadas en otros ayuntamientos de la ‹diputación/mancomunidad› con
   convenio pagan la tarifa de no empadronada. [Eira: `network_open`, `network_max_active`, `network_advance_days`]
5. Las tarifas incluyen el IVA cuando proceda. ‹Comprobar con Intervención la sujeción al IVA.›

### Artículo 4. Suplemento de iluminación

1. En las instalaciones exteriores con iluminación artificial, las franjas que necesiten luz llevan
   un suplemento de ‹importe› € por franja.
2. Una franja necesita luz ‹elegir›: a) cuando empieza después de la puesta de sol o termina antes del
   amanecer, según las tablas astronómicas de ‹localidad›; o b) entre las ‹21:00› y las ‹08:00› horas.
3. La persona usuaria puede pedir la luz en otras franjas, con el mismo suplemento.
   [Eira: `lighting_supplement_cents`; `lighting_rule` (`sunset` o `fixed`), `lighting_from`, `lighting_until`]

### Artículo 5. Abonos y bonos

1. **Abono:** da derecho, durante su validez, a un descuento del ‹%› sobre la tarifa que corresponda.
   Tipos y precios en el anexo III. [Eira: *Abonos e carné* (`PassType`: `price_cents`, `valid_days`, `discount_pct`)]
2. **Bono:** ‹10› usos de una instalación o de cualquiera que lo admita, con validez de ‹365› días.
   [Eira: *Cobros → Bonos* (`VoucherType`: `uses`, `price_cents`, `valid_days`)]
3. Abonos y bonos son personales e intransferibles y se acreditan con el carné municipal (digital o
   impreso). [Eira: carné con QR dinámico; lector en la gestión]
4. Los usos de un bono no consumidos dentro de su validez no se reembolsan, salvo cierre de la
   instalación por causa imputable al ayuntamiento.

### Artículo 6. Exenciones y bonificaciones

1. **Colectivos.** Tarifas reducidas del anexo II para: a) juventud hasta ‹25› años empadronada
   [Eira: `youth`]; b) mayores de ‹65› años empadronadas [Eira: `senior`]; c) personas con discapacidad
   igual o superior al 33 %, en desempleo y familias numerosas o monoparentales, acreditándolo ante el
   ayuntamiento [Eira: `reduced` + validación del personal (`Eligibility`: colectivo y fecha de fin; **no se guarda la documentación**)].
2. **Franjas de baja demanda.** Descuento del ‹20› % en las franjas que el ayuntamiento señale.
   [Eira: `low_demand_discount_pct`; franjas marcadas con ★]
3. Los descuentos no son acumulables salvo ‹el del abono, que se aplica después de la tarifa y del
   descuento de baja demanda›. [Eira: orden fijo: tarifa del colectivo → baja demanda → abono; luz aparte]
4. **Exenciones:** a) actividades del propio ayuntamiento y escuelas deportivas municipales;
   b) ‹centros educativos públicos en horario lectivo›; c) ‹entidades deportivas inscritas, según convenio›.
   [Eira: a) reservas del ayuntamiento sin coste; b) y c) **[Eira: no hay un campo de «entidad exenta»]**: reserva en mostrador con forma de pago «Gratuíta» (`free`) o tarifa 0 en `reduced`]
5. Conforme al art. 44.2 TRLRHL, si las cuantías quedan por debajo del coste, el presupuesto
   consignará la diferencia.

*Tasa:* las exenciones y bonificaciones solo pueden ser las previstas en normas con rango de ley
(art. 9 TRLRHL); puede tenerse en cuenta la capacidad económica (art. 24.4).

### Artículo 7. Devengo y pago

1. La obligación de pago nace con el inicio de la utilización. Conforme al art. 46.1 TRLRHL, se exige
   el depósito previo del importe íntegro al hacer la reserva.
2. Formas de pago: a) **en línea** con TPV virtual al reservar [Eira: `tpv`]; b) **en la oficina**
   ‹dirección y horario›, en las ‹48› horas siguientes y siempre antes del inicio; si no se paga, la
   reserva se anula y la franja queda libre [Eira: `office`, `office_payment_hours`]; c) con **bono**
   [Eira: `voucher`]; ‹opcional› d) **aplazado** para ‹entidades›, con liquidación ‹mensual› [Eira:
   `deferred`, desactivado por defecto]. [Eira: formas admitidas en `payment_methods`; cada instalación puede restringirlas]
3. El justificante de pago es el recibo que emite el sistema. [Eira: recibo PDF]
4. Las deudas impagadas podrán exigirse por la vía de apremio (art. 46.3 TRLRHL). [Eira: no lo hace]

*Tasa:* devengo con la solicitud y pago previo (art. 26.1.b) y autoliquidación (art. 27.1).

### Artículo 8. Reservas

1. Antelación máxima de ‹14› días [Eira: `max_advance_days`]; máximo ‹4› reservas activas por persona
   [Eira: `max_active_bookings`].
2. Puede exigirse confirmar la asistencia ‹120› minutos antes; si no se confirma y hay lista de
   espera, la franja se ofrece a esta. [Eira: `confirm_release_enabled`, `confirm_release_minutes`, `waitlist_offer_minutes`]

### Artículo 9. Devoluciones y cancelaciones

1. **Por causa no imputable a la persona usuaria** (cierre, avería, meteorología que impida el uso,
   actos municipales…): devolución íntegra (art. 46.2 TRLRHL) o del uso del bono. [Eira: *Peches*: anulación con devolución íntegra y aviso]
2. **Cancelación por la persona usuaria:** a) con ‹24› horas o más: devolución íntegra [Eira:
   `cancellation_hours`]; b) con menos: devolución menos una penalización del ‹50› % [Eira:
   `late_cancel_penalty_pct`]; c) si la franja se vuelve a reservar desde la lista de espera, se
   devuelve también la penalización [Eira: automático].
3. No hay devolución una vez empezada la franja.
4. Las devoluciones se hacen por la misma vía del pago en ‹15› días.

### Artículo 10. No presentación

1. Si la persona no se presenta ni cancela, no procede devolución. Se considera no presentada si no
   registra el acceso en los ‹15› minutos siguientes al inicio. [Eira: estado `no_show`; `no_show_grace_minutes`; en nivel 0 (QR voluntario) no se marca]
2. ‹Opcional› Con lista de espera, la franja puede liberarse ‹15› minutos después del inicio sin
   registro de acceso. [Eira: `checkin_release_minutes`]
3. ‹Opcional› La reiteración de no presentaciones podrá suponer la suspensión del derecho de reserva
   en línea, previa audiencia, conforme al reglamento de uso. **[Eira: no lo hace]**: registra las no
   presentaciones, pero no bloquea reservas automáticamente. Se recomienda regularlo en el reglamento
   de uso y no en la ordenanza fiscal.

### Artículo 11. Gestión

1. La gestión y el cobro corresponden al servicio municipal de deportes, en coordinación con Tesorería.
2. El ayuntamiento podrá usar medios electrónicos para reserva, pago, acceso y avisos. El tratamiento
   de datos personales se rige por el Reglamento (UE) 2016/679 y la Ley Orgánica 3/2018.

### Disposiciones derogatoria y final

Queda derogada la ‹ordenanza anterior›. Esta ordenanza entrará en vigor ‹al día siguiente de su
publicación íntegra en el BOP›. *Tasa:* aprobación provisional, exposición pública de 30 días hábiles,
aprobación definitiva y publicación (art. 17 TRLRHL).

### Anexos

Mismos anexos I (instalaciones), II (tarifas por franja) y III (abonos y bonos) que en la versión en
gallego, con la misma correspondencia de campos de Eira (sección 2).

## 3. Variante de tasa (resumen de cambios)

1. **Título:** «Ordenanza fiscal reguladora de la tasa por la utilización de las instalaciones deportivas municipales».
2. **Fundamento:** arts. 15 a 19 y 20 a 27 TRLRHL; art. 20.4.o o 20.3.
3. **Sujetos pasivos:** art. 23 TRLRHL y art. 35.4 LGT.
4. **Cuota:** no puede exceder el coste real o previsible (art. 24.2); requiere **informe técnico-económico** (art. 25).
5. **Exenciones y bonificaciones:** solo las previstas en ley (art. 9); capacidad económica (art. 24.4).
6. **Devengo y pago:** con la solicitud y pago previo (art. 26.1.b), autoliquidación (art. 27.1) y
   devolución si el servicio no se presta por causas no imputables (art. 26.3).
7. **Infracciones y sanciones:** remisión a la LGT (arts. 178 y siguientes).
8. **Tramitación:** art. 17 TRLRHL.

En la configuración de Eira **no cambia nada**.
