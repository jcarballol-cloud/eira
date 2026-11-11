// SPDX-License-Identifier: EUPL-1.2
// v1.5.1: guía paso a paso do perfil. Diálogo modal accesible (<dialog> + showModal): o foco
// entra, non escapa e volve ao pechar; Esc pecha; frechas e tabulador navegan; cada paso
// anúnciase. Se o elemento dun paso non existe ou non se ve, o paso vai centrado.
(function () {
  "use strict";
  var dataEl = document.getElementById("tour-data");
  var dlg = document.getElementById("tour");
  if (!dataEl || !dlg || typeof dlg.showModal !== "function") return;

  var tour;
  try { tour = JSON.parse(dataEl.textContent); } catch (e) { return; }
  if (!tour || !tour.steps || !tour.steps.length) return;

  var KEY = "eira-tour-" + tour.id;
  var ring = dlg.querySelector(".tour__ring");
  var panel = dlg.querySelector(".tour__panel");
  var stepEl = document.getElementById("tour-step");
  var titleEl = document.getElementById("tour-title");
  var bodyEl = document.getElementById("tour-body");
  var live = document.getElementById("tour-live");
  var prevBtn = dlg.querySelector("[data-tour-prev]");
  var nextBtn = dlg.querySelector("[data-tour-next]");
  var closeBtn = dlg.querySelector("[data-tour-close]");
  var index = 0;
  var opener = null;
  var target = null;
  var opened = []; // <details> abertos pola guía para mostrar un elemento; péchanse despois

  // localStorage pode non estar (navegación privada, cookies bloqueadas): entón non se lembra
  function seen() { try { return window.localStorage.getItem(KEY) === "1"; } catch (e) { return false; } }
  function markSeen() { try { window.localStorage.setItem(KEY, "1"); } catch (e) { /* sen memoria */ } }

  function isVisible(el) {
    if (!el || dlg.contains(el)) return false;
    var r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    var s = window.getComputedStyle(el);
    return s.visibility !== "hidden" && s.display !== "none";
  }

  function restoreDetails() {
    while (opened.length) opened.pop().open = false;
  }

  function findTarget(selector) {
    if (!selector) return null;
    var els;
    try { els = document.querySelectorAll(selector); } catch (e) { return null; }
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      var mine = [];
      // Se está nun menú despregable pechado (p. ex. «Máis ferramentas»), ábrese mentres dura o paso
      for (var d = el.parentElement; d; d = d.parentElement) {
        if (d.tagName === "DETAILS" && !d.open) { d.open = true; mine.push(d); }
      }
      if (isVisible(el)) { opened = opened.concat(mine); return el; }
      while (mine.length) mine.pop().open = false;
    }
    return null;
  }

  function overlaps(a, b) {
    return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
  }

  // Parte do elemento que debe quedar á vista: todo, ou a cabeza se é moi alto (p. ex. unha lista)
  function band(r, max) {
    return { left: r.left, right: r.right, top: r.top, bottom: Math.min(r.bottom, r.top + max) };
  }

  function place(side) {
    dlg.classList.remove("tour--top", "tour--bottom");
    dlg.classList.add("tour--" + side);
    var gap = panel.getBoundingClientRect().height + 24;
    var room = window.innerHeight - gap - 32;
    var tall = target.getBoundingClientRect().height > room;
    // Deixar o elemento á vista sen que o tape o panel (scroll-margin, sen animación)
    target.style.scrollMarginTop = (side === "top" ? gap : 16) + "px";
    target.style.scrollMarginBottom = (side === "bottom" ? gap : 16) + "px";
    target.scrollIntoView({ block: tall ? "start" : "nearest", inline: "nearest", behavior: "instant" });
    target.style.scrollMarginTop = "";
    target.style.scrollMarginBottom = "";
    var r = target.getBoundingClientRect();
    return !overlaps(band(r, tall ? Math.max(room, 120) : r.height), panel.getBoundingClientRect());
  }

  function position() {
    if (!target) { dlg.classList.remove("tour--top", "tour--bottom"); drawRing(); return; }
    if (!place("bottom") && !place("top")) place("bottom");
    drawRing();
  }

  function drawRing() {
    if (!target) { ring.hidden = true; return; }
    var r = target.getBoundingClientRect();
    var pad = 6;
    ring.style.top = (r.top - pad) + "px";
    ring.style.left = (r.left - pad) + "px";
    ring.style.width = (r.width + pad * 2) + "px";
    ring.style.height = (r.height + pad * 2) + "px";
    ring.hidden = false;
  }

  function render() {
    var step = tour.steps[index];
    var total = tour.steps.length;
    restoreDetails();
    var label = tour.labels.step.replace("%(n)s", index + 1).replace("%(total)s", total);
    stepEl.textContent = label;
    titleEl.textContent = step.title;
    bodyEl.textContent = step.body;
    prevBtn.hidden = index === 0;
    nextBtn.textContent = index === total - 1 ? tour.labels.done : tour.labels.next;

    target = findTarget(step.target);
    dlg.classList.toggle("tour--center", !target);
    position();
    dlg.setAttribute("data-step", String(index + 1));
    dlg.setAttribute("data-target", target ? step.target : "");
    live.textContent = "";
    window.setTimeout(function () { live.textContent = label + ". " + step.title + ". " + step.body; }, 60);
  }

  function go(delta) {
    var n = index + delta;
    if (n < 0) return;
    if (n >= tour.steps.length) { close(); return; }
    var focusWasPrev = document.activeElement === prevBtn;
    index = n;
    render();
    if (focusWasPrev && prevBtn.hidden) nextBtn.focus();
  }

  function open() {
    if (dlg.open) return;
    opener = document.activeElement && document.activeElement !== document.body ? document.activeElement : null;
    index = 0;
    dlg.showModal();
    render();
    titleEl.focus();
  }

  function close() {
    markSeen();
    restoreDetails();
    target = null;
    if (dlg.open) dlg.close();
    // Quitar ?guia=1 para que non volva saír ao recargar
    try {
      var url = new URL(window.location.href);
      if (url.searchParams.has("guia")) {
        url.searchParams.delete("guia");
        window.history.replaceState(null, "", url.pathname + url.search + url.hash);
      }
    } catch (e) { /* navegador antigo */ }
    var back = opener && document.contains(opener) ? opener : document.getElementById("main");
    // Se quen abriu a guía quedou oculto (p. ex. dentro do «?» pechado), o foco vai ao «?»
    var pop = back && back.closest ? back.closest("details") : null;
    if (pop && !pop.open) back = pop.querySelector("summary") || back;
    if (back) back.focus();
  }

  function focusables() {
    return Array.prototype.filter.call(
      panel.querySelectorAll("button, [href], [tabindex]:not([tabindex='-1'])"),
      function (el) { return !el.hidden && !el.disabled; }
    );
  }

  prevBtn.addEventListener("click", function () { go(-1); });
  nextBtn.addEventListener("click", function () { go(1); });
  closeBtn.addEventListener("click", close);
  dlg.addEventListener("cancel", function (e) { e.preventDefault(); close(); }); // Esc
  dlg.addEventListener("keydown", function (e) {
    if (e.key === "ArrowRight") { e.preventDefault(); go(1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); go(-1); }
    else if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "Tab") {
      // O foco dá a volta dentro do diálogo
      var items = focusables();
      if (!items.length) return;
      var first = items[0], last = items[items.length - 1];
      if (e.shiftKey && (document.activeElement === first || document.activeElement === titleEl)) {
        e.preventDefault(); last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus();
      }
    }
  });
  window.addEventListener("resize", function () { if (dlg.open) position(); });
  document.addEventListener("scroll", function () { if (dlg.open) drawRing(); }, true);

  // «?» → «Ver a guía» nesta mesma pantalla: ábrea sen recargar
  Array.prototype.forEach.call(document.querySelectorAll("[data-tour-open]"), function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      var pop = a.closest("details");
      if (pop) pop.open = false;
      open();
    });
  });

  var wanted = false;
  try { wanted = new URL(window.location.href).searchParams.get("guia") === "1"; } catch (e) { wanted = false; }
  function start() { if (wanted || (tour.auto && !seen())) open(); }
  // Esperar ás imaxes: se non, a pantalla móvese despois de colocar o panel
  if (document.readyState === "complete") start(); else window.addEventListener("load", start);
})();
