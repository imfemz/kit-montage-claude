// Le verre : mes cartes en glassmorphisme au glow bleu, qui montent DROIT (aucune rotation).
// Tout vient d'une de mes comps After Effects, échantillonnée image par image à 29,97 i/s puis validée sur mes vidéos :
// - carte 821,5 × 475,7 px (en 1080p), rayon 9,19 % de la largeur ; fond = un dégradé noir → blanc à 32 % posé sur un flou
//   d'arrière-plan (22 px, saturation 1,3, luminosité 1,08) ; brume bleue du haut vers le bas ; reflet bleu en diagonale (light sweep) ;
//   arête du haut bleue qui suit les coins ; halo froid fort au-dessus de la carte, doux tout autour (deep glow) ; scintillement ±3 % ;
//   grain très léger ;
// - entrée : la carte monte de 119 px (courbe échantillonnée ci-dessous) et apparaît en 0,23 s ; l'avatar suit (+45 px, 0,167 s après) ;
//   chaque mot monte de 90 px sur un ressort exp(−8,14 t)·cos(2π·1,482 t) et apparaît en 0,15 s, un mot toutes les 0,101 s ;
// - sortie : la carte descend de 112 px en accélérant et s'efface ; aucune rotation, ni à l'entrée ni après.
// Deux pièges du navigateur, réglés ici :
// - un PARENT en opacité < 1 coupe le flou d'arrière-plan : l'opacité se pose sur chaque couche de la carte, jamais sur la carte ;
// - un mode de fusion « plus-lighter » ne voit pas l'image derrière une carte isolée dans sa couche : les lumières sont des couleurs
//   semi-transparentes équivalentes (exactes sur du noir).
// UI.verre(conteneur, o) et UI.etiquette(conteneur, o) rendent jouer(t), t en secondes. Scène de travail : 1920 × 1080 px.
// UI.habiller(boite, o) pose le même verre sur une boîte à toi (carte, pilule, fenêtre), avec un light sweep en option.
// Besoin de motion.js chargé avant. Le verre a besoin d'une image DERRIÈRE lui (ta vidéo) : o.decor pose un fond sombre uni pour la démo.
(function (racine) {
  const M = racine.MOTION || (typeof require !== "undefined" ? require("../motion/motion.js") : null);
  const UI = racine.UI || {};
  const TAU = Math.PI * 2, FPS = 30000 / 1001;
  const borne = (x, a, b) => Math.max(a, Math.min(b, x));
  const f2 = x => Math.round(x * 100) / 100, f4 = x => Math.round(x * 10000) / 10000;
  const POLICE = '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif';

  const V = {
    W: 821.5,
    // échantillons de la comp, une valeur par image (29,97 i/s), interpolés entre deux images
    entY: [119, 111.71, 96.61, 77.33, 62.06, 50.83, 42.2, 35.33, 29.69, 24.96, 20.97, 17.55, 14.62, 12.09, 9.92, 8.04, 6.42, 5.03, 3.85, 2.86, 2.04, 1.38, 0.86, 0.47, 0.21, 0.05, 0],
    entO: [0, 0.1429, 0.2857, 0.4286, 0.5714, 0.7143, 0.8571, 1],
    sorY: [0, 0.02, 0.1, 0.23, 0.41, 0.65, 0.95, 1.31, 1.73, 2.23, 2.78, 3.42, 4.13, 4.92, 5.8, 6.76, 7.82, 8.97, 10.23, 11.6, 13.1, 14.72, 16.48, 18.38, 20.45, 22.7, 25.14, 27.8, 30.68, 33.84, 37.28, 41.08, 45.3, 50, 55.29, 61.36, 68.47, 77.11, 88.55, 112, 112],
    sorO: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0.9375, 0.875, 0.7583, 0.65, 0.55, 0.4583, 0.375, 0.3, 0.2333, 0.175, 0.125, 0.0833, 0.05, 0.025, 0.0083, 0, 0],
    avY: [45, 39.64, 28.85, 20.82, 15.62, 11.93, 9.15, 7, 5.29, 3.93, 2.85, 1.99, 1.32, 0.8, 0.43, 0.18, 0.04, 0], avO: [0, 0.2, 0.4, 0.6, 0.8, 1], avT: 0.167,
    rise: 90, dec: 8.14, fr: 1.482, pas: 0.101, fondu: 0.15, tTitre: 0.234, tCorps: 0.3, lecture: 1.5, pose: 0.479,
    rampe: [[475.5, 100.85], [612.5, 1361.85]], reflet: [[36.5, 648.5], [1144.5, 8.5]],
    verre: 0.32, flou: "blur(22px) saturate(1.3) brightness(1.08)", flicker: 0.03,
  };
  V.sorDur = (V.sorY.length - 1) / FPS;

  const el = (tag, style, parent, txt) => {
    const e = document.createElement(tag);
    if (style) e.style.cssText = style;
    if (txt != null) e.textContent = txt;
    if (parent) parent.appendChild(e);
    return e;
  };
  const table = (T, f) => {
    if (f <= 0) return T[0];
    if (f >= T.length - 1) return T[T.length - 1];
    const i = Math.floor(f), u = f - i; return T[i] + (T[i + 1] - T[i]) * u;
  };

  // état de la carte à l'instant t (vie de t0 à t1) : { y, op } ou null ; k = échelle (largeur / 821,5) ; coupe = sortie sur une coupe franche
  function etat(t, t0, t1, coupe, k) {
    if (t < t0 || t >= t1) return null;
    const f = (t - t0) * FPS;
    let y = table(V.entY, f) * k, op = table(V.entO, f);
    if (!coupe) { const g = (t - (t1 - V.sorDur)) * FPS; if (g > 0) { y += table(V.sorY, g) * k; op *= table(V.sorO, g); } }
    return { y, op };
  }
  // les mots : ML Rise + ML Fade, un mot toutes les 0,101 s ; f = compression du temps (≥ 1) pour laisser lire
  function mots(ws, v, k, f) {
    ws.forEach((w, i) => {
      const tl = v * (f || 1) - i * V.pas;
      const r = tl < 0 ? 1 : Math.exp(-V.dec * tl) * Math.cos(V.fr * TAU * tl), o = tl < 0 ? 0 : Math.min(1, tl / V.fondu);
      w.style.transform = `translateY(${f2(V.rise * k * r)}px)`; w.style.opacity = f4(o);
    });
  }
  function decouper(e) {
    const out = [];
    const walk = n => { for (const c of [...n.childNodes]) {
      if (c.nodeType === 3) {
        const fr = document.createDocumentFragment();
        for (const p of c.textContent.split(/(\s+)/)) { if (!p) continue; if (/^\s+$/.test(p)) fr.append(p); else { const s = el("span", "display:inline-block"); s.textContent = p; fr.append(s); out.push(s); } }
        c.replaceWith(fr);
      } else if (c.nodeType === 1) walk(c);
    } };
    walk(e); return out;
  }
  // dégradé CSS qui reproduit un dégradé de la comp (de p1 à p2, coordonnées de la carte de 821,5 px × k) sur une boîte W × H
  function degrade(W, H, p1, p2, k, arrets) {
    const dx = (p2[0] - p1[0]) * k, dy = (p2[1] - p1[1]) * k, th = Math.atan2(dx, -dy), u = [Math.sin(th), -Math.cos(th)];
    const L = Math.abs(W * u[0]) + Math.abs(H * u[1]), s = q => ((q[0] - W / 2) * u[0] + (q[1] - H / 2) * u[1]) / L + 0.5;
    return `linear-gradient(${f2(th * 180 / Math.PI)}deg, ${arrets.map(([f, c]) => `${c} ${f2(100 * s([p1[0] * k + f * dx, p1[1] * k + f * dy]))}%`).join(", ")})`;
  }
  // tuile de grain : bruit gaussien à graine fixe (jamais Math.random : deux rendus donnent la même image)
  let BRUIT = null;
  function bruit() {
    if (BRUIT) return BRUIT;
    const cv = document.createElement("canvas"); cv.width = cv.height = 192; const g = cv.getContext("2d"), im = g.createImageData(192, 192);
    let s = 1234567; const r = () => ((s = (s * 1103515245 + 12345) >>> 0) / 4294967296);
    for (let i = 0; i < im.data.length; i += 4) { const n = Math.sqrt(-2 * Math.log(r() + 1e-9)) * Math.cos(TAU * r()), v = n > 0 ? 255 : 0; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = borne(Math.abs(n) * 4, 0, 255); }
    g.putImageData(im, 0, 0); return (BRUIT = cv.toDataURL());
  }
  // les couches du verre, sous le contenu : halo, couronne de lumière au-dessus, flou + dégradé, brume, reflet, arête, grain
  function couches(parent, avant) {
    const abs = "position:absolute;left:0;top:0;pointer-events:none";
    const L = {}; for (const n of ["halo", "couronne", "bd", "brume", "reflet", "arete", "grain"]) L[n] = el("div", abs, null);
    for (const n of ["halo", "couronne", "bd", "brume", "reflet", "arete", "grain"]) parent.insertBefore(L[n], avant || null);
    L.lueur = el("div", "position:absolute", L.couronne);
    L.lum = [L.halo, L.couronne, L.brume, L.reflet, L.arete];    // les lumières (le scintillement les module)
    L.flick = 1;
    L.bd.style.backdropFilter = L.bd.style.webkitBackdropFilter = V.flou;
    L.grain.style.backgroundImage = `url(${bruit()})`; L.grain.style.backgroundRepeat = "repeat"; L.grain.style.backgroundSize = "96px 96px";
    return L;
  }
  // k = échelle du dessin (dégradé, reflet) ; kl = échelle des lumières (arête, halo, barres), k par défaut
  function forme(L, W, H, k, rayon, kl) {
    kl = kl ?? k;
    const cle = `${W}|${H}|${rayon}|${kl}`;
    if (L.cle === cle) return; L.cle = cle;
    L.bd.style.background = degrade(W, H, V.rampe[0], V.rampe[1], k, [[0, `rgba(0,0,0,${V.verre})`], [1, `rgba(255,255,255,${V.verre})`]]);
    L.brume.style.background = "linear-gradient(180deg, rgba(0,93,255,0.086) 0%, rgba(0,128,255,0.024) 45%, rgba(0,0,0,0) 100%)";
    L.reflet.style.background = degrade(W, H, V.reflet[0], V.reflet[1], k,
      [[0, "rgba(0,0,0,0)"], [0.06, "rgba(32,128,255,0.063)"], [0.25, "rgba(44,133,255,0.180)"], [0.5, "rgba(46,135,255,0.392)"], [0.75, "rgba(44,133,255,0.180)"], [1, "rgba(0,0,0,0)"]]);
    // l'arête : la lumière du haut, À L'INTÉRIEUR de la forme (ombre intérieure qui suit les coins), douce, jamais un trait
    const m = (v, min) => f2(Math.max(v * kl, min));
    L.arete.style.boxShadow = `inset 0 ${m(9, 4)}px ${m(22, 10)}px -${m(7, 3)}px rgba(0,110,255,0.5), inset 0 ${m(2.5, 1.5)}px ${m(7, 4)}px -${m(2, 1)}px rgba(70,155,255,0.4)`;
    for (const e of [L.bd, L.brume, L.reflet, L.arete, L.grain, L.halo]) Object.assign(e.style, { width: f2(W) + "px", height: f2(H) + "px", borderRadius: f2(rayon) + "px" });
    L.halo.style.boxShadow = `0 0 ${f2(12 * kl)}px rgba(30,45,75,.55), 0 0 ${f2(110 * kl)}px rgba(25,40,70,.75)`;
    // la couronne : le glow bleu AU-DESSUS de la carte. Ombres portées de la forme elle-même (elles suivent les coins arrondis),
    // poussées vers le haut, puis effacées vers le bas par un masque : fort au-dessus, rien sous la mi-hauteur.
    const ombres = [[m(2, 1), m(14, 8), "rgba(0,90,255,0.55)"], [m(6, 3), m(60, 18), "rgba(0,80,255,0.45)"], [m(16, 6), m(220, 34), "rgba(0,71,255,0.4)"]];
    const P = Math.ceil(ombres[2][0] + ombres[2][1] + 10), masque = `linear-gradient(180deg, #000 0, #000 ${f2(P + 0.1 * H)}px, transparent ${f2(P + 0.55 * H)}px)`;
    Object.assign(L.couronne.style, { left: -P + "px", top: -P + "px", width: f2(W + 2 * P) + "px", height: f2(H + 2 * P) + "px", maskImage: masque, webkitMaskImage: masque });
    Object.assign(L.lueur.style, { left: P + "px", top: P + "px", width: f2(W) + "px", height: f2(H) + "px", borderRadius: f2(rayon) + "px",
      boxShadow: ombres.map(([y, b, c]) => `0 -${y}px ${b}px ${c}`).join(", ") });
  }
  // scintillement (±3 % à 30 Hz) et grain qui bouge, tirés du numéro d'image : déterministes
  function vie(L, image) {
    const h = Math.sin(image * 12.9898 + 78.233) * 43758.5453;
    L.flick = 1 + V.flicker * ((h - Math.floor(h)) * 2 - 1);
    L.grain.style.backgroundPosition = `${(image * 37) % 96}px ${(image * 75) % 96}px`;
  }
  // l'opacité se pose couche par couche (une carte en opacité < 1 perdrait son flou d'arrière-plan)
  function opacite(parent, op, L) {
    for (const e of parent.children) e.style.opacity = f4(op * (L.lum.includes(e) ? L.flick : 1));
  }
  // pour la démo, un fond sombre uni et rien d'autre (dans ta vidéo, c'est ta face cam qui est derrière)
  function decor(sc) {
    el("div", "position:absolute;inset:0;background:radial-gradient(circle at 50% 90%, #272727 0, #000 120%)", sc);
  }
  const scene = c => el("div", `position:absolute;left:0;top:0;width:1920px;height:1080px;overflow:hidden;font-family:${POLICE};color:#fff`, c);

  // 1. LA CARTE EN VERRE (un commentaire, une citation, un avis) : avatar blanc à liseré bleu, pseudo, date, texte blanc.
  // o.x, o.y = coin haut gauche dans l'image 1080p ; o.largeur (821,5 par défaut) ; o.t0 / o.t1 = arrivée / fin de vie (s) ;
  // o.coupe = true si la carte disparaît sur une coupe franche (pas d'animation de sortie).
  UI.verre = (conteneur, o) => {
    o = Object.assign({ pseudo: "@un_abonné", date: "il y a 2 jours", texte: "Le rythme, les coupures, le son… on dirait vraiment un monteur.",
      initiale: null, x: 1000, y: 330, largeur: V.W, t0: 0.3, t1: 5.6, coupe: false, decor: false }, o);
    const sc = scene(conteneur), k = o.largeur / V.W;
    if (o.decor) decor(sc);
    const carte = el("div", `position:absolute;left:${o.x}px;top:${o.y}px;width:${f2(o.largeur)}px;display:flex;align-items:flex-start;gap:${f2(24 * k)}px;padding:${f2(36 * k)}px ${f2(36 * k)}px ${f2(36 * k)}px ${f2(30 * k)}px;box-sizing:border-box`, sc);
    const av = el("div", `position:relative;z-index:1;flex:none;width:${f2(96 * k)}px;height:${f2(96 * k)}px;border-radius:50%;background:#fff;color:#1c1c1e;display:grid;place-items:center;font:600 ${f2(48 * k)}px ${POLICE};box-shadow:0 0 0 ${f2(3 * k)}px #008bff`, carte, o.initiale || o.pseudo.replace(/^@/, "")[0].toUpperCase());
    // les mots montent de 90 px : masqués sous le bloc de texte, jamais hors de la carte
    const corps = el("div", `position:relative;z-index:1;flex:1;min-width:0;clip-path:inset(-${f2(30 * k)}px -${f2(60 * k)}px 0 -${f2(60 * k)}px)`, carte);
    const tete = el("div", "white-space:nowrap", corps);
    el("span", `font:700 ${f2(38 * k)}px ${POLICE};letter-spacing:-0.01em`, tete, o.pseudo);
    tete.append(" ");
    el("span", `font:500 ${f2(22 * k)}px ${POLICE};color:rgba(255,255,255,.55)`, tete, o.date);
    const tx = el("div", `margin-top:${f2(10 * k)}px;font:500 ${f2(32 * k)}px/1.22 ${POLICE}`, corps, o.texte);
    const L = couches(carte, av), wt = decouper(tete), wb = decouper(tx);
    const fin = o.coupe ? o.t1 : o.t1 - V.sorDur;
    const f = M.compression(wb.length, o.t0 + V.tCorps, fin, { decalage: V.pas, pose: V.pose, lecture: V.lecture });
    return t => {
      forme(L, carte.offsetWidth || o.largeur, carte.offsetHeight || 300 * k, k, 0.0919 * o.largeur);
      const s = etat(t, o.t0, o.t1, o.coupe, k);
      if (!s) { opacite(carte, 0, L); return; }
      carte.style.transform = `translateY(${f2(s.y)}px)`;                       // DROIT : jamais de rotation
      vie(L, Math.round(t * FPS)); opacite(carte, s.op, L);
      const v = t - o.t0, a = { y: table(V.avY, (v - V.avT) * FPS) * k, op: table(V.avO, (v - V.avT) * FPS) };
      av.style.opacity = f4(s.op * a.op); av.style.transform = `translateY(${f2(a.y)}px)`;
      mots(wt, v - V.tTitre, k, f); mots(wb, v - V.tCorps, k, f);
    };
  };

  // 2. L'ÉTIQUETTE DE 2 MOTS, en verre : elle apparaît SUR le mot dit (0 à +0,3 s), naît à 65 % de sa taille depuis le côté
  // de ta tête et se pose sans rebond (courbe mesurée image par image sur un YouTuber, MOTION.etiquette). o.cote = côté de ta tête ("gauche" / "droite").
  UI.etiquette = (conteneur, o) => {
    o = Object.assign({ texte: "Le rythme", x: 1080, y: 300, hauteur: 92, t0: 0.4, t1: 3.6, cote: "gauche", decor: false }, o);
    const sc = scene(conteneur), k = o.hauteur / 92;
    if (o.decor) decor(sc);
    const pil = el("div", `position:absolute;left:${o.x}px;top:${o.y}px;height:${o.hauteur}px;display:flex;align-items:center;padding:0 ${f2(40 * k)}px;box-sizing:border-box;transform-origin:${o.cote === "gauche" ? "left" : "right"} center`, sc);
    const mot = el("div", `position:relative;z-index:1;font:700 ${f2(42 * k)}px ${POLICE};letter-spacing:-0.015em;white-space:nowrap`, pil, o.texte);
    const L = couches(pil, mot);
    return t => {
      forme(L, pil.offsetWidth || 300 * k, o.hauteur, k * 0.6, o.hauteur / 2);
      const e = M.etiquette(t - o.t0);
      if (!e || t >= o.t1) { opacite(pil, 0, L); return; }
      const sortie = M.COURBES.ekin.f((t - (o.t1 - 0.3)) / 0.3);             // sortie : se resserre un peu et s'efface en 0,3 s
      pil.style.transform = `scale(${f4(e.echelle * (1 - 0.08 * sortie))})`;
      vie(L, Math.round(t * FPS)); opacite(pil, e.opacite * (1 - sortie), L);
    };
  };

  // 3. HABILLER UNE BOÎTE À TOI : une carte, une pilule, une fenêtre prend le même verre, son contenu passe devant.
  // La boîte doit être positionnée (absolute ou relative). Rend vivre(t, op, balayage), à appeler à chaque image :
  // t en secondes (scintillement, grain), op = opacité, balayage = 0 → 1 fait traverser un light sweep bleu (null : aucun).
  // Le halo et l'arête débordent de la boîte : un parent en overflow: hidden trop serré couperait le glow. Dans un petit cadre,
  // o.k (échelle des lumières, largeur / 821,5 par défaut) les resserre pour qu'elles s'éteignent avant son bord ; le dégradé ne change pas.
  // Sur une page web, la couronne déborde aussi de la page : pose overflow-x: clip sur la section qui contient la boîte.
  UI.habiller = (boite, o) => {
    o = Object.assign({ rayon: null, k: null }, o);
    for (const c of boite.children) {
      const pos = c.isConnected ? getComputedStyle(c).position : c.style.position;
      if (!pos || pos === "static") { c.style.position = "relative"; c.style.zIndex = 1; }
    }
    const L = couches(boite, boite.firstChild);
    // le light sweep : une bande bleue qui traverse toute la boîte en biais, contenu compris (comme un CC Light Sweep), rognée à sa forme
    const fen = el("div", "position:absolute;left:0;top:0;z-index:2;overflow:hidden;pointer-events:none;visibility:hidden", boite);
    const bande = el("div", "position:absolute;left:0;top:-50%;height:200%;width:40%;background:linear-gradient(90deg, rgba(0,105,255,0), rgba(0,105,255,0.22) 30%, rgba(120,185,255,0.5) 50%, rgba(0,105,255,0.22) 70%, rgba(0,105,255,0))", fen);
    L.lum.push(fen);
    return (t, op, balayage) => {
      const W = boite.offsetWidth, H = boite.offsetHeight, r = o.rayon ?? 0.0919 * W;
      forme(L, W, H, W / V.W, r, o.k);
      Object.assign(fen.style, { width: f2(W) + "px", height: f2(H) + "px", borderRadius: f2(r) + "px" });
      const u = balayage == null ? 0 : M.COURBES.ekin.f(balayage);
      fen.style.visibility = u > 0 && u < 1 ? "visible" : "hidden";
      bande.style.transform = `translateX(${f2((u * 1.8 - 0.6) * W)}px) rotate(20deg)`;
      vie(L, Math.round(t * FPS)); opacite(boite, op ?? 1, L);
    };
  };

  UI.VERRE = [
    ["verre", "Carte en verre", "Un commentaire, une citation : verre au glow bleu, montée droite, texte mot à mot.", { x: 1000, y: 330, decor: true }],
    ["etiquette", "Étiquette de 2 mots", "Sur le mot dit : naît à 65 %, se pose sans rebond.", { x: 1080, y: 300, decor: true }],
  ];
  UI.VERRE_REGLAGES = V;

  if (typeof module !== "undefined" && module.exports) module.exports = UI;
  else racine.UI = UI;
})(typeof window !== "undefined" ? window : globalThis);
