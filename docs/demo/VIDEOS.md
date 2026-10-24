<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Vídeos da demostración

Os vídeos do guión pesan máis de 10 MB, así que non se gardan no repositorio: van como adxuntos dunha release.

| Ficheiro | Contido |
|---|---|
| `docs/demo/eira-pitch.mp4` (H.264) e `docs/demo/eira-pitch.webm` (VP9) | **Vídeo final do pitch**, 1920×1080, ≈ 2 min 5 s, subtítulos en galego queimados na imaxe e tamén como pista no MP4 e en `eira-pitch.vtt` |
| `eira-demo-movil.webm` | Percorrido do guión co marco de teléfono e de tableta (≈ 88 s, con subtítulos) |
| `eira-demo-escritorio.webm` | O mesmo percorrido en escritorio |

**Xeralos:** `python tools/tasks.py pitch` (vídeo final; rexenera a demo xusto antes e grava sen IA, `EIRA_AI_ENABLED=0`) e `python tools/tasks.py video` (os dous percorridos longos, en `release-assets/`). Todos os ficheiros de vídeo e o `.vtt` están ignorados polo git.

**Publicalos** nunha release en borrador, que só ve quen ten acceso ao repositorio privado:

```sh
gh release create v0.4.1-demo --draft --title "Eira v0.4.1 · vídeos da demo"   --notes "Vídeos do guión da demostración (datos ficticios)."   docs/demo/eira-pitch.mp4 docs/demo/eira-pitch.webm docs/demo/eira-pitch.vtt \n  release-assets/eira-demo-movil.webm release-assets/eira-demo-escritorio.webm
```
