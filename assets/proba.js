/* G-BET : estimation de la probabilite de victoire en direct, pour TOUS les sports hors football (25/10/2026).
   Calculee dans le navigateur a partir de ce que le site connait deja : score, temps restant, situation de jeu. Aucune donnee externe.
   Ce n'est PAS une cote ni un pronostic du bot : c'est une estimation statistique du score actuel (marge / ecart-type du temps restant). */
(function (root) {
  "use strict";
  function erf(x) { var s = x < 0 ? -1 : 1; x = Math.abs(x); var t = 1 / (1 + .3275911 * x);
    return s * (1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - .284496736) * t + .254829592) * t * Math.exp(-x * x)); }
  function phi(x) { return .5 * (1 + erf(x / Math.SQRT2)); }
  function borne(p) { return Math.min(.995, Math.max(.005, p)); }
  function sec(clk) { if (!clk && clk !== 0) return null; var p = String(clk).split(":").map(Number); return p.length === 2 && isFinite(p[0] + p[1]) ? p[0] * 60 + p[1] : null; }

  /* sport -> {n periodes, duree d'une periode en s, ecart-type de la marge finale, avantage du domicile en points de marge} */
  var EQUIPE = {
    nfl: {n: 4, len: 900, sd: 13.5, adv: 1.8, mot: "point"},
    nba: {n: 4, len: 720, sd: 12.5, adv: 2.2, mot: "point"}, nbam: {n: 4, len: 720, sd: 12.5, adv: 2.2, mot: "point"},
    wnba: {n: 4, len: 600, sd: 11.5, adv: 1.8, mot: "point"},
    euroleague: {n: 4, len: 600, sd: 10.5, adv: 2.5, mot: "point"}, nbl: {n: 4, len: 600, sd: 11, adv: 2.5, mot: "point"}, grebl: {n: 4, len: 600, sd: 10.5, adv: 2.5, mot: "point"},
    kbl: {n: 4, len: 600, sd: 10.5, adv: 2.5, mot: "point"},
    hockey: {n: 3, len: 1200, sd: 2.25, adv: .15, mot: "but"}, nhl: {n: 3, len: 1200, sd: 2.25, adv: .15, mot: "but"}
  };
  ["hfra", "hpol", "hrom", "hromf", "hden", "hesp"].forEach(function (k) { EQUIPE[k] = {n: 2, len: 1800, sd: 5.4, adv: 1.1, mot: "but"}; });
  var BASE = {baseball: 1, mlb: 1, npb: 1, kbo: 1};

  /* fraction de match RESTANTE (1 = rien joue, 0 = fini) */
  function restant(cfg, sc, fsd) {
    var total = cfg.n * cfg.len, s = fsd && sec(fsd.clk), per = fsd && Number(fsd.per);
    if (s !== null && s !== undefined && per) return Math.max(0, Math.min(1, ((cfg.n - per) * cfg.len + s) / total));
    var st = String((sc && sc.status_long) || ""), m = st.match(/(\d)/), rang = {First: 1, Second: 2, Third: 3, Fourth: 4}[(st.match(/(First|Second|Third|Fourth)/) || [])[1]] || (m ? Number(m[1]) : 0);
    if (rang) return Math.max(0, Math.min(1, (cfg.n - rang + .5) / cfg.n));
    return null;
  }

  function equipe(sport, sc, fsd) {
    var cfg = EQUIPE[sport], f = restant(cfg, sc, fsd);
    if (f === null) return null;
    var diff = (Number(sc.home_score) || 0) - (Number(sc.away_score) || 0);
    if (sc.finished || f <= 0) return diff > 0 ? 1 : diff < 0 ? 0 : .5;
    var f2 = Math.max(f, .015);
    return phi((diff + cfg.adv * f2) / (cfg.sd * Math.sqrt(f2)));
  }

  function baseball(sc, fsd) {
    var st = String((sc && sc.status_long) || ""), m = st.match(/(\d+)/);
    if (!m) return null;
    var diff = (Number(sc.home_score) || 0) - (Number(sc.away_score) || 0);
    if (sc.finished) return diff > 0 ? 1 : diff < 0 ? 0 : .5;
    var inn = Number(m[1]), haut = /^Top/i.test(st), o = fsd && fsd.bb && Number(fsd.bb.o) || 0;
    /* retraits restants dans le match (27 par camp) */
    var restHaut = haut ? (27 - ((inn - 1) * 3 + o)) : (27 - (inn * 3)), restBas = haut ? (27 - ((inn - 1) * 3)) : (27 - ((inn - 1) * 3 + o));
    var f = Math.max(.02, (Math.max(0, restHaut) + Math.max(0, restBas)) / 54);
    return phi((diff + .25 * f) / (4.4 * Math.sqrt(f)));
  }

  /* tennis : chaine de Markov point -> jeu -> set -> match (meilleur des 3). Probabilite de gagner un point au service : ATP 64,5 %, WTA 56 % */
  function course(p, a, b, cible) {            /* premier a `cible` points avec 2 d'ecart (jeu : cible 4 ; jeu decisif : cible 7) */
    var memo = {};
    function f(x, y) {
      if (x >= cible && x - y >= 2) return 1; if (y >= cible && y - x >= 2) return 0;
      if (x >= cible - 1 && y >= cible - 1) { var d = p * p / (p * p + (1 - p) * (1 - p)); return x === y ? d : x > y ? p + (1 - p) * d : p * d; }
      var k = x + "," + y; if (memo[k] !== undefined) return memo[k]; return (memo[k] = p * f(x + 1, y) + (1 - p) * f(x, y + 1));
    }
    return f(a, b);
  }
  function tennis(sc, fsd, sport, fid) {
    var sets = String(sc.events_json || "").split(",").map(function (x) { return x.trim().match(/^(\d+)\s*-\s*(\d+)$/); }).filter(Boolean).map(function (m) { return [Number(m[1]), Number(m[2])]; });
    var s1 = Number(sc.home_score) || 0, s2 = Number(sc.away_score) || 0;
    if (sc.finished) return s1 > s2 ? 1 : s1 < s2 ? 0 : .5;
    if (!sets.length) return null;
    var pa = /wta/i.test(String(fid || "")) ? .56 : .645, pb = pa;            /* j1 (home) et j2 (away) : meme niveau de service par defaut */
    var q = (pa + (1 - pb)) / 2;                                               /* point gagne par j1 dans un jeu decisif (moyenne service / retour) */
    var memo = {};
    function jeu(srv, x, y) { return srv === 1 ? course(pa, x, y, 4) : 1 - course(pb, y, x, 4); }   /* P(j1 gagne le jeu) */
    function set(a, b, srv, dep) {                                             /* P(j1 gagne le set) : jeux a-b, srv sert le jeu en cours, dep = points deja joues dans ce jeu */
      var k = a + "," + b + "," + srv + (dep ? "," + dep[0] + "," + dep[1] : ""); if (memo[k] !== undefined) return memo[k];
      var v;
      if ((a >= 6 && a - b >= 2) || a === 7) v = 1;
      else if ((b >= 6 && b - a >= 2) || b === 7) v = 0;
      else if (a === 6 && b === 6) v = course(q, dep ? dep[0] : 0, dep ? dep[1] : 0, 7);
      else { var pj = jeu(srv, dep ? dep[0] : 0, dep ? dep[1] : 0); v = pj * set(a + 1, b, 3 - srv, null) + (1 - pj) * set(a, b + 1, 3 - srv, null); }
      return (memo[k] = v);
    }
    var g = sets[sets.length - 1], srv = fsd && fsd.srv === "a" ? 2 : 1;
    var pts = fsd && fsd.pts ? String(fsd.pts).split(":").map(function (v) { return {"0": 0, "15": 1, "30": 2, "40": 3, "Av": 4}[String(v).trim()]; }) : null;
    var dep = pts && pts.length === 2 && pts[0] !== undefined && pts[1] !== undefined ? pts : [0, 0];
    if (dep[0] === 4 || dep[1] === 4) { var m = Math.min(dep[0], dep[1]); dep = dep[0] === 4 ? [3 + (m === 3 ? 1 : 0), 3] : [3, 3 + (m === 3 ? 1 : 0)]; dep = dep[0] > dep[1] ? [4, 3] : [3, 4]; }
    var pc = set(g[0], g[1], srv, dep);                                        /* le set en cours */
    var pf = (set(0, 0, 1, null) + set(0, 0, 2, null)) / 2;                    /* un set tout neuf */
    if (s1 === 1 && s2 === 1) return borne(pc);
    if (s1 === 1 && s2 === 0) return borne(pc + (1 - pc) * pf);
    if (s1 === 0 && s2 === 1) return borne(pc * pf);
    return borne(pc * (pf + (1 - pf) * pf) + (1 - pc) * pf * pf);
  }

  function golf(sc, fsd) {
    var g = fsd && fsd.g; if (!g || g.length !== 2) return null;
    var th = Math.min(18, Math.max(Number(g[0].thru) || 0, Number(g[1].thru) || 0)), rest = 18 - th;
    var d = (Number(sc.away_score) || 0) - (Number(sc.home_score) || 0);                 /* le plus bas gagne : j1 devant si d > 0 */
    if (sc.finished || rest <= 0) return d > 0 ? 1 : d < 0 ? 0 : .5;
    return phi((d - .15) / (Math.sqrt(2) * .95 * Math.sqrt(rest) + .3));
  }

  /* point d'entree : renvoie {h: probabilite de victoire du premier nom (domicile / joueur 1), modele} ou null */
  function live(sport, sc, fsd, league, fid) {
    if (!sc || sport === "football") return null;
    var p = null, modele = "";
    if (EQUIPE[sport]) { p = equipe(sport, sc, fsd); modele = "score et temps restant"; }
    else if (BASE[sport]) { p = baseball(sc, fsd); modele = "score et manches restantes"; }
    else if (sport === "tennis") { p = tennis(sc, fsd, sport, fid); modele = "score, jeux et service"; }
    else if (sport === "golf") { p = golf(sc, fsd); modele = "écart et trous restants"; }
    return p === null || p === undefined || !isFinite(p) ? null : {h: Math.round(borne(p) * 1000) / 1000, modele: modele};
  }
  var API = {live: live, _phi: phi, _equipe: equipe, _tennis: tennis};
  if (typeof module !== "undefined" && module.exports) module.exports = API; else root.GB_PROBA = API;
})(typeof window !== "undefined" ? window : this);
