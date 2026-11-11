<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Vídeos da demostración

Os vídeos do guión pesan máis de 10 MB, así que non se gardan no repositorio: están dispoñibles baixo petición ao equipo.

| Ficheiro | Contido |
|---|---|
| `docs/demo/eira-pitch.mp4` (H.264) e `docs/demo/eira-pitch.webm` (VP9) | **Vídeo final do pitch (v5)**, 1920×1080, ≈ 2 min 14 s, co paso novo da reserva en Pontedouro (tarifa de non empadroada e luz). Subtítulos en galego **só queimados na imaxe** (o MP4 xa non leva pista activable); o texto tamén en `eira-pitch.vtt` |
| `docs/demo/eira-anexo-saude.mp4` e `.webm` | **Anexo v5 «Eira para o concello e a saúde»** (máximo 75 s, con «Escoitar» e o mapa de procedencia desde a v1.5): consellos de saúde co tempo, valoracións, observatorio e índice de vida activa, cartel da porta, revisión de seguridade e rexistro de brechas. Subtítulos queimados e `eira-anexo-saude.vtt` |
| `eira-demo-movil.webm` | Percorrido do guión co marco de teléfono e de tableta (≈ 88 s, con subtítulos) |
| `eira-demo-escritorio.webm` | O mesmo percorrido en escritorio |

**Xeralos:** `python tools/tasks.py pitch` (vídeo final), `python tools/tasks.py annex` (anexo; rexenera a demo xusto antes e grava sen IA, `EIRA_AI_ENABLED=0`) e `python tools/tasks.py video` (os dous percorridos longos, en `release-assets/`). Todos os ficheiros de vídeo e o `.vtt` están ignorados polo git.

**Publicalos** nunha release en borrador, que só ve quen ten acceso ao repositorio privado:

```sh
gh release create v1.0-certame-demo --draft --title "Eira v1.0 · vídeos da demo" \
  --notes "Vídeos do guión da demostración (datos ficticios)." \
  docs/demo/eira-pitch.mp4 docs/demo/eira-pitch.webm docs/demo/eira-pitch.vtt \
  docs/demo/eira-anexo-saude.mp4 docs/demo/eira-anexo-saude.webm docs/demo/eira-anexo-saude.vtt \
  release-assets/eira-demo-movil.webm release-assets/eira-demo-escritorio.webm
```
