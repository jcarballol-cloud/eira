<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Guía de linguaxe inclusiva (galego e castelán)

Eira fálalle a toda a veciñanza. Os textos da interface non deben dar por suposto o xénero de quen os le nin de quen se nomea. Esta guía resume as regras que se aplicaron na revisión da v5 e as que hai que seguir nas cadeas novas.

## Principios
1. **Termos colectivos ou neutros** antes ca masculino xenérico.
2. **Reformular** a frase antes ca usar barras («o/a») ou arrobas: as barras dificultan a lectura e os lectores de pantalla len «barra».
3. **Linguaxe sinxela:** frases curtas, verbos en activa, segunda persoa («podes reservar»), sen tecnicismos.
4. Cando se fala dunha **persoa concreta** cun nome, non se deduce o xénero do nome: úsase o seu rol («a persoa monitora», «persoal de mantemento») ou unha forma sen xénero.
5. Non se cambian **nomes propios, termos legais** (p. ex. «persoa interesada» no RXPD) nin textos de normas que cita o concello.

## Equivalencias usadas

| Evitar | Galego | Castelán |
|---|---|---|
| os veciños, o veciño | a veciñanza, a persoa | el vecindario, la persona |
| o usuario, os usuarios | a persoa usuaria, as persoas usuarias | la persona usuaria, las personas usuarias |
| o monitor, monitor/a | a persoa monitora | la persona monitora |
| o operario | o persoal de mantemento | el personal de mantenimiento |
| empadroado/a | ter o empadroamento (aquí) | estar empadronado → «tener el empadronamiento (aquí)» |
| inscrito/a | ter inscrición, inscrición feita | tener inscripción, inscripción hecha |
| Benvida/o | Dámosche a benvida | Te damos la bienvenida |
| todos os interesados | quen estea interesado → «quen teña interese» | quien tenga interés |
| reservar en nome dun veciño | reservar en nome doutra persoa | reservar en nombre de otra persona |

## Cadeas revisadas na v5
- Rexistro de entrada: «Benvida/o!» → «Dámosche a benvida!».
- Ficha de alta no mostrador: «Benvida/o, ‹nome›» → «Dámosche a benvida, ‹nome›».
- Escolas: «Monitor/a» → «Persoa monitora»; «o monitor verá unha cámara riscada» → «a persoa monitora verá…»; «%(n)s inscrito/a» → «Inscrición feita: %(n)s».
- App: «Estás empadroado/a aquí?» → «Tes o empadroamento aquí?»; «Non estou empadroado/a» → «Non teño o empadroamento aquí»; solicitude da app e alta.
- Panel do día: «Reservar en nome dun veciño» → «Reservar en nome doutra persoa».
- Rol do concello: «Monitor/a» → «Persoa monitora».
- Perfís da demo: «Veciña» → «Persoa usuaria», «Veciño maior» → «Persoa maior», «Veciño novo» → «Alta nova», «Operario de mantemento» → «Persoal de mantemento», «Monitora deportiva» → «Persoa monitora». (Son personaxes ficticias; o rol descríbeas sen deducir o xénero do nome.)
- O castelán revisouse en paralelo con `locale/es/LC_MESSAGES/django.po`.

## Como comprobalo
- `tests/unit/test_inclusive_language.py` busca as formas que hai que evitar («/a», «/o», «veciño», «o monitor», «usuario»…) nas cadeas de interface (`msgid` en galego e `msgstr` en castelán) e falla se aparece algunha nova. As excepcións (nomes propios, citas legais) van nunha lista no propio test, co motivo.
