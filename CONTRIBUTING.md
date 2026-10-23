# Como contribuír a Eira

Grazas por axudar! Eira é software libre baixo a licenza **EUPL-1.2**.

1. Abre unha incidencia antes dun cambio grande para comentalo.
2. Crea unha rama, fai commits pequenos e describe o *porqué*.
3. Antes de enviar: `make lint`, `make test` e, se tocas interface, `make e2e` (cero violacións axe).
4. Todo ficheiro de código novo leva a cabeceira `SPDX-License-Identifier: EUPL-1.2`.
5. Novas dependencias: só con licenza compatible coa EUPL-1.2 (`make licenses`).
6. Textos da interface: escríbeos en galego dentro de `{% translate %}` / `gettext` e engade a tradución ao castelán en `locale/es/LC_MESSAGES/django.po`.
7. Integracións externas: sempre detrás dun adaptador en `apps/integrations/` cunha implementación simulada.

Ao contribuír aceptas que a túa achega se publique baixo EUPL-1.2 e que respectas o [código de conduta](CODE_OF_CONDUCT.md).
