# SPDX-License-Identifier: EUPL-1.2
"""v1.2 · H: vínculo co carné que xa teña o concello (biblioteca, piscina…), detrás dun adaptador.

Só o adaptador e a documentación (docs/carne-municipal.md): **non hai integración real**. A
implementación simulada le un CSV ficticio. Unha implementación real consultaría o sistema do
concello (p. ex. unha API do xestor da biblioteca) só co número do carné, sen copiar datos."""

import csv
from pathlib import Path

DEMO_CSV = Path(__file__).resolve().parent / "data" / "carnes_demo.csv"


class MunicipalCardAdapter:
    def lookup(self, municipality, external_id):
        """{"external_id", "service", "valid"} ou None. Nunca devolve datos persoais."""
        raise NotImplementedError

    def link(self, card, external_id):
        """Vincula o carné de Eira co externo se este existe e é válido. Devolve True/False."""
        found = self.lookup(card.municipality, external_id)
        if not found or not found["valid"]:
            return False
        card.external_id = found["external_id"]
        card.save(update_fields=["external_id"])
        return True


class FakeMunicipalCardAdapter(MunicipalCardAdapter):
    """Simulado: carnés ficticios (municipality_slug, external_id, service, valid)."""

    def lookup(self, municipality, external_id):
        with DEMO_CSV.open(encoding="utf-8") as fh:
            rows = csv.DictReader(line for line in fh if not line.startswith("#"))
            for row in rows:
                if row["municipality"] == municipality.slug and row["external_id"] == external_id:
                    return {
                        "external_id": row["external_id"],
                        "service": row["service"],
                        "valid": row["valid"] == "1",
                    }
        return None
