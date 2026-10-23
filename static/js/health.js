// SPDX-License-Identifier: EUPL-1.2
// Saúde persoal no dispositivo: os datos gárdanse só en localStorage e nunca saen do navegador.
// Os campos non teñen atributo `name` e o formulario non ten `action`: non hai nada que enviar.
(function () {
  "use strict";
  var KEY = "eira-health-v1";
  function $(id) { return document.getElementById(id); }
  function load() { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; } }
  function save(d) { try { localStorage.setItem(KEY, JSON.stringify(d)); } catch (e) { /* modo privado */ } }
  function fmt(s, v) { return s.replace("%s", v); }

  function render(d) {
    var S = $("h-strings").dataset, out = $("h-advice");
    var items = [];
    var age = parseFloat(d.age), weight = parseFloat(d.weight), minutes = parseFloat(d.minutes), session = parseFloat(d.session);
    if (weight > 0) {
      var low = Math.round(weight * 5 / 50) * 50, high = Math.round(weight * 7 / 50) * 50;
      items.push(fmt(S.waterBefore, low + "–" + high));
    }
    if (session > 60) items.push(S.waterDuring); else if (session > 0) items.push(S.waterShort);
    if (age >= 18 && minutes >= 0) items.push(minutes >= 150 ? S.whoAdultOk : fmt(S.whoAdult, Math.round(minutes)));
    if (age > 0 && age < 18) items.push(S.whoChild);
    if (age >= 65) items.push(S.senior);
    out.textContent = "";
    if (!items.length) return;
    var ul = document.createElement("ul");
    ul.className = "stack-sm";
    items.forEach(function (t) { var li = document.createElement("li"); li.textContent = t; ul.appendChild(li); });
    out.appendChild(ul);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = $("health-form");
    if (!form) return;
    var d = load();
    ["age", "weight", "minutes", "session"].forEach(function (k) { if (d[k] !== undefined) $("h-" + k).value = d[k]; });
    render(d);
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var data = { age: $("h-age").value, weight: $("h-weight").value, minutes: $("h-minutes").value, session: $("h-session").value };
      save(data);
      render(data);
      if (window.eiraAnnounce) window.eiraAnnounce($("h-strings").dataset.saved);
    });
    $("h-clear").addEventListener("click", function () {
      try { localStorage.removeItem(KEY); } catch (e) { /* nada */ }
      form.reset();
      render({});
      if (window.eiraAnnounce) window.eiraAnnounce($("h-strings").dataset.cleared);
    });
  });
})();
