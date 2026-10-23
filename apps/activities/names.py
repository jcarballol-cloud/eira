# SPDX-License-Identifier: EUPL-1.2
"""Nomes para a tableta da monitora: inicial do primeiro apelido, orde e busca.

- Ignóranse as partículas do apelido (de, del, da, do, dos, das, la, las, los, van, von, mc, mac, y, e).
- Os acentos normalízanse (Á → A) pero a Ñ é unha letra propia.
- Sen apelidos rexistrados, úsase a inicial do nome (os menores poden non telos).
"""

import unicodedata

ALPHABET = list("ABCDEFGHIJKLMNÑOPQRSTUVWXYZ")
PARTICLES = {
    "DE",
    "DEL",
    "LA",
    "LAS",
    "LOS",
    "DA",
    "DO",
    "DOS",
    "DAS",
    "VAN",
    "VON",
    "MC",
    "MAC",
    "Y",
    "E",
    "D'",
}


def fold(text):
    """Maiúsculas sen acentos, conservando a Ñ."""
    out = []
    for ch in (text or "").upper():
        if ch == "Ñ":
            out.append("Ñ")
            continue
        base = unicodedata.normalize("NFD", ch)[0]
        out.append(base)
    return "".join(out)


def first_surname(surnames):
    words = [w for w in fold(surnames).replace("-", " ").split() if w]
    for w in words:
        if w not in PARTICLES:
            return w
    return words[0] if words else ""


def first_surname_label(surnames):
    """Primeiro apelido tal como se escribe, coas partículas que o preceden («do Campo»,
    «de la Fuente»). É o único apelido que se amosa na tableta."""
    words = (surnames or "").replace("-", " ").split()
    out = []
    for w in words:
        out.append(w)
        if fold(w) not in PARTICLES:
            break
    return " ".join(out)


def initial(surnames, name=""):
    word = first_surname(surnames) or fold(name).strip()
    for ch in word:
        if ch in ALPHABET:
            return ch
    return "#"


def sort_key(surnames, name=""):
    return (first_surname(surnames) or fold(name), fold(surnames), fold(name))


def display(surnames, name):
    """«Apelidos, Nome» (ou só o nome)."""
    return f"{surnames.strip()}, {name.strip()}" if surnames and surnames.strip() else name.strip()
