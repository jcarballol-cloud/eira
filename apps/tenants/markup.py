# SPDX-License-Identifier: EUPL-1.2
"""v1.5: Markdown mínimo e seguro para o LEEME e os documentos legais.

Escapa todo o HTML antes de aplicar o formato, polo que un texto editado por un concello non pode
inxectar marcado. Só entende títulos, listas, táboas, citas, código, grosa, cursiva e ligazóns
http(s) ou mailto; unha ligazón relativa (a un ficheiro do repositorio) queda como texto.
Sen dependencias novas nin estilos en liña, para cumprir a CSP."""

import re

from django.utils.html import escape
from django.utils.safestring import mark_safe

_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_AUTOLINK = re.compile(r"&lt;(https?://[^\s&]+)&gt;")
_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])")


def _link(match):
    label, url = match.group(1), match.group(2)
    if url.startswith(("http://", "https://", "mailto:")):
        return f'<a href="{url}" rel="noopener">{label}</a>'
    return label


def _inline(text):
    html = str(escape(text))
    # O código protéxese para que o seu contido non se interprete como formato
    chunks = []

    def stash(match):
        chunks.append(f"<code>{match.group(1)}</code>")
        return f"\x00{len(chunks) - 1}\x00"

    html = _CODE.sub(stash, html)
    html = _LINK.sub(_link, html)
    html = _AUTOLINK.sub(r'<a href="\1" rel="noopener">\1</a>', html)
    html = _BOLD.sub(r"<strong>\1</strong>", html)
    html = _ITALIC.sub(r"<em>\1</em>", html)
    return re.sub(r"\x00(\d+)\x00", lambda m: chunks[int(m.group(1))], html)


def _table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], cells[2:]
    out = ['<div class="table-wrap" tabindex="0"><table class="data"><thead><tr>']
    out += [f'<th scope="col">{_inline(c)}</th>' for c in head]
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def _is_table_separator(line):
    return bool(re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", line)) and "-" in line


def render(text, base_level=0):
    """Devolve HTML seguro. `base_level` baixa os títulos (1 → un `#` pasa a ser <h2>)."""
    html = []
    lines = (text or "").replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
            i += 1
        elif stripped.startswith("```"):
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            html.append(
                f'<pre class="legal-pre" tabindex="0"><code>{escape(chr(10).join(block))}</code></pre>'
            )
        elif m := re.match(r"(#{1,6})\s+(.*)", stripped):
            level = min(len(m.group(1)) + base_level, 6)
            html.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
        elif stripped.startswith("|") and i + 1 < len(lines) and _is_table_separator(lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            html.append(_table(rows))
        elif stripped.startswith(">"):
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i].strip().lstrip(">").strip())
                i += 1
            html.append(f'<blockquote class="note">{_inline(" ".join(block))}</blockquote>')
        elif re.match(r"(\d+\.|[-*])\s+", stripped):
            ordered = bool(re.match(r"\d+\.", stripped))
            items = []
            while i < len(lines):
                current = lines[i].strip()
                m = re.match(r"(\d+\.|[-*])\s+(.*)", current)
                if m:
                    items.append(m.group(2))
                elif current and lines[i].startswith((" ", "\t")) and items:
                    items[-1] += " " + current  # continuación da mesma entrada
                else:
                    break
                i += 1
            tag = "ol" if ordered else "ul"
            html.append(f"<{tag}>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + f"</{tag}>")
        else:
            block = []
            while i < len(lines):
                current = lines[i].strip()
                if (
                    not current
                    or current.startswith(("#", ">", "|", "```"))
                    or re.match(r"(\d+\.|[-*])\s+", current)
                ):
                    break
                block.append(current)
                i += 1
            html.append(f"<p>{_inline(' '.join(block))}</p>")
    return mark_safe("\n".join(html))  # noqa: S308 — todo o texto pasou por escape()
