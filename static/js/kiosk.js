// SPDX-License-Identifier: EUPL-1.2
// Tableta da monitora (patrón do quiosco AFS +50, adaptado a Eira; sen datos de alí):
// abecedario do primeiro apelido → nomes → Entrada (rexistra e volve) ou Saída (escala RPE → grazas →
// volta soa aos 3 s). Funciona sen conexión: cada toque vai a unha cola local e envíase cando hai rede.
(function () {
  "use strict";
  var ALPHABET = "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ".split("");
  var BACK_IN_MS = 1500, BACK_OUT_MS = 3000, FLUSH_MS = 15000;

  function fold(s) {
    var out = "";
    s = (s || "").toUpperCase();
    for (var i = 0; i < s.length; i++) {
      var ch = s[i];
      out += ch === "Ñ" ? ch : ch.normalize("NFD")[0];
    }
    return out;
  }
  function fill(s, a, b) { return String(s || "").replace("%1", a).replace("%2", b === undefined ? "" : b); }
  function el(tag, attrs, children) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") e.textContent = attrs[k];
      else if (k === "on") Object.keys(attrs.on).forEach(function (ev) { e.addEventListener(ev, attrs.on[ev]); });
      else if (attrs[k] !== null && attrs[k] !== undefined && attrs[k] !== false) e.setAttribute(k, attrs[k] === true ? "" : attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) e.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return e;
  }

  function init(root) {
    var data = JSON.parse(document.getElementById("kiosk-data").textContent);
    var T = document.getElementById("kiosk-strings").dataset;
    var sprite = root.dataset.sprite;
    var view = root.querySelector("[data-view]");
    var QKEY = "eira-kiosk-" + data.session;
    var people = data.people;
    var byId = {};
    people.forEach(function (p) { byId[p.id] = p; });
    var state = { mode: "in", letter: null, person: null, search: "", filter: "" };
    var timer = null;

    function icon(name, cls) {
      var ns = "http://www.w3.org/2000/svg";
      var svg = document.createElementNS(ns, "svg");
      svg.setAttribute("class", "icon " + (cls || ""));
      svg.setAttribute("aria-hidden", "true");
      var use = document.createElementNS(ns, "use");
      use.setAttribute("href", sprite + "#" + name);
      svg.appendChild(use);
      return svg;
    }

    // ---- Cola sen conexión ----
    function queue() { try { return JSON.parse(localStorage.getItem(QKEY) || "[]"); } catch (e) { return []; } }
    function saveQueue(q) { try { localStorage.setItem(QKEY, JSON.stringify(q)); } catch (e) { /* modo privado */ } }
    // Ao abrir, os toques aínda sen enviar aplícanse á lista (o servidor pode non telos)
    queue().forEach(function (ev) { apply(ev); });
    var flushing = false;
    function csrf() {
      try { return JSON.parse(document.body.getAttribute("hx-headers"))["X-CSRFToken"]; } catch (e) { return ""; }
    }
    function flush() {
      var q = queue();
      if (!q.length || flushing || !navigator.onLine) { renderStats(); return; }
      flushing = true;
      fetch(data.api, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body: JSON.stringify(q)
      }).then(function (r) {
        if (!r.ok) throw new Error(r.status);
        var rest = queue().slice(q.length);  // o que se engadiu mentres se enviaba
        saveQueue(rest);
      }).catch(function () { /* sen rede: queda na cola */ }).then(function () {
        flushing = false;
        renderStats();
      });
    }
    window.addEventListener("online", flush);
    setInterval(flush, FLUSH_MS);

    function apply(ev) {
      var p = byId[ev.enrollment];
      if (!p) return;
      p["in"] = true;
      if (ev.action === "out" && ev.value !== null && ev.value !== undefined && p.effort) p.rpe = ev.value;
    }
    function record(p, action, value) {
      var ev = { enrollment: p.id, action: action, value: value === undefined ? null : value, at: new Date().toISOString() };
      apply(ev);
      var q = queue(); q.push(ev); saveQueue(q);
      flush();
    }

    // ---- Cabeceira ----
    root.querySelectorAll("[data-mode]").forEach(function (b) {
      b.addEventListener("click", function () {
        state.mode = b.dataset.mode;
        root.querySelectorAll("[data-mode]").forEach(function (o) { o.setAttribute("aria-pressed", String(o === b)); });
        root.classList.toggle("kiosk--out", state.mode === "out");
        renderMissing();
        home();
      });
    });
    var missingBtn = root.querySelector("[data-missing-toggle]");
    var missingBox = root.querySelector("[data-missing]");
    missingBtn.addEventListener("click", function () {
      missingBox.hidden = !missingBox.hidden;
      missingBtn.setAttribute("aria-expanded", String(!missingBox.hidden));
      renderMissing();
    });
    function missingList() {
      return people.filter(function (p) { return state.mode === "in" ? !p["in"] : (p["in"] && p.effort && p.rpe === null); });
    }
    function renderMissing() {
      var list = missingList();
      missingBtn.textContent = fill(T.missing, list.length);
      if (missingBox.hidden) return;
      missingBox.textContent = "";
      missingBox.appendChild(el("h2", { class: "kiosk__missing-title", text: state.mode === "in" ? T.missingIn : T.missingOut }));
      if (!list.length) { missingBox.appendChild(el("p", { text: T.noneMissing })); return; }
      missingBox.appendChild(el("ul", { class: "kiosk__missing-list", role: "list" },
        list.map(function (p) { return el("li", {}, [el("button", { type: "button", class: "linklike", text: p.label, on: { click: function () { pick(p); } } })]); })));
    }
    function renderStats() {
      var n = people.length, inside = people.filter(function (p) { return p["in"]; }).length;
      var rpe = people.filter(function (p) { return p.rpe !== null; }).length;
      root.querySelector("[data-stat-in]").textContent = fill(T.entered, inside, n);
      root.querySelector("[data-stat-rpe]").textContent = fill(T.rpeCount, rpe);
      var pend = queue().length, sync = root.querySelector("[data-sync]");
      sync.textContent = !pend ? T.syncOk : (navigator.onLine ? fill(T.syncPending, pend) : fill(T.syncOffline, pend));
      sync.classList.toggle("is-warn", pend > 0);
      renderMissing();
    }

    // ---- Vistas ----
    function show(nodes, focusFirst) {
      if (timer) { clearTimeout(timer); timer = null; }
      view.textContent = "";
      nodes.forEach(function (n) { if (n) view.appendChild(n); });
      renderStats();
      if (focusFirst) { var f = view.querySelector(focusFirst); if (f) f.focus(); }
    }
    function nameButton(p) {
      var marks = [];
      if (p["in"]) marks.push(el("span", { class: "kiosk__mark", text: "✓ " + T.inMark }));
      if (p.rpe !== null) marks.push(el("span", { class: "kiosk__mark kiosk__mark--rpe rpe-v" + p.rpe, text: "RPE " + p.rpe }));
      var parts = p.surnames ? [el("span", { class: "kiosk__surnames", text: p.surnames }), el("span", { class: "kiosk__first", text: p.name })] : [el("span", { class: "kiosk__surnames", text: p.name })];
      return el("button", {
        type: "button", class: "kiosk__name" + (p["in"] ? " is-in" : ""), "data-person": p.id,
        "aria-label": p.label + ", " + (p.photo ? T.photoOk : T.photoNo) + (p["in"] ? ", " + T.inMark : "") + (p.rpe !== null ? ", RPE " + p.rpe : ""),
        on: { click: function () { pick(p); } }
      }, [el("span", { class: "kiosk__photo " + (p.photo ? "is-on" : "is-off") }, [icon(p.photo ? "camera" : "camera-off")]),
          el("span", { class: "kiosk__nametext" }, parts), el("span", { class: "kiosk__marks" }, marks)]);
    }
    function names(list, empty) {
      if (!list.length) return el("p", { class: "kiosk__empty", text: empty });
      return el("div", { class: "kiosk__names", role: "list" }, list.map(function (p) {
        var b = nameButton(p); b.setAttribute("role", "listitem"); return b;
      }));
    }
    function home() {
      state.letter = null; state.person = null; state.filter = "";
      var results = el("div", { class: "kiosk__results", "aria-live": "polite" });
      var input = el("input", {
        type: "search", class: "kiosk__search", placeholder: T.search, "aria-label": T.searchLabel, autocomplete: "off", value: state.search,
        on: { input: function (e) { state.search = e.target.value; renderResults(); } }
      });
      function renderResults() {
        results.textContent = "";
        var q = fold(state.search.trim());
        if (q.length < 2) return;
        var list = people.filter(function (p) { return fold(p.label).indexOf(q) !== -1 || fold(p.name + " " + p.surnames).indexOf(q) !== -1; }).slice(0, 60);
        results.appendChild(names(list, T.noMatch));
      }
      var counts = {};
      people.forEach(function (p) { counts[p.initial] = (counts[p.initial] || 0) + 1; });
      var grid = el("div", { class: "kiosk__letters", role: "group", "aria-label": T.pickLetter }, ALPHABET.map(function (L) {
        var n = counts[L] || 0;
        return el("button", {
          type: "button", class: "kiosk__letter" + (n ? " has-people" : " is-empty"), disabled: n === 0, "data-letter": L,
          "aria-label": L + ": " + (n ? (n === 1 ? T.person : fill(T.persons, n)) : T.noLetter),
          on: { click: function () { letter(L); } }
        }, [el("span", { class: "kiosk__L", "aria-hidden": "true", text: L }), n ? el("span", { class: "kiosk__count", "aria-hidden": "true", text: String(n) }) : null]);
      }));
      show([el("h2", { class: "kiosk__question", text: T.pickLetter }),
            el("div", { class: "kiosk__searchrow" }, [input, el("button", { type: "button", class: "btn btn-secondary", text: T.clear, on: { click: function () { state.search = ""; input.value = ""; renderResults(); input.focus(); } } })]),
            results, grid]);
      renderResults();
    }
    function letter(L) {
      state.letter = L;
      var list = people.filter(function (p) { return p.initial === L; });
      var box = el("div");
      function paint() {
        box.textContent = "";
        var f = fold(state.filter.trim());
        box.appendChild(names(f ? list.filter(function (p) { return fold(p.label).indexOf(f) !== -1; }) : list, T.noPeople));
      }
      paint();
      show([el("div", { class: "kiosk__bar" }, [
              el("button", { type: "button", class: "btn btn-secondary btn-lg", text: "← " + T.back, on: { click: home } }),
              el("h2", { class: "kiosk__question" }, [T.letterTitle + " ", el("span", { class: "kiosk__bigL", text: L })])]),
            list.length > 6 ? el("input", { type: "search", class: "kiosk__search", placeholder: T.filter, "aria-label": T.filter, autocomplete: "off",
              on: { input: function (e) { state.filter = e.target.value; paint(); } } }) : null,
            box], ".kiosk__name");
    }
    function pick(p) {
      state.person = p;
      if (state.mode === "in") {
        record(p, "in");
        thanks(p, fill(T.inDone, new Date().toTimeString().slice(0, 5)), BACK_IN_MS);
      } else if (!p.effort) {
        record(p, "out", null);
        thanks(p, T.noEffort, BACK_OUT_MS);
      } else {
        rpe(p);
      }
    }
    function rpe(p) {
      var omni = data.scale === "omni";
      var grid = el("div", { class: "kiosk__rpe rpe-scale--" + data.scale, role: "group", "aria-label": T.question }, data.points.map(function (pt) {
        return el("button", {
          type: "button", class: "kiosk__rpebtn rpe-v" + pt.value, "data-rpe": pt.value,
          "aria-label": pt.value + (pt.label ? ", " + pt.label : ""),
          on: { click: function (e) {
            e.currentTarget.classList.add("is-pressed");
            record(p, "out", pt.value);
            setTimeout(function () { thanks(p, fill(T.rpeDone, pt.value) + (pt.label ? " · " + pt.label : ""), BACK_OUT_MS, pt.value); }, 150);
          } }
        }, [omni ? icon(pt.face, "kiosk__face") : null, el("span", { class: "kiosk__rpenum", "aria-hidden": "true", text: String(pt.value) }),
            el("span", { class: "kiosk__rpelbl", "aria-hidden": "true", text: pt.label })]);
      }));
      show([el("div", { class: "kiosk__bar" }, [
              el("button", { type: "button", class: "btn btn-secondary btn-lg", text: "← " + T.notMe, on: { click: function () { state.letter ? letter(state.letter) : home(); } } }),
              el("p", { class: "kiosk__who" }, [el("span", { class: "kiosk__photo " + (p.photo ? "is-on" : "is-off") }, [icon(p.photo ? "camera" : "camera-off")]), p.label])]),
            p.rpe !== null ? el("p", { class: "alert", text: fill(T.already, p.rpe) }) : null,
            el("h2", { class: "kiosk__question kiosk__question--center", text: T.question }),
            grid,
            el("p", { class: "kiosk__help", text: T.savedOnTap })], ".kiosk__rpebtn");
    }
    function thanks(p, detail, ms, value) {
      var bar = el("div", { class: "kiosk__progress", "aria-hidden": "true" }, [el("span")]);
      show([el("section", { class: "kiosk__thanks", role: "status" }, [
        icon("check", "kiosk__check"),
        el("h2", { class: "kiosk__thanks-title", text: fill(T.thanks, p.name) }),
        el("p", { class: "kiosk__thanks-detail" + (value !== undefined ? " rpe-v" + value : ""), text: detail }),
        el("button", { type: "button", class: "btn btn-lg", text: T.next, on: { click: home } }),
        bar])], ".kiosk__thanks .btn");
      bar.firstChild.style.transitionDuration = ms + "ms";
      requestAnimationFrame(function () { requestAnimationFrame(function () { bar.firstChild.classList.add("is-running"); }); });
      timer = setTimeout(home, ms);
    }
    home();
    flush();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.querySelector("[data-kiosk]");
    if (root) init(root);
  });
})();
