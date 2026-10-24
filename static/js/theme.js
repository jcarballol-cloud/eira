/* SPDX-License-Identifier: EUPL-1.2 */
/* v4.1: tema da app. Cárgase síncrono no <head> (pequeno) para que non haxa escintileo:
   data-theme="dark|light" (botón «Día / Noite» da demo, gardado na sesión) ou, sen valor,
   a preferencia do sistema. O CSS usa só a clase .theme-dark. */
(function () {
  var root = document.documentElement;
  var media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  function apply() {
    var chosen = root.getAttribute("data-theme");
    root.classList.toggle("theme-dark", chosen === "dark" || (!chosen && !!media && media.matches));
  }
  apply();
  if (media && media.addEventListener) media.addEventListener("change", apply);
  window.eiraApplyTheme = apply;
})();
