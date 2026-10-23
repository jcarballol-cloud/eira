# SPDX-License-Identifier: EUPL-1.2
"""Consulta do padrón municipal detrás dun adaptador.

Eira nunca garda o padrón: só pregunta «esta persoa figura empadroada?» e anota o resultado.

- `FakePadronAdapter` (demo): figura quen indica un código postal do termo municipal
  (campo «códigos postais» do concello) e un ano de nacemento plausible. Sen datos reais.
- `SvdrPadronAdapter` (esqueleto): Servizo de Verificación de Datos de Residencia da
  Plataforma de Intermediación de Datos (ou o servizo web do padrón do propio concello),
  con consentimento da persoa e finalidade rexistrada.
"""

from dataclasses import dataclass

from django.utils import timezone


@dataclass
class PadronResult:
    found: bool
    reason: str = ""


class PadronAdapter:
    def check(self, municipality, *, name, birth_year, postcode):
        raise NotImplementedError


class FakePadronAdapter(PadronAdapter):
    def check(self, municipality, *, name, birth_year, postcode):
        postcodes = {p.strip() for p in (municipality.postcodes or "").split(",") if p.strip()}
        year = timezone.localdate().year
        if not birth_year or not (year - 110 <= birth_year <= year):
            return PadronResult(False, "birth_year")
        if postcode.strip() not in postcodes:
            return PadronResult(False, "postcode")
        return PadronResult(True)


class SvdrPadronAdapter(PadronAdapter):
    def check(self, municipality, *, name, birth_year, postcode):
        raise NotImplementedError
