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

  // Service worker (PWA)
  if ("serviceWorker" in navigator && window.isSecureContext) {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {});
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
    return { url: form.action, entries: entries, label: form.getAttribute("data-offline-label") || "", at: new Date().toISOString() };
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

  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-print]")) { e.preventDefault(); window.print(); }
  });

  document.addEventListener("DOMContentLoaded", function () {
    var f = document.querySelector("[data-focus]");
    if (f) { f.setAttribute("tabindex", "-1"); f.focus(); }
    setupMenu(); updateOnline(); setupOfflineForms(); setupKeypad(); setupToggles(); setupAutoSubmit();
  });
})();
