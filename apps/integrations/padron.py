# SPDX-License-Identifier: EUPL-1.2
"""Consulta do padrón municipal detrás dun adaptador.

Eira nunca garda o padrón: só pregunta «esta persoa figura empadroada?» e anota o resultado.
O contraste faise só con DNI/NIE e data de nacemento; o nome **nunca** se usa para casar.

- `CsvPadronAdapter` (por defecto, v4): compara co HMAC das entradas do CSV que sobe o concello
  (apps/accounts/padron.py). O CSV non se garda.
- `SvdrPadronAdapter` (esqueleto): Servizo de Verificación de Datos de Residencia da
  Plataforma de Intermediación de Datos, ou o servizo web do padrón do propio concello, coa
  finalidade rexistrada. Mesma interface, para cando o concello teña API.
"""

from dataclasses import dataclass


@dataclass
class PadronResult:
    found: bool
    reason: str = ""  # "", "no_padron" (aínda sen cargar), "no_match", "invalid"


class PadronAdapter:
    def check(self, municipality, *, id_number, birth_date):
        raise NotImplementedError


class CsvPadronAdapter(PadronAdapter):
    def check(self, municipality, *, id_number, birth_date):
        from apps.accounts import padron

        if padron.digest(municipality, id_number, birth_date) is None:
            return PadronResult(False, "invalid")
        if padron.current(municipality) is None:
            return PadronResult(False, "no_padron")
        if padron.matches(municipality, id_number, birth_date):
            return PadronResult(True)
        return PadronResult(False, "no_match")


# Compatibilidade coa configuración anterior (EIRA_PADRON_ADAPTER=…FakePadronAdapter)
FakePadronAdapter = CsvPadronAdapter


class SvdrPadronAdapter(PadronAdapter):
    def check(self, municipality, *, id_number, birth_date):
        raise NotImplementedError
