// SPDX-License-Identifier: EUPL-1.2
// v1.5 · A: botón «Escoitar». Usa só a Web Speech API do navegador (speechSynthesis): o texto non
// sae do dispositivo. Non fala se non se lle pide, non move o foco e non usa rexións aria-live
// mentres le, para non interferir con TalkBack nin VoiceOver.
(function () {
  "use strict";
  var core = window.EiraListenCore;
  var synth = window.speechSynthesis;
  var KEYS = { rate: "eira.listen.rate", auto: "eira.listen.autocode", notice: "eira.listen.notice" };
  var memory = {};
  var activeButton = null;
  var noticeShown = false;

  function read(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return memory[key] || null; }
  }
  function write(key, value) {
    memory[key] = value;
    try { window.localStorage.setItem(key, value); } catch (e) { /* só en memoria */ }
  }

  function supported() {
    return !!(synth && window.SpeechSynthesisUtterance && core);
  }

  function setButton(button, speaking) {
    var label = button.querySelector("[data-listen-label]");
    label.textContent = button.getAttribute(speaking ? "data-text-stop" : "data-text-start");
    button.setAttribute("aria-label", button.getAttribute(speaking ? "data-aria-stop" : "data-aria-start"));
    button.classList.toggle("is-speaking", speaking);
  }

  function stop() {
    if (synth) { synth.cancel(); }
    if (activeButton) { setButton(activeButton, false); activeButton = null; }
  }

  // Texto dunha zona, sen botóns, formularios nin nada marcado para omitir.
  function textOf(target) {
    var clone = target.cloneNode(true);
    clone.querySelectorAll(
      "[data-listen-skip], [data-listen-bar], svg, script, style, form, button, nav, [hidden], [aria-hidden='true'], noscript"
    ).forEach(function (node) { node.remove(); });
    clone.querySelectorAll("li, p, h1, h2, h3, dt, dd, div, br").forEach(function (node) {
      node.append(document.createTextNode(". "));
    });
    return core.normalize(clone.textContent).replace(/(\.\s*){2,}/g, ". ").replace(/:\s*\./g, ":");
  }

  function voicesReady(callback) {
    var voices = synth.getVoices();
    if (voices.length) { callback(voices); return; }
    var done = false;
    function finish() {
      if (done) { return; }
      done = true;
      callback(synth.getVoices());
    }
    if (synth.addEventListener) { synth.addEventListener("voiceschanged", finish, { once: true }); }
    window.setTimeout(finish, 800);
  }

  function showFallbackNotice(bar) {
    if (noticeShown || read(KEYS.notice) === "1") { return; }
    noticeShown = true;
    write(KEYS.notice, "1");
    var note = bar && bar.querySelector("[data-listen-note]");
    if (note) { note.hidden = false; note.textContent = note.getAttribute("data-text"); }
  }

  function speak(text, button) {
    stop();
    var parts = core.chunks(text);
    if (!parts.length) { return; }
    voicesReady(function (voices) {
      var choice = core.pickVoice(voices, document.documentElement.lang);
      if (choice.fallback) { showFallbackNotice(button && button.closest("[data-listen-bar]")); }
      var rate = core.rateFor(read(KEYS.rate));
      if (button) { activeButton = button; setButton(button, true); }
      parts.forEach(function (part, index) {
        var utterance = new window.SpeechSynthesisUtterance(part);
        utterance.lang = choice.lang;
        utterance.rate = rate;
        if (choice.voice) { utterance.voice = choice.voice; }
        if (index === parts.length - 1) {
          utterance.onend = utterance.onerror = function () {
            if (button && activeButton === button) { setButton(button, false); activeButton = null; }
          };
        }
        synth.speak(utterance);
      });
    });
  }

  function targetOf(button) {
    return document.querySelector(button.getAttribute("data-listen"));
  }

  function showBars() {
    document.querySelectorAll("[data-listen-bar]").forEach(function (bar) { bar.hidden = false; });
  }

  function setupPreferences() {
    var box = document.getElementById("voz");
    if (!box) { return; }
    box.hidden = false;
    var rate = read(KEYS.rate) === "slow" ? "slow" : "normal";
    box.querySelectorAll("input[data-listen-rate]").forEach(function (input) {
      input.checked = input.value === rate;
      input.addEventListener("change", function () { write(KEYS.rate, input.value); });
    });
    var auto = box.querySelector("[data-listen-auto]");
    if (auto) {
      auto.checked = read(KEYS.auto) === "1";
      auto.addEventListener("change", function () { write(KEYS.auto, auto.checked ? "1" : "0"); });
    }
  }

  function autoReadCode() {
    if (read(KEYS.auto) !== "1") { return; }
    var code = document.querySelector("[data-listen-code]");
    if (code) {
      speak(code.getAttribute("data-listen-prefix") + " " + core.spellCode(code.getAttribute("data-listen-code")), null);
    }
  }

  function init() {
    if (!supported()) { return; }  // Sen speechSynthesis, o botón segue oculto
    showBars();
    setupPreferences();
    autoReadCode();
    document.addEventListener("click", function (event) {
      var button = event.target.closest("[data-listen]");
      if (!button) { return; }
      if (activeButton === button) { stop(); return; }
      var target = targetOf(button);
      if (target) { speak(textOf(target), button); }
    });
    // Ao cambiar de pantalla non debe seguir falando
    window.addEventListener("pagehide", stop);
    document.body.addEventListener("htmx:afterSwap", showBars);
  }

  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); }
  else { init(); }
})();
