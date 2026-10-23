// Trois styles de sous-titres, recréés en code web d'après mes réglages After Effects.
// La version After Effects d'origine (police de marque, grain, bords adoucis) est dans MotionLAB : https://www.femzlab.shop/motionlab/
// Chaque fabrique rend une fonction jouer(t), t en secondes depuis l'arrivée du sous-titre. Besoin de motion.js chargé avant.
(function (racine) {
  const M = racine.MOTION || (typeof require !== "undefined" ? require("../motion/motion.js") : null);
  const TAU = Math.PI * 2, sat = u => Math.max(0, Math.min(1, u));
  const POLICE = '"Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif';
  const balaie = M.bezier(0.16, 1, 0.3, 1);

  // Les chiffres de la variante 1 (relevés sur la comp d'origine) :
  // chaque mot part 0,75 × la taille de police plus bas, monte avec e^(−8,71 t)·cos(2π·2,01 t), fondu linéaire,
  // un mot toutes les 0,125 s (courbe étirée ×1,544), cadence posée à 20 i/s, ombre noire à 59 %, 135°, 9 px, adoucie 12 px.
  const V1 = { etire: 1.544, decalage: 0.081, fondu: 0.115, ips: 20 };
  function monteeMot(t, i, taille) {
    const tl = t / V1.etire - i * V1.decalage;               // temps « naturel » du mot
    if (tl < 0) return { y: 0.75 * taille, op: 0 };
    return { y: 0.75 * taille * Math.exp(-8.71 * tl) * Math.cos(2.01 * TAU * tl), op: sat(tl / V1.fondu) };
  }

  function bloc(conteneur, texte, taille, o) {
    const b = document.createElement("div");
    b.style.cssText = `position:absolute;left:0;right:0;text-align:center;font-family:${POLICE};font-weight:700;font-size:${taille}px;` +
      `line-height:.95;letter-spacing:-.06em;color:#fff;white-space:nowrap;` +
      `text-shadow:${(0.05 * taille).toFixed(1)}px ${(0.05 * taille).toFixed(1)}px ${(0.09 * taille).toFixed(1)}px rgba(0,0,0,.59);` +
      `filter:blur(${o.flou ?? 0.45}px)`;
    conteneur.appendChild(b);
    const mots = texte.split(" ").map((m, i) => {
      const s = document.createElement("span");
      s.style.cssText = "display:inline-block;margin:0 .14em;position:relative";
      s.textContent = m;
      b.appendChild(s);
      return s;
    });
    return { b, mots };
  }

  const ST = {};

  // Variante 1 : blanc, mot à mot avec un petit rebond, ombre douce, cadence à 20 i/s.
  ST.variante1 = (conteneur, texte, o) => {
    o = Object.assign({ taille: 40, y: 0 }, o);
    const { b, mots } = bloc(conteneur, texte, o.taille, o);
    b.style.top = o.y + "px";
    return t => {
      const q = Math.floor(t * V1.ips) / V1.ips;
      mots.forEach((m, i) => { const a = monteeMot(q, i, o.taille); m.style.opacity = a.op; m.style.transform = `translateY(${a.y.toFixed(2)}px)`; });
    };
  };

  // Mot-clé bleu : la variante 1, avec UN mot dans le bleu des miniatures (dégradé opaque, jamais transparent).
  ST.motCle = (conteneur, texte, o) => {
    o = Object.assign({ taille: 40, y: 0, cle: 0 }, o);
    const { b, mots } = bloc(conteneur, texte, o.taille, o);
    b.style.top = o.y + "px";
    const k = mots[o.cle];
    k.style.background = "linear-gradient(180deg,#6ACBFF 0%,#3AA2FF 55%,#0A7AFF 100%)";
    k.style.webkitBackgroundClip = "text"; k.style.backgroundClip = "text";
    k.style.color = "transparent";
    k.style.textShadow = "none";
    k.style.filter = `drop-shadow(${(0.05 * o.taille).toFixed(1)}px ${(0.05 * o.taille).toFixed(1)}px ${(0.06 * o.taille).toFixed(1)}px rgba(0,0,0,.45))`;
    return ST.variante1Joue(mots, o);
  };
  ST.variante1Joue = (mots, o) => t => {
    const q = Math.floor(t * V1.ips) / V1.ips;
    mots.forEach((m, i) => { const a = monteeMot(q, i, o.taille); m.style.opacity = a.op; m.style.transform = `translateY(${a.y.toFixed(2)}px)`; });
  };

  // Sélection : les mots montent, puis le mot-clé se sélectionne façon macOS (aplat bleu clair, coins droits, texte noir).
  ST.selection = (conteneur, texte, o) => {
    o = Object.assign({ taille: 40, y: 0, cle: 0 }, o);
    const { b, mots } = bloc(conteneur, texte, o.taille, o);
    b.style.top = o.y + "px";
    const k = mots[o.cle];
    const aplat = document.createElement("span");
    aplat.style.cssText = "position:absolute;left:-.08em;top:.04em;bottom:-.06em;width:0;background:#CFE0FB;z-index:-1";
    k.style.zIndex = 0; k.prepend(aplat);
    const debut = (mots.length - 1) * V1.decalage * V1.etire + 0.75;
    const joue = ST.variante1Joue(mots, o);
    return t => {
      joue(t);
      const p = balaie((t - debut) / 0.5);
      aplat.style.width = `calc(${(p * 100).toFixed(1)}% + .16em)`;
      aplat.style.opacity = p > 0 ? 1 : 0;
      k.style.color = p > 0.15 ? "#1D1D1F" : "#fff";
      k.style.textShadow = p > 0.15 ? "none" : "";
    };
  };

  ST.LISTE = [
    ["variante1", "Variante 1", "Blanc, mot à mot avec un petit rebond, ombre douce."],
    ["motCle", "Mot-clé bleu", "Un seul mot dans le bleu des miniatures."],
    ["selection", "Sélection", "Le mot important se sélectionne, comme dans l'OS."],
  ];

  if (typeof module !== "undefined" && module.exports) module.exports = ST;
  else racine.SOUS_TITRES = ST;
})(typeof window !== "undefined" ? window : globalThis);
