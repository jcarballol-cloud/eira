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

  // Formato breve (v3): de 2 a 4 consellos dunha liña, con cifra e acción, e o detalle en «Ver máis».
  // s: {start, duration, indoor, temp, feels, humidity, uv, rain, wind}
  function recommendBrief(p, s, T) {
    var out = [];
    var age = parseFloat(p.age), weight = parseFloat(p.weight), weekly = parseFloat(p.minutes);
    var dur = s ? parseFloat(s.duration) || 0 : 0;
    var adult = age >= 18 || (!(age > 0) && weight > 0);
    var minor = age > 0 && age < 18;
    var hasWx = s && s.temp !== undefined && s.temp !== null && s.temp !== "";
    var t = hasWx ? Math.round(parseFloat(s.temp)) : null;
    var feels = hasWx && s.feels !== undefined && s.feels !== "" ? Math.round(parseFloat(s.feels)) : t;
    var uv = hasWx ? parseFloat(s.uv) || 0 : 0, rain = hasWx ? parseFloat(s.rain) || 0 : 0, wind = hasWx ? parseFloat(s.wind) || 0 : 0;
    var outdoor = s && !s.indoor;
    var hot = hasWx && feels >= 27, cold = hasWx && feels <= 8;
    // 1. Tempo da franxa → acción
    if (hasWx) {
      var bits = [fill(T.bTemp, fmtNum(t))];
      if (Math.abs(feels - t) >= 2) bits = [fill(T.bFeels, fmtNum(feels))];
      if (outdoor && uv >= 3) bits.push(fill(T.bUv, fmtNum(uv)));
      if (outdoor && rain >= 60) bits.push(fill(T.bRain, fmtNum(rain)));
      if (outdoor && wind >= 35) bits.push(fill(T.bWind, fmtNum(wind)));
      var act = hot ? T.aHot : (outdoor && uv >= 6 ? T.aUv : (cold ? T.aCold : (outdoor && rain >= 60 ? T.aRain : (outdoor && wind >= 35 ? T.aWind : (outdoor && uv >= 3 ? T.aUvMid : T.aOk)))));
      out.push({ icon: hot ? "sun-hot" : (cold ? "thermo" : (outdoor && rain >= 60 ? "rain" : "sun")), text: bits.join(" · ") + " → " + act,
                 more: fill(T.mWx, fmtNum(t), fmtNum(feels)) + " " + fill(T.mWx2, fmtNum(parseFloat(s.humidity) || 0), fmtNum(wind)), source: T.srcWx });
    }
    // 2. Antes: 5–7 ml/kg entre catro e dúas horas antes (ACSM 2007) — cantidade só para adultos
    if (adult && weight > 0) {
      var early = s && s.start && new Date(s.start.getTime() - 4 * 3600e3).getHours() < 7;
      if (early) {
        // Sesión de primeira hora: non ten sentido beber ás 5 da mañá; 3–5 ml/kg ao espertar (2 h antes)
        out.push({ icon: "droplet", text: fill(T.bBeforeWake, fmtNum(round50(weight * 3)) + "–" + fmtNum(round50(weight * 5))), more: T.mBeforeWake, source: "ACSM 2007" });
      } else {
        var lo = round50(weight * 5), hi = round50(weight * 7);
        var when = s && s.start ? fill(T.bBeforeWhen, hhmm(new Date(s.start.getTime() - 4 * 3600e3)), hhmm(new Date(s.start.getTime() - 2 * 3600e3))) : T.bBeforeAny;
        out.push({ icon: "droplet", text: fill(T.bBefore, fmtNum(lo) + "–" + fmtNum(hi)) + " " + when, more: T.mBefore, source: "ACSM 2007" });
      }
    } else if (s) {
      out.push({ icon: "droplet", text: T.bBeforeNoWeight, more: T.mBefore, source: "ACSM 2007" });
    }
    // 3. Durante: 0,4–0,8 l/h repartidos cada 15–20 min (ACSM 2007), se é longa ou fai calor
    if (s && dur > 0 && (dur > 60 || hot)) {
      if (adult) out.push({ icon: "clock", text: fill(T.bDuring, fmtNum(round50(400 / 4)) + "–" + fmtNum(round50(800 / 3))), more: T.mDuring, source: "ACSM 2007" });
      else if (minor) out.push({ icon: "clock", text: T.bDuringMinor, more: T.mDuring, source: "ACSM 2007" });
    }
    // 4. Sesión longa: hidratos e non beber de máis (ACSM/AND/DC 2016; ACSM 2007)
    if (adult && dur >= 90) {
      out.push({ icon: "utensils", text: fill(T.bLong, fmtNum(dur)), more: T.mLong, source: "Thomas, Erdman e Burke 2016 · ACSM 2007", warn: true });
    } else if (adult && weekly >= 0 && !isNaN(weekly) && out.length < 4) {
      out.push({ icon: "chart", text: fill(T.bWeek, fmtNum(weekly + dur)), more: T.mWeek, source: "OMS 2020" });
    }
    if (age >= 65 && out.length < 4) out.push({ icon: "heart", text: T.bSenior, more: T.mSenior, source: "OMS 2020 · EFSA 2010" });
    return out.slice(0, 4);
  }

  function renderBrief(container, items, T, sprite) {
    container.textContent = "";
    if (!items.length) return;
    var ns = "http://www.w3.org/2000/svg";
    var ul = document.createElement("ul");
    ul.className = "tips";
    ul.setAttribute("role", "list");
    var more = document.createElement("details");
    more.className = "tips__more";
    var sum = document.createElement("summary");
    sum.textContent = T.seeMore;
    var ol = document.createElement("ul");
    items.forEach(function (it) {
      var li = document.createElement("li");
      li.className = "tip" + (it.warn ? " tip--warn" : "");
      var svg = document.createElementNS(ns, "svg");
      svg.setAttribute("class", "icon tip__icon");
      svg.setAttribute("aria-hidden", "true");
      var use = document.createElementNS(ns, "use");
      use.setAttribute("href", sprite + "#" + it.icon);
      svg.appendChild(use);
      var txt = document.createElement("span");
      txt.className = "tip__text";
      txt.textContent = it.text;
      li.appendChild(svg); li.appendChild(txt);
      ul.appendChild(li);
      var d = document.createElement("li");
      var strong = document.createElement("strong");
      strong.textContent = it.text;
      d.appendChild(strong);
      d.appendChild(document.createTextNode(" " + it.more + " "));
      var src = document.createElement("small");
      src.textContent = fill(T.source, it.source);
      d.appendChild(src);
      ol.appendChild(d);
    });
    more.appendChild(sum); more.appendChild(ol);
    container.appendChild(ul);
    container.appendChild(more);
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

  window.EiraHealth = { recommend: recommend, render: render, recommendBrief: recommendBrief, renderBrief: renderBrief, profile: profile, saveLocal: saveLocal, clearLocal: clearLocal, loadLocal: loadLocal, strings: strings };

  // Recomendacións dentro dunha reserva
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-health-booking]").forEach(initBox);
  });
  function initBox(box) {
    var d = box.dataset, T = strings(), p = profile();
    var session = {
      start: d.start ? new Date(d.start) : null,
      duration: d.duration,
      indoor: d.indoor === "1",
      temp: d.temp, feels: d.feels, humidity: d.humidity, uv: d.uv, rain: d.rain, wind: d.wind
    };
    var items = recommendBrief(p, session, T);
    renderBrief(box.querySelector("[data-health-list]"), items, T, d.sprite);
    var hasProfile = p && (parseFloat(p.weight) > 0 || parseFloat(p.age) > 0);
    var cta = box.querySelector("[data-health-cta]");
    if (cta) cta.hidden = !!hasProfile;
    var note = box.querySelector("[data-health-personal]");
    if (note) note.hidden = !hasProfile;
  }
})();
