# SPDX-License-Identifier: EUPL-1.2
"""Asistente IA opcional. Só recibe datos AGREGADOS (nunca persoais).

- FakeAIAdapter: resumo semanal xerado con regras (sen modelo).
- OpenAICompatibleAdapter: calquera servidor compatible coa API de OpenAI autoaloxado
  (llama.cpp server, Ollama, vLLM) con modelos de pesos abertos.
A plataforma funciona igual co adaptador desactivado (EIRA_AI_ENABLED=0).
"""

import json
import re
import urllib.request

from django.conf import settings
from django.utils.translation import gettext as _


class AIAdapter:
    def weekly_summary(self, aggregates):
        raise NotImplementedError


def _check_aggregates(aggregates):
    forbidden = {"email", "name", "user", "phone", "user_id", "holder_name"}
    text = json.dumps(aggregates).lower()
    if any(f'"{k}"' in text for k in forbidden):
        raise ValueError("O asistente só acepta datos agregados")


class FakeAIAdapter(AIAdapter):
    def weekly_summary(self, aggregates):
        _check_aggregates(aggregates)
        lines = [_("Resumo semanal (xerado sen IA, a partir de datos agregados):")]
        lines.append(
            _("%(b)s reservas, ocupación media do %(o)s %% e %(n)s non presentadas.")
            % {
                "b": aggregates.get("bookings", 0),
                "o": aggregates.get("occupancy_pct", 0),
                "n": aggregates.get("no_shows", 0),
            }
        )
        if aggregates.get("top_facility"):
            lines.append(
                _("A instalación máis usada foi %(f)s.") % {"f": aggregates["top_facility"]}
            )
        if aggregates.get("underused"):
            lines.append(
                _("Infrautilizadas: %(f)s. Valora ofrecelas a escolas ou clubs.")
                % {"f": ", ".join(aggregates["underused"])}
            )
        if aggregates.get("open_incidents"):
            lines.append(
                _("Quedan %(n)s incidencias abertas.") % {"n": aggregates["open_incidents"]}
            )
        return "\n".join(lines)


class OpenAICompatibleAdapter(AIAdapter):
    def weekly_summary(self, aggregates):
        _check_aggregates(aggregates)
        payload = {
            "model": settings.EIRA_AI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "Es un asistente dun servizo municipal de deportes. Responde en galego, "
                    "breve, con 3-5 frases e recomendacións prácticas. Só tes datos agregados.",
                },
                {"role": "user", "content": json.dumps(aggregates, ensure_ascii=False)},
            ],
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            settings.EIRA_AI_BASE_URL.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=settings.EIRA_AI_TIMEOUT) as resp:  # noqa: S310
            data = json.load(resp)
        text = data["choices"][0]["message"]["content"]
        # Algúns modelos de razoamento (p. ex. Qwen3) devolven o seu «pensamento» entre etiquetas
        return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
