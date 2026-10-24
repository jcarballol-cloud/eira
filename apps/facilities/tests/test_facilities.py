# SPDX-License-Identifier: EUPL-1.2
"""Busca e listado público de instalacións."""


def test_compact_search_counts_active_filters_and_offers_removal(client, padel_a, gym_a):
    """v4: busca nunha liña; o botón «Filtros» leva o número de filtros activos (a busca non conta)
    e cada filtro activo ten unha ligazón para quitalo."""
    r = client.get("/c/concello-a/", {"q": "pista", "lighting": "on", "kind": "padel"})
    active = r.context["active"]
    assert [a["name"] for a in active] == ["kind", "lighting"]
    lighting = next(a for a in active if a["name"] == "lighting")
    assert "lighting" not in lighting["remove"] and "q=pista" in lighting["remove"]
    html = r.content.decode()
    assert 'class="count-badge"' in html and 'role="search"' in html
    assert client.get("/c/concello-a/").context["active"] == []
