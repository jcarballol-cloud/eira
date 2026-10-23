// SPDX-License-Identifier: EUPL-1.2
// Motor de recomendacións de saúde. Execútase no navegador: o peso e a idade non saen do dispositivo
// (salvo que a persoa decida gardalos na conta). Regras e fontes en docs/health/recomendacions.md.
(function () {
  "use strict";

  function round50(v) { return Math.round(v / 50) * 50; }
  function fmtNum(v, lang) {
    try { return new Intl.NumberFormat(lang || document.documentElement.lang || "gl").format(v); } catch (e) { return String(v); }
  }
  function fill(s, a, b) { return String(s || "").replace("%1", a).replace("%2", b); }
  function hhmm(d) { return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2); }

  // p = {age, weight, minutes}; s = {start: Date|null, duration, indoor, temp, uv, rain, wind} ou null
  function recommend(p, s, T) {
    var items = [];
    var age = parseFloat(p.age), weight = parseFloat(p.weight), weekly = parseFloat(p.minutes);
    var dur = s ? parseFloat(s.duration) || 0 : 0;
    var adult = age >= 18 || (!(age > 0) && weight > 0);
    var minor = age > 0 && age < 18;
    var hot = s && !s.indoor && parseFloat(s.temp) >= 27;
    var warm = s && parseFloat(s.temp) >= 20;

    // 1. Auga antes (ACSM 2007: 5–7 ml/kg polo menos 4 h antes) — só persoas adultas
    if (adult && weight > 0) {
      var lo = round50(weight * 5), hi = round50(weight * 7);
      var when = s && s.start ? fill(T.beforeAt, hhmm(new Date(s.start.getTime() - 4 * 3600e3)), "") : T.beforeAny;
      items.push({ icon: "droplet", title: T.beforeTitle, text: when, amount: fill(T.ml, fmtNum(lo) + "–" + fmtNum(hi)), source: "ACSM 2007" });
    }

    // 2. Durante (ACSM 2007: 0,4–0,8 l/h como punto de partida en sesións longas ou con calor)
    if (s && dur > 0) {
      if (adult && (dur > 60 || hot)) {
        var h = dur / 60;
        var dlo = round50(400 * h), dhi = round50(800 * h);
        items.push({ icon: "clock", title: T.duringTitle, text: T.duringLong, amount: fill(T.mlTotal, fmtNum(dlo) + "–" + fmtNum(dhi)), source: "ACSM 2007" });
      } else {
        items.push({ icon: "clock", title: T.duringTitle, text: minor ? T.duringMinor : T.duringShort, amount: "", source: "ACSM 2007" });
      }
      // 3. Sales: sesións de 2 h ou máis, ou longas con calor
      if (dur >= 120 || (hot && dur > 60)) {
        items.push({ icon: "droplet", title: T.saltTitle, text: T.saltText, amount: "", source: "ACSM 2007" });
      }
      // 4. Hiponatremia: aviso en sesións longas para quen recibe cifras
      if (adult && dur >= 90) {
        items.push({ icon: "alert", title: T.hypoTitle, text: T.hypoText, amount: "", source: "ACSM 2007", warn: true });
      }
      // 5. Hidratos en sesións de máis de 75 min (ACSM/AND/DC 2016: 30–60 g/h)
      if (adult && dur > 75) {
        var hh = dur / 60;
        items.push({ icon: "utensils", title: T.carbsTitle, text: T.carbsText, amount: fill(T.grams, fmtNum(Math.round(30 * hh)) + "–" + fmtNum(Math.round(60 * hh))), source: "Thomas, Erdman e Burke 2016" });
      }
    }

    // 6. Despois (ACSM 2007: ~1,5 l por kg perdido)
    if (adult && s && dur >= 45) {
      items.push({ icon: "thermo", title: T.afterTitle, text: T.afterText, amount: T.afterAmount, source: "ACSM 2007" });
    }

    // 7. Tempo (limiares de apps/integrations/weather.py)
    if (s && s.temp !== undefined && s.temp !== null && s.temp !== "") {
      var t = parseFloat(s.temp);
      if (hot) items.push({ icon: "sun-hot", title: T.heatTitle, text: T.heatText, amount: fill(T.degrees, fmtNum(Math.round(t))), source: "OMS (calor e saúde)" });
      else if (warm && !s.indoor) items.push({ icon: "sun", title: T.warmTitle, text: T.warmText, amount: fill(T.degrees, fmtNum(Math.round(t))), source: "ACSM 2007" });
      if (t <= 8) items.push({ icon: "thermo", title: T.coldTitle, text: T.coldText, amount: fill(T.degrees, fmtNum(Math.round(t))), source: "ACSM" });
      if (!s.indoor && parseFloat(s.uv) >= 3) items.push({ icon: "sun", title: T.uvTitle, text: parseFloat(s.uv) >= 6 ? T.uvHigh : T.uvMid, amount: fill(T.uv, s.uv), source: "OMS (índice UV)" });
      if (!s.indoor && parseFloat(s.rain) >= 60) items.push({ icon: "rain", title: T.rainTitle, text: T.rainText, amount: fmtNum(s.rain) + " %", source: T.forecastSource });
    }

    // 8. Idade
    if (age >= 65) items.push({ icon: "heart", title: T.seniorTitle, text: T.seniorText, amount: "", source: "OMS 2020 · EFSA 2010" });
    if (minor) items.push({ icon: "users", title: T.minorTitle, text: T.minorText, amount: fill(T.perDay, "60"), source: "OMS 2020" });

    // 9. Actividade semanal (OMS 2020: 150–300 min/semana)
    if (adult && weekly >= 0 && !isNaN(weekly)) {
      var total = weekly + dur;
      items.push({ icon: "chart", title: T.whoTitle, text: total >= 150 ? T.whoOk : fill(T.whoMore, fmtNum(150 - total)), amount: fill(T.whoAmount, fmtNum(total)), source: "OMS 2020" });
    }
    return items;
  }

  function render(container, items, T, sprite) {
    container.textContent = "";
    if (!items.length) return;
    var ul = document.createElement("ul");
    ul.className = "rec-list";
    ul.setAttribute("role", "list");
    items.forEach(function (it) {
      var li = document.createElement("li");
      li.className = "rec" + (it.warn ? " rec--warn" : "");
      var ns = "http://www.w3.org/2000/svg";
      var svg = document.createElementNS(ns, "svg");
      svg.setAttribute("class", "icon rec__icon");
      svg.setAttribute("aria-hidden", "true");
      var use = document.createElementNS(ns, "use");
      use.setAttribute("href", sprite + "#" + it.icon);
      svg.appendChild(use);
      var body = document.createElement("div");
      body.className = "rec__body";
      var title = document.createElement("strong");
      title.textContent = it.title;
      var text = document.createElement("p");
      text.textContent = it.text;
      var src = document.createElement("small");
      src.textContent = fill(T.source, it.source);
      body.appendChild(title); body.appendChild(text); body.appendChild(src);
      li.appendChild(svg); li.appendChild(body);
      if (it.amount) {
        var amount = document.createElement("span");
        amount.className = "rec__amount";
        amount.textContent = it.amount;
        li.appendChild(amount);
      }
      ul.appendChild(li);
    });
    container.appendChild(ul);
  }

  var KEY = "eira-health-v1";
  function loadLocal() { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; } }
  function saveLocal(d) { try { localStorage.setItem(KEY, JSON.stringify(d)); } catch (e) { /* modo privado */ } }
  function clearLocal() { try { localStorage.removeItem(KEY); } catch (e) { /* nada */ } }
  function strings() { var el = document.getElementById("h-strings"); return el ? el.dataset : {}; }
  function accountProfile() {
    var el = document.getElementById("h-account");
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }
  // Perfil efectivo: o da conta (se a persoa o gardou) ou o do dispositivo
  function profile() {
    var acc = accountProfile();
    if (acc) return { age: acc.age, weight: acc.weight, minutes: acc.minutes, fromAccount: true };
    return loadLocal();
  }

  window.EiraHealth = { recommend: recommend, render: render, profile: profile, saveLocal: saveLocal, clearLocal: clearLocal, loadLocal: loadLocal, strings: strings };

  // Recomendacións dentro dunha reserva
  document.addEventListener("DOMContentLoaded", function () {
    var box = document.querySelector("[data-health-booking]");
    if (!box) return;
    var d = box.dataset, T = strings(), p = profile();
    var session = {
      start: d.start ? new Date(d.start) : null,
      duration: d.duration,
      indoor: d.indoor === "1",
      temp: d.temp, uv: d.uv, rain: d.rain, wind: d.wind
    };
    var items = recommend(p, session, T);
    render(box.querySelector("[data-health-list]"), items, T, d.sprite);
    var hasProfile = p && (parseFloat(p.weight) > 0 || parseFloat(p.age) > 0);
    var cta = box.querySelector("[data-health-cta]");
    if (cta) cta.hidden = !!hasProfile;
    var note = box.querySelector("[data-health-personal]");
    if (note) note.hidden = !hasProfile;
  });
})();
