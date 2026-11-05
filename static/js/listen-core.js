// SPDX-License-Identifier: EUPL-1.2
// v1.5 · A: lóxica pura do botón «Escoitar», sen tocar o DOM nin a voz, para poder probala.
// Exponse como window.EiraListenCore no navegador e como módulo en Node (tests unitarios).
(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) { module.exports = api; }
  else { root.EiraListenCore = api; }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var RATES = { normal: 1, slow: 0.75 };

  function byLang(voices, prefix) {
    var wanted = prefix.toLowerCase();
    var exact = voices.filter(function (v) {
      return (v.lang || "").toLowerCase().replace("_", "-") === wanted;
    });
    if (exact.length) { return exact[0]; }
    var short = wanted.split("-")[0];
    return voices.filter(function (v) {
      var lang = (v.lang || "").toLowerCase().replace("_", "-");
      return lang === short || lang.indexOf(short + "-") === 0;
    })[0] || null;
  }

  // Escolle a voz: castelán se a interface está en castelán; se non, galego e, de non habelo,
  // castelán avisando (fallback). Sen ningunha das dúas, a voz por defecto co idioma es-ES.
  function pickVoice(voices, uiLang) {
    var list = voices || [];
    var ui = (uiLang || "gl").toLowerCase();
    if (ui.indexOf("es") === 0) {
      return { voice: byLang(list, "es-ES"), lang: "es-ES", fallback: false };
    }
    var gl = byLang(list, "gl-ES");
    if (gl) { return { voice: gl, lang: "gl-ES", fallback: false }; }
    return { voice: byLang(list, "es-ES"), lang: "es-ES", fallback: true };
  }

  function rateFor(setting) {
    return RATES[setting] || RATES.normal;
  }

  function normalize(text) {
    return (text || "").replace(/\s+/g, " ").trim();
  }

  // O código de acceso, díxito a díxito e con pausas: «1 2 3, 4 5 6».
  function spellCode(code) {
    var digits = String(code || "").replace(/\D/g, "").split("");
    var groups = [];
    for (var i = 0; i < digits.length; i += 3) {
      groups.push(digits.slice(i, i + 3).join(" "));
    }
    return groups.join(", ");
  }

  // Algúns navegadores cortan os textos longos: pártese por frases, sen pasar de `max` caracteres.
  function chunks(text, max) {
    var limit = max || 180;
    var clean = normalize(text);
    if (!clean) { return []; }
    var parts = clean.match(/[^.!?:;]+[.!?:;]*\s*/g) || [clean];
    var out = [];
    var current = "";
    parts.forEach(function (raw) {
      var part = raw.trim();
      while (part.length > limit) {
        var cut = part.lastIndexOf(" ", limit);
        if (cut <= 0) { cut = limit; }
        if (current) { out.push(current); current = ""; }
        out.push(part.slice(0, cut).trim());
        part = part.slice(cut).trim();
      }
      if (current && (current + " " + part).length > limit) {
        out.push(current);
        current = part;
      } else {
        current = current ? current + " " + part : part;
      }
    });
    if (current) { out.push(current); }
    return out;
  }

  return {
    pickVoice: pickVoice,
    rateFor: rateFor,
    normalize: normalize,
    spellCode: spellCode,
    chunks: chunks
  };
});
