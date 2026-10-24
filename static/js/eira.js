// SPDX-License-Identifier: EUPL-1.2
// Eira: melloras progresivas. Todo funciona sen JavaScript; isto só engade comodidade.
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  // Menú móbil accesible
  function setupMenu() {
    var toggle = document.querySelector(".menu-toggle");
    var nav = document.getElementById("primary-nav");
    if (!toggle || !nav) return;
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!open));
      nav.setAttribute("data-collapsed", String(open));
      if (!open) { var first = nav.querySelector("a"); if (first) first.focus(); }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
        toggle.setAttribute("aria-expanded", "false");
        nav.setAttribute("data-collapsed", "true");
        toggle.focus();
      }
    });
  }

  // Anuncios aria-live tras cada intercambio HTMX
  function announce(text) {
    var live = document.getElementById("live");
    if (!live || !text) return;
    live.textContent = "";
    window.setTimeout(function () { live.textContent = text; }, 50);
  }
  window.eiraAnnounce = announce;

  document.addEventListener("htmx:afterSwap", function (e) {
    var root = e.detail.target || document;
    var el = root.querySelector ? (root.matches && root.matches("[data-announce]") ? root : root.querySelector("[data-announce]")) : null;
    if (el) announce(el.getAttribute("data-announce"));
    var focusEl = root.querySelector && root.querySelector("[data-focus]");
    if (focusEl) { focusEl.setAttribute("tabindex", "-1"); focusEl.focus(); }
  });
  document.addEventListener("htmx:responseError", function () {
    announce(document.documentElement.lang === "es" ? "Se produjo un error. Inténtalo de nuevo." : "Produciuse un erro. Téntao de novo.");
  });

  // Estado da conexión
  function updateOnline() {
    var banner = document.getElementById("offline-banner");
    if (banner) banner.hidden = navigator.onLine;
  }
  window.addEventListener("online", function () { updateOnline(); flushQueue(); });
  window.addEventListener("offline", updateOnline);

  // Escala de esforzo: unha persoa tras outra, con avance automático ao escoller
  function setupRpe(form) {
    var people = Array.prototype.slice.call(form.querySelectorAll(".rpe-person"));
    if (!people.length) return;
    var done = form.querySelector("[data-rpe-done]");
    var dots = Array.prototype.slice.call(form.querySelectorAll("[data-dot]"));
    var current = 0;
    var timer = null;
    form.classList.add("is-flow");
    form.querySelectorAll(".rpe-progress, .rpe-nav, [data-rpe-back], .rpe-done__title, [data-rpe-summary]").forEach(function (el) { el.hidden = false; });
    function answered(p) { return !!p.querySelector("input:checked"); }
    function summary() {
      var list = form.querySelector("[data-rpe-summary]");
      list.textContent = "";
      people.forEach(function (p) {
        var li = document.createElement("li");
        var name = document.createElement("span");
        name.textContent = p.getAttribute("data-name");
        var val = document.createElement("strong");
        var c = p.querySelector("input:checked");
        val.textContent = c ? c.value : (p.getAttribute("data-skip") || "—");
        li.appendChild(name);
        li.appendChild(val);
        list.appendChild(li);
      });
    }
    function show(i) {
      window.clearTimeout(timer);
      current = i;
      people.forEach(function (p, j) { p.classList.toggle("is-current", j === i); });
      done.classList.toggle("is-current", i >= people.length);
      dots.forEach(function (d, j) {
        d.classList.toggle("is-current", j === i);
        d.classList.toggle("is-done", answered(people[j]));
      });
      if (i >= people.length) {
        summary();
        var t = form.querySelector(".rpe-done__title");
        t.setAttribute("tabindex", "-1");
        t.focus();
        if (window.eiraAnnounce) window.eiraAnnounce(t.textContent);
        return;
      }
      var p = people[i];
      if (window.eiraAnnounce) window.eiraAnnounce(p.getAttribute("data-name") + ", " + p.querySelector(".rpe-count").textContent);
      var target = p.querySelector("input:checked") || p.querySelector("input") || p.querySelector("[data-rpe-next]");
      if (target) target.focus({ preventScroll: true });
    }
    form.addEventListener("change", function (e) {
      if (e.target.type !== "radio") return;
      if (dots[current]) dots[current].classList.add("is-done");
      window.clearTimeout(timer);
      // Pausa curta: a persoa ve a súa elección antes de pasar á seguinte
      timer = window.setTimeout(function () { show(current + 1); }, 650);
    });
    form.addEventListener("click", function (e) {
      if (e.target.closest("[data-rpe-next]")) show(current + 1);
      else if (e.target.closest("[data-rpe-prev]")) show(Math.max(0, current - 1));
      else if (e.target.closest("[data-rpe-back]")) show(people.length - 1);
    });
    var firstPending = people.findIndex(function (p) { return p.querySelector("input") && !answered(p); });
    show(firstPending === -1 ? 0 : firstPending);
  }
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-rpe-flow]").forEach(setupRpe);
  });

  // Valoración: as etiquetas aparecen ao escoller; «Avisar ao concello» só con «Mal»
  function setupRating(box) {
    function sync() {
      var c = box.querySelector('input[type="radio"]:checked');
      box.classList.toggle("has-score", !!c);
      box.classList.toggle("is-bad", !!c && c.value === "bad");
    }
    box.addEventListener("change", sync);
    sync();
  }
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-rating]").forEach(setupRating);
  });

  // Lapelas accesibles: [data-tabs] > [role=tablist] + [role=tabpanel]
  function setupTabs(root) {
    var tabs = Array.prototype.slice.call(root.querySelectorAll('[role="tab"]'));
    if (!tabs.length) return;
    function select(tab, focus) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute("aria-selected", String(on));
        t.tabIndex = on ? 0 : -1;
        document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
      });
      if (focus) tab.focus();
    }
    tabs.forEach(function (t, i) {
      t.addEventListener("click", function () { select(t, false); });
      t.addEventListener("keydown", function (e) {
        var j = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
        if (j === undefined) return;
        e.preventDefault();
        select(tabs[(j + tabs.length) % tabs.length], true);
      });
    });
    root.querySelector('[role="tablist"]').hidden = false;
    root.classList.add("is-ready");
    var withErrors = root.querySelector("[data-has-errors]");
    var first = withErrors ? document.getElementById(withErrors.getAttribute("aria-labelledby"))
      : (root.querySelector('[role="tab"][data-initial]') || tabs[0]);
    select(first, false);
  }
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-tabs]").forEach(setupTabs);
  });
  // Contido novo por HTMX (p. ex. cambio de semana no selector de franxas)
  document.addEventListener("htmx:afterSwap", function (e) {
    var root = e.detail.target;
    if (root && root.querySelectorAll) root.querySelectorAll("[data-tabs]").forEach(setupTabs);
  });

  // Selector de franxas: tocar unha pastilla escóllea e amosa o resumo fixo con «Reservar».
  // Sen JS, a pastilla é unha ligazón normal á confirmación.
  document.addEventListener("click", function (e) {
    var pill = e.target.closest && e.target.closest("a.pill[data-pick]");
    if (!pill) return;
    var picker = pill.closest("[data-picker]");
    var sum = picker && picker.querySelector("[data-picksum]");
    if (!sum) return;
    e.preventDefault();
    picker.querySelectorAll("a.pill[aria-current]").forEach(function (p) { p.removeAttribute("aria-current"); });
    pill.setAttribute("aria-current", "true");
    sum.querySelector("[data-picksum-when]").textContent = pill.getAttribute("data-pick");
    sum.querySelector("[data-picksum-price]").textContent = pill.getAttribute("data-price") || "";
    sum.querySelector("[data-picksum-base]").textContent = pill.getAttribute("data-base") || "";
    sum.querySelector("[data-picksum-go]").setAttribute("href", pill.getAttribute("href"));
    sum.hidden = false;
  });

  // Instalación da app (Chrome/Android); en iPhone móstranse as instrucións
  var installEvent = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    installEvent = e;
    document.querySelectorAll("[data-install]").forEach(function (b) { b.hidden = false; });
  });
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-install]");
    if (!b || !installEvent) return;
    installEvent.prompt();
    installEvent = null;
    b.hidden = true;
  });

  // Service worker (PWA)
  if ("serviceWorker" in navigator && window.isSecureContext) {
    navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }).catch(function () {});
  }

  // ---------- Cola sen conexión (app do operario) ----------
  var DB = "eira-offline", STORE = "queue";
  function openDb() {
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open(DB, 1);
      req.onupgradeneeded = function () { req.result.createObjectStore(STORE, { keyPath: "id", autoIncrement: true }); };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }
  function withStore(mode, fn) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, mode);
        var result = fn(tx.objectStore(STORE));
        tx.oncomplete = function () { resolve(result && result.result !== undefined ? result.result : result); };
        tx.onerror = function () { reject(tx.error); };
      });
    });
  }
  function serializeForm(form, submitter) {
    var entries = [];
    var fd;
    try { fd = submitter ? new FormData(form, submitter) : new FormData(form); } catch (err) { fd = new FormData(form); }
    fd.forEach(function (value, key) { entries.push([key, value]); });
    // OLLO: un campo name="action" tapa form.action; úsase o atributo ou a URL actual.
    return { url: form.getAttribute("action") || window.location.href, entries: entries, label: form.getAttribute("data-offline-label") || "", at: new Date().toISOString() };
  }
  function queueCount() {
    if (!("indexedDB" in window)) return Promise.resolve(0);
    return withStore("readonly", function (s) { return s.count(); });
  }
  function renderQueue() {
    var el = document.querySelector("[data-queue-count]");
    if (!el) return;
    queueCount().then(function (n) {
      el.hidden = n === 0;
      el.querySelector("[data-n]").textContent = String(n);
    });
  }
  function flushQueue() {
    if (!("indexedDB" in window) || !navigator.onLine) return Promise.resolve();
    return withStore("readonly", function (s) { return s.getAll(); }).then(function (items) {
      return items.reduce(function (p, item) {
        return p.then(function () {
          var fd = new FormData();
          item.entries.forEach(function (kv) { fd.append(kv[0], kv[1]); });
          return fetch(item.url, { method: "POST", body: fd, credentials: "same-origin", headers: { "X-Eira-Sync": "1" } })
            .then(function (resp) {
              if (resp.ok || resp.status === 409 || resp.status === 404) {
                return withStore("readwrite", function (s) { return s.delete(item.id); });
              }
            }).catch(function () {});
        });
      }, Promise.resolve());
    }).then(function () {
      renderQueue();
      queueCount().then(function (n) { if (n === 0 && document.querySelector("[data-queue-count]")) announce(document.documentElement.lang === "es" ? "Cambios sincronizados." : "Cambios sincronizados."); });
    });
  }
  function setupOfflineForms() {
    document.querySelectorAll("form[data-offline-queue]").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        if (navigator.onLine) return;
        e.preventDefault();
        withStore("readwrite", function (s) { return s.add(serializeForm(form, e.submitter)); }).then(function () {
          renderQueue();
          var msg = form.getAttribute("data-offline-message") || "Gardado sen conexión.";
          announce(msg);
          var note = form.querySelector("[data-offline-note]");
          if (note) { note.hidden = false; note.textContent = msg; }
        });
      });
    });
    renderQueue();
    if (navigator.onLine) flushQueue();
  }
  window.eiraFlushQueue = flushQueue;

  // ---------- Teclado do simulador de pechadura ----------
  function setupKeypad() {
    document.querySelectorAll("[data-keypad]").forEach(function (pad) {
      var input = document.getElementById(pad.getAttribute("data-keypad"));
      pad.addEventListener("click", function (e) {
        var btn = e.target.closest("button[data-key]");
        if (!btn || !input) return;
        e.preventDefault();
        var key = btn.getAttribute("data-key");
        if (key === "del") input.value = input.value.slice(0, -1);
        else if (key === "ok") { input.form.requestSubmit(); return; }
        else if (input.value.length < (parseInt(input.getAttribute("maxlength"), 10) || 8)) input.value += key;
        input.focus();
      });
    });
  }

  // ---------- Botóns de asistencia (tableta) sen recargar ----------
  function setupToggles() {
    document.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-toggle-input]");
      if (!btn) return;
      var input = document.getElementById(btn.getAttribute("data-toggle-input"));
      if (!input) return;
      e.preventDefault();
      var on = btn.getAttribute("aria-pressed") !== "true";
      btn.setAttribute("aria-pressed", String(on));
      input.value = on ? "1" : "0";
      var mark = btn.querySelector(".mark");
      if (mark) mark.textContent = on ? "✓" : "";
      var counter = document.querySelector("[data-present-count]");
      if (counter) counter.textContent = String(document.querySelectorAll('button[data-toggle-input][aria-pressed="true"]').length);
    });
  }

  // Enviar automaticamente un formulario ao cambiar un select (filtros), con botón de reserva sen JS
  function setupAutoSubmit() {
    document.querySelectorAll("form[data-autosubmit]").forEach(function (form) {
      form.addEventListener("change", function () { if (form.requestSubmit) form.requestSubmit(); else form.submit(); });
    });
  }

  // v4.1: botón «Día / Noite» da demo. Cambia o tema ao momento (a ilustración fai crossfade)
  // e gárdao na sesión en segundo plano; sen JS o formulario envíase e recarga.
  document.addEventListener("submit", function (e) {
    var form = e.target.closest ? e.target.closest("form[data-theme-toggle]") : null;
    if (!form || !window.fetch) return;
    e.preventDefault();
    var root = document.documentElement;
    var dark = !root.classList.contains("theme-dark");
    root.setAttribute("data-theme", dark ? "dark" : "light");
    if (window.eiraApplyTheme) window.eiraApplyTheme();
    syncThemeToggles();
    var data = new FormData(form);
    data.set("tema", dark ? "dark" : "light");
    fetch(form.action, { method: "POST", body: data, credentials: "same-origin", headers: { "X-Eira-Theme": "1" } });
    var es = root.lang === "es";
    announce(dark ? (es ? "Tema de noche activado" : "Tema de noite activado") : (es ? "Tema de día activado" : "Tema de día activado"));
  });
  function syncThemeToggles() {
    var dark = document.documentElement.classList.contains("theme-dark");
    document.querySelectorAll("form[data-theme-toggle]").forEach(function (f) {
      f.querySelector("button").setAttribute("aria-pressed", dark ? "true" : "false");
      f.querySelector("input[name=tema]").value = dark ? "light" : "dark";
    });
  }

  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-print]")) { e.preventDefault(); window.print(); }
  });

  document.addEventListener("DOMContentLoaded", function () {
    var f = document.querySelector("[data-focus]");
    if (f) { f.setAttribute("tabindex", "-1"); f.focus(); }
    setupMenu(); syncThemeToggles(); updateOnline(); setupOfflineForms(); setupKeypad(); setupToggles(); setupAutoSubmit();
  });
})();
