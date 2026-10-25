/* G-BET : contenu rendu flou des qu'on quitte la page ou qu'on tente une capture / une impression (22/10/2026, demande
   explicite : pas de message, juste du flou). Limites reelles d'un site web : une capture faite par le systeme (telephone,
   outil de capture deja ouvert, photo de l'ecran) ne peut pas etre bloquee ; on agit sur tout ce que le navigateur
   laisse voir : perte du focus (outil de capture, changement d'application), page masquee (selecteur d'applications),
   touches de capture, impression, copie, clic droit, glisser-deposer. Aucun texte n'est affiche. */
(function () {
"use strict";
var racine = document.documentElement;
var minuteur = null, verrou = 0;

var st = document.createElement("style");
st.textContent =
  "html.flou body>*:not(script):not(style){filter:blur(34px)!important;transition:none!important;pointer-events:none!important}" +
  "html.flou body>*:not(script):not(style) *{animation-play-state:paused!important}" +
  "body{-webkit-touch-callout:none;-webkit-user-select:none;user-select:none}" +
  "input,textarea,[contenteditable=true]{-webkit-user-select:text;user-select:text}" +
  "img{-webkit-user-drag:none;user-drag:none}" +
  "@media print{html{display:none!important}}";
(document.head || racine).appendChild(st);

function flouter() { clearTimeout(minuteur); racine.classList.add("flou"); }
function degager(delai) {
  clearTimeout(minuteur);
  minuteur = setTimeout(function () {
    if (Date.now() < verrou) return degager(300);
    if (document.hidden) return;                  // reste flou tant que la page est masquee
    racine.classList.remove("flou");
  }, delai === undefined ? 120 : delai);
}
function bloquer(ms) { verrou = Date.now() + ms; flouter(); degager(ms + 50); }

window.addEventListener("blur", flouter);
window.addEventListener("focus", function () { degager(); });
window.addEventListener("pagehide", flouter);
window.addEventListener("pageshow", function () { degager(); });
document.addEventListener("visibilitychange", function () { if (document.hidden) flouter(); else degager(); });
/* un geste sur la page prouve qu'elle est au premier plan : on ne reste jamais flou par erreur (webviews, focus inconnu) */
["pointerdown", "touchstart", "keydown"].forEach(function (n) {
  window.addEventListener(n, function () { if (!document.hidden && Date.now() >= verrou) degager(60); }, true);
});
window.addEventListener("beforeprint", function () { bloquer(4000); });
window.addEventListener("afterprint", function () { degager(); });

function effacerPressePapier() {
  try { if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(" ").catch(function () {}); } catch (e) {}
}
function toucheCapture(e) {
  var k = e.key, c = (e.code || "");
  var capture = k === "PrintScreen" || c === "PrintScreen" || k === "Snapshot" ||
    ((e.metaKey || e.ctrlKey) && e.shiftKey && /^(s|S|3|4|5|6)$/.test(k)) ||               // Win+Maj+S, Cmd+Maj+3/4/5/6
    ((e.metaKey || e.ctrlKey) && e.shiftKey && /^(Digit|Numpad)[3-6]$/.test(c));
  if (capture) { bloquer(2500); effacerPressePapier(); return; }
  if ((e.ctrlKey || e.metaKey) && /^(p|s|P|S)$/.test(k) && !e.shiftKey) { e.preventDefault(); bloquer(1500); }
}
window.addEventListener("keydown", toucheCapture, true);
window.addEventListener("keyup", toucheCapture, true);       // Windows n'envoie que le keyup pour ImprEcran

function champ(t) { return t && t.closest && t.closest("input,textarea,[contenteditable=true]"); }
document.addEventListener("contextmenu", function (e) { if (!champ(e.target)) e.preventDefault(); });
document.addEventListener("selectstart", function (e) { if (!champ(e.target)) e.preventDefault(); });
document.addEventListener("dragstart", function (e) { e.preventDefault(); });
document.addEventListener("copy", function (e) { if (!champ(e.target)) e.preventDefault(); });
document.addEventListener("cut", function (e) { if (!champ(e.target)) e.preventDefault(); });

if (document.hidden) flouter();
})();
