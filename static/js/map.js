// SPDX-License-Identifier: EUPL-1.2
// Mapa de instalacións con Leaflet + teselas configurables (OpenStreetMap por defecto).
// A lista accesible é sempre a alternativa principal; o mapa é un complemento.
(function () {
  "use strict";
  function init() {
    var el = document.querySelector("[data-map]");
    if (!el || !window.L) return;
    var data = JSON.parse(document.getElementById(el.getAttribute("data-map")).textContent);
    if (!data.features.length) { el.hidden = true; return; }
    var map = L.map(el, { scrollWheelZoom: false, keyboard: true });
    // A política global é «same-origin» (non se filtra a URL a terceiros), pero os servidores de teselas
    // de OSM esixen o Referer: envíase só a orixe e só nas teselas.
    var attribution = document.createElement("span");
    var link = document.createElement("a");
    link.href = data.attribution_url; link.textContent = data.attribution; link.rel = "noopener";
    attribution.appendChild(document.createTextNode("© ")); attribution.appendChild(link);
    L.tileLayer(data.tiles, {
      maxZoom: 18,
      referrerPolicy: "strict-origin-when-cross-origin",
      attribution: attribution.outerHTML
    }).addTo(map);
    var icon = L.icon({ iconUrl: data.icon, iconRetinaUrl: data.icon2x, shadowUrl: data.shadow, iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41] });
    var layer = L.geoJSON(data, {
      pointToLayer: function (f, latlng) { return L.marker(latlng, { icon: icon, title: f.properties.name, alt: f.properties.name }); },
      onEachFeature: function (f, m) {
        var a = document.createElement("a");
        a.href = f.properties.url; a.textContent = f.properties.name;
        var p = document.createElement("div");
        var strong = document.createElement("strong"); strong.appendChild(a);
        p.appendChild(strong);
        var small = document.createElement("div"); small.textContent = f.properties.kind + (f.properties.parish ? " · " + f.properties.parish : "");
        p.appendChild(small);
        m.bindPopup(p);
      }
    }).addTo(map);
    map.fitBounds(layer.getBounds().pad(0.2));
  }
  document.addEventListener("DOMContentLoaded", init);
})();
