<!-- SPDX-License-Identifier: EUPL-1.2 -->
# Vídeos da demostración

Os vídeos do guión pesan máis de 10 MB, así que non se gardan no repositorio: van como adxuntos dunha release.

| Ficheiro | Contido |
|---|---|
| `eira-demo-movil.webm` | Percorrido do guión co marco de teléfono e de tableta (≈ 88 s, con subtítulos) |
| `eira-demo-escritorio.webm` | O mesmo percorrido en escritorio |

**Xeralos:** `python tools/tasks.py video`. Gárdanse en `release-assets/`, que o git ignora.

**Publicalos** nunha release en borrador, que só ve quen ten acceso ao repositorio privado:

```sh
gh release create v0.4.1-demo --draft --title "Eira v0.4.1 · vídeos da demo"   --notes "Vídeos do guión da demostración (datos ficticios)."   release-assets/eira-demo-movil.webm release-assets/eira-demo-escritorio.webm
```
