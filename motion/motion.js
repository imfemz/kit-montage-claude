// Courbes de mouvement du kit : toutes les valeurs viennent de comps After Effects mesurées image par image.
// Utilisable tel quel dans une page web (window.MOTION) ou dans Node (require("./motion.js")).
// Chaque fonction prend un temps en secondes depuis le début du geste et rend des valeurs prêtes à poser.
(function (racine) {
  const TAU = Math.PI * 2;
  const borne = (x, a, b) => Math.max(a, Math.min(b, x));
  const sat = u => borne(u, 0, 1);
  const lerp = (a, b, u) => a + (b - a) * u;

  // Bézier CSS (x1, y1, x2, y2) résolue par Newton puis bissection : même résultat que cubic-bezier() du navigateur.
  function bezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const X = s => ((ax * s + bx) * s + cx) * s, Y = s => ((ay * s + by) * s + cy) * s;
    const dX = s => (3 * ax * s + 2 * bx) * s + cx;
    return u => {
      u = sat(u);
      if (u === 0 || u === 1) return u;
      let s = u;
      for (let i = 0; i < 6; i++) { const d = dX(s); if (Math.abs(d) < 1e-6) break; s -= (X(s) - u) / d; }
      if (!(s >= 0 && s <= 1) || Math.abs(X(s) - u) > 1e-5) {
        let a = 0, b = 1; s = u;
        for (let i = 0; i < 30; i++) { if (X(s) < u) a = s; else b = s; s = (a + b) / 2; }
      }
      return Y(s);
    };
  }

  // Les deux courbes « lent → rapide → lent ». Jamais de départ en flèche (expo-out, quint-out) sur une entrée.
  const COURBES = {
    ekin: { css: "cubic-bezier(0.65, 0, 0.15, 1)", f: bezier(0.65, 0, 0.15, 1) },     // entrées, déplacements, caméras d'UI
    kinetic: { css: "cubic-bezier(0.75, 0, 0.11, 1)", f: bezier(0.75, 0, 0.11, 1) },  // pas d'une roue, d'un carrousel, sortie repliée
    // Mesurées image par image sur les vidéos d'un YouTuber qui zoome bien (24/10/2026), voir zoom() et etiquette() plus bas.
    zoom: { css: "cubic-bezier(0.35, 0, 0.27, 1)", f: bezier(0.35, 0, 0.27, 1) },     // zoom face cam : 25 / 75 / 95 % du trajet à 25 / 50 / 75 % du temps
    etiquette: { css: "cubic-bezier(0.28, 0.25, 0.08, 1)", f: bezier(0.28, 0.25, 0.08, 1) }, // étiquette courte : sortie vive, fin très douce, sans rebond
  };

  // ENTRÉE d'une box (carte, fenêtre, dialogue) : elle se pose droite depuis (+60, +150) px en 0,6 s.
  // L'opacité ne part pas de 0 : 46 → 100 % en 0,12 s ; c'est le mouvement qui fait apparaître.
  // Petit objet (tuile, coche, icône) : même courbe en 0,3 s, a = 0,3.
  function entree(t, o) {
    o = Object.assign({ dx: 60, dy: 150, duree: 0.6, a: 1 }, o);
    if (t < 0) return null;
    const p = COURBES.ekin.f(t / o.duree);
    return {
      x: o.a * o.dx * (1 - p),
      y: o.a * o.dy * (1 - p),
      opacite: t < 0.12 ? lerp(0.46, 1, t / 0.12) : 1,
      rotation: 0,                                   // jamais de rotation ni de wiggle à l'entrée
    };
  }

  // SIGNATURE ELASTIC (expression de Dan Ebberts) : amplitude 0,05 · fréquence 2 · amortissement 4, active 1 s après la clé.
  // Elle rebondit à partir de la VITESSE d'arrivée : la dernière clé doit arriver lancée (arrivée courte, 0,12 à 0,28 s).
  // t = temps depuis la dernière clé, v = vitesse d'arrivée (px/s) → décalage en px à ajouter à la position posée.
  function elastic(t, v, o) {
    o = Object.assign({ amp: 0.05, freq: 2, amort: 4 }, o);
    if (t <= 0 || t >= 1) return 0;
    return v * o.amp * Math.sin(o.freq * t * TAU) / Math.exp(o.amort * t);
  }

  // Arrivée complète « courte + Elastic », comme deux clés linéaires dans After Effects : trajet d en px parcouru en `duree` s
  // à vitesse constante (d / duree), puis le rebond. Rend le décalage restant en px (0 = posé).
  function arrivee(t, d, o) {
    o = Object.assign({ duree: 0.24 }, o);
    if (t < 0) return d;
    if (t < o.duree) return d * (1 - t / o.duree);
    return -elastic(t - o.duree, d / o.duree, o);
  }

  // Impulsion amortie (pic = 1) : la réponse à un choc. P = période en s, z = amortissement.
  function impulsion(w, P, z) {
    if (w <= 0) return 0;
    const wd = TAU / P, wn = wd / Math.sqrt(1 - z * z), tp = Math.atan(wd / (z * wn)) / wd;
    return Math.exp(-z * wn * w) * Math.sin(wd * w) / (Math.exp(-z * wn * tp) * Math.sin(wd * tp));
  }

  // RÉACTION DE CHAÎNE : quand un élément se BRANCHE dans une UI (ligne, message, étape, clic validé),
  // TOUTE l'UI fait un petit rebond avec une légère rotation : 5,5 px · +1,3 % · 0,55°, période 0,58 s.
  // sens = +1 / −1, à alterner d'un branchement à l'autre. En pixels constants : une grande fenêtre bouge autant qu'une carte.
  function reaction(w, sens) {
    const k = impulsion(w, 0.58, 0.42);
    return { y: 5.5 * k, echelle: 1 + 0.013 * k, rotation: 0.55 * (sens || 1) * k };
  }

  // Ressort doux (ω 9, ζ 0,62) qui part à vitesse nulle : une box qui grandit, une caméra qui recentre une pile.
  function ressort(u, w, z) {
    w = w || 9; z = z || 0.62;
    if (u <= 0) return 0;
    const wd = w * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w * u) * (Math.cos(wd * u) + (z * w / wd) * Math.sin(wd * u));
  }

  // TEXTE MOT À MOT (réglages MotionLAB Fade Up : hauteur 48 px, un mot toutes les 0,105 s).
  // Chaque mot monte de 48 px avec la courbe e^(−8,71 t)·cos(2π·2,01 t) et apparaît en 0,115 s. Jamais lettre par lettre.
  function motAMot(t, i, o) {
    o = Object.assign({ hauteur: 48, decalage: 0.105 }, o);
    const tl = t - i * o.decalage;
    if (tl < 0) return { y: o.hauteur, opacite: 0 };
    return { y: o.hauteur * Math.exp(-8.71 * tl) * Math.cos(2.01 * TAU * tl), opacite: sat(tl / 0.115) };
  }

  // LAISSER LIRE : le dernier mot d'un texte doit être posé au moins `lecture` s avant la coupe ou la sortie.
  // Rend le facteur f (1 à 3) qui accélère tout le bloc (le temps du texte = t × f) quand il n'a pas la place.
  // n = nombre de mots, debut / fin = heure du 1er mot et de la coupe (ou de la sortie), en s.
  function compression(n, debut, fin, o) {
    o = Object.assign({ decalage: 0.105, pose: 0.48, lecture: 1.5, max: 3 }, o);
    const duree = Math.max(0, n - 1) * o.decalage + o.pose, dispo = fin - o.lecture - debut;
    return borne(duree / Math.max(0.05, dispo), 1, o.max);
  }

  // ZOOM FACE CAM (44 zooms mesurés image par image sur un YouTuber, 24/10/2026) : 0,85 s, +8,5 %, toujours le même geste
  // (lent → rapide → fin très douce), avant ou arrière, avec un whoosh grave un peu long qui démarre avec lui.
  // Rend l'échelle à poser sur la face cam. QUAND le poser : au début d'une phrase qui fait tourner le récit (voir le skill).
  function zoom(t, o) {
    o = Object.assign({ duree: 0.85, de: 1, a: 1.085 }, o);
    return lerp(o.de, o.a, COURBES.zoom.f(t / o.duree));
  }

  // ÉTIQUETTE de 2 mots qui apparaît sur le mot dit : naît à 65 % de sa taille, 85 % à 0,2 s, 98 % à 0,5 s,
  // 100 % à 0,8 s, sans jamais dépasser (aucun rebond). Opacité en 2 images.
  function etiquette(t, o) {
    o = Object.assign({ depart: 0.65, duree: 0.8 }, o);
    if (t < 0) return null;
    return { echelle: lerp(o.depart, 1, COURBES.etiquette.f(t / o.duree)), opacite: sat(t / (2 / 30)), rotation: 0 };
  }

  // DÉRIVE : une UI posée ne fige jamais (+1 % qui s'installe, puis +0,12 %/s).
  const derive = u => 1 + 0.010 * (1 - Math.exp(-Math.max(0, u) / 4)) + 0.0012 * Math.max(0, u);

  const MOTION = { bezier, COURBES, entree, elastic, arrivee, reaction, ressort, motAMot, derive, impulsion, compression, zoom, etiquette };
  if (typeof module !== "undefined" && module.exports) module.exports = MOTION;
  else racine.MOTION = MOTION;
})(typeof window !== "undefined" ? window : globalThis);
