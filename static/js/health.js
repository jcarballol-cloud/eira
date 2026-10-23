// SPDX-License-Identifier: EUPL-1.2
// Páxina «A miña saúde»: o formulario non ten `name` nin `action`; os datos gárdanse en localStorage.
// Só se envían ao servidor se a persoa usa o formulario aparte «Gardar tamén na miña conta» e marca
// o consentimento explícito (art. 9 RXPD).
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }

  document.addEventListener("DOMContentLoaded", function () {
    var form = $("health-form");
    if (!form || !window.EiraHealth) return;
    var H = window.EiraHealth, T = H.strings(), out = $("h-advice");
    function show(d) {
      var session = parseFloat(d.session) > 0 ? { start: null, duration: d.session, indoor: true } : null;
      var items = H.recommend(d, session, T);
      if (items.length) H.render(out, items, T, out.dataset.sprite);
    }
    var d = H.profile();
    ["age", "weight", "minutes", "session"].forEach(function (k) { if (d[k] !== undefined && d[k] !== null) $("h-" + k).value = d[k]; });
    show(d);
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var data = { age: $("h-age").value, weight: $("h-weight").value, minutes: $("h-minutes").value, session: $("h-session").value };
      H.saveLocal(data);
      show(data);
      if (window.eiraAnnounce) window.eiraAnnounce(T.saved);
    });
    $("h-clear").addEventListener("click", function () {
      H.clearLocal();
      form.reset();
      out.textContent = "";
      if (window.eiraAnnounce) window.eiraAnnounce(T.cleared);
    });
    // Gardar na conta: copia os valores do formulario local só no momento de enviar
    var acc = $("health-account-form");
    if (acc) {
      acc.addEventListener("submit", function () {
        acc.querySelectorAll("[data-copy]").forEach(function (inp) { inp.value = $(inp.dataset.copy).value; });
      });
    }
  });
})();
