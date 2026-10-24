// UI animées du kit, recréées en code web : les composants de mes Tuto IA et Tuto Split.
// Chaque fabrique pose ses éléments dans un conteneur et rend une fonction jouer(t), t en secondes depuis le début.
// Taille de travail : 360 × 220 px (le conteneur peut la mettre à l'échelle). Besoin de motion.js chargé avant.
(function (racine) {
  const M = racine.MOTION || (typeof require !== "undefined" ? require("../motion/motion.js") : null);
  const sat = u => Math.max(0, Math.min(1, u)), lerp = (a, b, u) => a + (b - a) * u;
  const relais = M.bezier(0.62, 0.05, 0.2, 0.92);          // un trait qui se trace, un relais d'une carte à l'autre
  const balaie = M.bezier(0.16, 1, 0.3, 1);                // sélection macOS : balaie vite, freine longuement
  const NS = "http://www.w3.org/2000/svg";

  const el = (tag, style, parent, txt) => {
    const e = document.createElement(tag);
    if (style) e.style.cssText = style;
    if (txt != null) e.textContent = txt;
    if (parent) parent.appendChild(e);
    return e;
  };
  const sv = (tag, attrs, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  const POLICE = '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", system-ui, sans-serif';
  const OMBRE = "0 18px 50px rgba(0,0,0,.10), 0 2px 6px rgba(0,0,0,.05)";
  const scene = conteneur => el("div", `position:absolute;left:0;top:0;width:360px;height:220px;font-family:${POLICE};color:#1D1D1F`, conteneur);
  const pose = (e, x, y, s, r, op) => { e.style.transform = `translate(${x}px,${y}px) scale(${s ?? 1}) rotate(${r ?? 0}deg)`; if (op != null) e.style.opacity = op; };
  // glyphes simples façon SF Symbols (blancs, une seule couleur)
  const GLYPHES = {
    micro: '<rect x="9" y="3" width="6" height="11" rx="3" fill="#fff"/><path d="M6 11a6 6 0 0 0 12 0M12 17v4" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round"/>',
    ciseaux: '<circle cx="7" cy="17" r="3" stroke="#fff" stroke-width="2" fill="none"/><circle cx="17" cy="17" r="3" stroke="#fff" stroke-width="2" fill="none"/><path d="M9 15 18 4M15 15 6 4" stroke="#fff" stroke-width="2" stroke-linecap="round"/>',
    note: '<path d="M9 18V5l11-2v13" stroke="#fff" stroke-width="2" fill="none" stroke-linejoin="round"/><circle cx="6.5" cy="18" r="2.5" fill="#fff"/><circle cx="17.5" cy="16" r="2.5" fill="#fff"/>',
    envoi: '<path d="M12 19V5M6 11l6-6 6 6" stroke="#fff" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
  };
  const tuile = (parent, glyphe, couleur, taille) => {
    const t = el("div", `width:${taille}px;height:${taille}px;border-radius:22.4%;background:${couleur};display:grid;place-items:center;flex:none`, parent);
    const s = sv("svg", { viewBox: "0 0 24 24", width: taille * 0.58, height: taille * 0.58 }, t);
    s.innerHTML = GLYPHES[glyphe];
    return t;
  };

  const UI = {};

  // 1. LISTE « RAPPELS » : une carte qui se pose, grandit ligne à ligne ; chaque case se coche en vert.
  UI.rappels = (conteneur, o) => {
    o = Object.assign({ surtitre: "AU PROGRAMME", titre: "Le montage", lignes: ["Dérush", "Rythme", "Export"] }, o);
    const sc = scene(conteneur), L = 34, H0 = 66;
    const carte = el("div", `position:absolute;left:70px;top:0;width:220px;border-radius:22px;background:#fff;box-shadow:${OMBRE};overflow:hidden`, sc);
    el("div", "position:absolute;left:18px;top:16px;font-size:10px;font-weight:600;letter-spacing:.08em;color:#8E8E93", carte, o.surtitre);
    el("div", "position:absolute;left:18px;top:30px;font-size:19px;font-weight:700;letter-spacing:-.02em", carte, o.titre);
    const lignes = o.lignes.map((txt, i) => {
      const l = el("div", `position:absolute;left:18px;right:18px;top:${H0 + i * L}px;height:${L}px`, carte);
      const filet = el("div", "position:absolute;left:0;top:0;height:1px;background:#EDEDED;width:0", l);
      const c = sv("svg", { width: 20, height: 20, viewBox: "0 0 20 20", style: "position:absolute;left:0;top:8px" }, l);
      const rond = sv("circle", { cx: 10, cy: 10, r: 8.5, fill: "none", stroke: "#C7C7CC", "stroke-width": 1.5, "stroke-dasharray": "2.6 2.4" }, c);
      const plein = sv("circle", { cx: 10, cy: 10, r: 0, fill: "#34C759" }, c);
      const coche = sv("path", { d: "M6 10.3l2.7 2.7L14.2 7.5", fill: "none", stroke: "#fff", "stroke-width": 2, "stroke-linecap": "round", "stroke-linejoin": "round", "stroke-dasharray": 12, "stroke-dashoffset": 12 }, c);
      const mot = el("div", "position:absolute;left:30px;top:8px;font-size:15px;font-weight:600", l, txt);
      return { l, filet, rond, plein, coche, mot };
    });
    const tLigne = i => 0.9 + i * 0.55, tCoche = i => 2.6 + i * 0.4;
    return t => {
      const e = M.entree(t);
      if (!e) { carte.style.opacity = 0; return; }
      // le contenant grandit en E.kin quand une ligne arrive, jamais d'un coup
      const h = H0 + 12 + lignes.reduce((a, _, i) => a + L * M.COURBES.ekin.f((t - tLigne(i)) / 0.45), 0);
      let y = e.y * 0.6, s = M.derive(t - 0.6), r = 0;
      lignes.forEach((_, i) => { const R = M.reaction(t - tLigne(i) - 0.3, i % 2 ? 1 : -1); y += R.y; s *= R.echelle; r += R.rotation; });
      carte.style.height = h + "px";
      // recentrage par transform (sous-pixel), jamais par top (pixels entiers)
      pose(carte, e.x * 0.6, 110 - h / 2 + y, s, r, e.opacite);
      lignes.forEach((g, i) => {
        const a = M.motAMot(t - tLigne(i), 0, { hauteur: 14 });
        g.l.style.opacity = a.opacite; g.l.style.transform = `translateY(${a.y}px)`;
        g.filet.style.width = (i ? 100 * relais((t - tLigne(i)) / 0.5) : 0) + "%";
        const c = sat((t - tCoche(i)) / 0.25);
        g.plein.setAttribute("r", 9 * M.COURBES.ekin.f(c));
        g.rond.style.opacity = 1 - c;
        g.coche.setAttribute("stroke-dashoffset", 12 * (1 - M.COURBES.ekin.f((t - tCoche(i) - 0.12) / 0.3)));
      });
    };
  };

  // 2. ENCHAÎNEMENT D'OUTILS (façon Raccourcis) : des cartes qui s'emboîtent, reliées par un trait ; toute la pile réagit.
  UI.enchainement = (conteneur, o) => {
    o = Object.assign({ etapes: [["micro", "#FF9F0A", "Transcrire", "mot à mot"], ["ciseaux", "#0A84FF", "Dérush", "les blancs, au creux"], ["envoi", "#34C759", "Exporter", "−14 LUFS"]] }, o);
    const sc = scene(conteneur), CH = 50, PAS = 64;
    const pile = el("div", "position:absolute;left:80px;width:200px;top:0;height:0", sc);
    const cartes = o.etapes.map(([g, c, ti, so], i) => {
      const k = el("div", `position:absolute;left:0;top:${i * PAS}px;width:200px;height:${CH}px;border-radius:15px;background:#fff;box-shadow:${OMBRE};display:flex;align-items:center;gap:10px;padding:0 10px`, pile);
      tuile(k, g, c, 30);
      const tx = el("div", "display:grid;line-height:1.15", k);
      el("div", "font-size:13px;font-weight:700", tx, ti);
      el("div", "font-size:11px;font-weight:500;color:#6E6E73", tx, so);
      return k;
    });
    const traits = o.etapes.slice(1).map((_, i) => el("div", `position:absolute;left:25px;top:${i * PAS + CH}px;width:2px;height:0;background:#D1D1D6;border-radius:1px`, pile));
    const tE = i => 0.2 + i * 0.75;
    const cible = n => 110 - (n * PAS + CH) / 2;                 // haut de la pile quand n + 1 cartes sont posées
    return t => {
      let y = 0, s = M.derive(t), r = 0, n = 0;
      cartes.forEach((k, i) => {
        const e = M.entree(t - tE(i));
        if (!e) { k.style.opacity = 0; return; }
        n = i;
        pose(k, e.x, e.y, 1, 0, e.opacite);
        // l'étape passée s'éteint en gris (jamais en transparence)
        k.style.filter = i < cartes.length - 1 && t > tE(i + 1) + 0.5 ? "grayscale(1) brightness(1.04)" : "";
        if (i) { const R = M.reaction(t - tE(i) - 0.5, i % 2 ? 1 : -1); y += R.y; s *= R.echelle; r += R.rotation; }
      });
      traits.forEach((tr, i) => { tr.style.height = (PAS - CH) * relais((t - tE(i + 1) - 0.35) / 0.4) + "px"; });
      // la pile reste centrée sur les cartes posées : la caméra suit par un ressort doux
      const top = n ? lerp(cible(n - 1), cible(n), M.ressort(t - tE(n))) : cible(0);
      pose(pile, 0, top + y, s, r);
    };
  };

  // 3. ANNOTATION AU STYLET : un mot et une flèche tracée main, posés en 15 i/s, qui tremblent toutes les 0,2 s.
  UI.stylet = (conteneur, o) => {
    o = Object.assign({ texte: "ici" }, o);
    const sc = scene(conteneur);
    el("div", "position:absolute;left:150px;top:118px;width:150px;height:84px;border-radius:14px;background:#E5E5EA", sc);
    const mot = el("div", "position:absolute;left:40px;top:42px;font-size:30px;font-weight:800;letter-spacing:-.02em;color:#1D1D1F", sc, o.texte);
    const s = sv("svg", { width: 360, height: 220, style: "position:absolute;left:0;top:0;overflow:visible" }, sc);
    const fleche = sv("path", { fill: "none", stroke: "#1D1D1F", "stroke-width": 4, "stroke-linecap": "round", "stroke-linejoin": "round" }, s);
    const pointe = sv("path", { fill: "none", stroke: "#1D1D1F", "stroke-width": 4, "stroke-linecap": "round", "stroke-linejoin": "round" }, s);
    const alea = k => { const x = Math.sin(k * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
    return t => {
      const q = Math.floor(t * 15) / 15;                       // posé en 15 i/s, comme un vrai trait au stylet
      const k = Math.floor(q / 0.2), j = (a) => (alea(k * 7 + a) - 0.5) * 1.6;
      const mo = sat((q - 0.2) / 0.27);
      mot.style.opacity = mo > 0 ? 1 : 0; mot.style.transform = `translate(${j(1)}px,${j(2)}px) rotate(${-3 + j(3)}deg)`;
      // UNE courbe simple, jamais de boucle
      const p = sat((q - 0.6) / 0.6), N = 24, pts = [];
      for (let i = 0; i <= N * p; i++) {
        const u = i / N, x = 92 + u * 96, y = 84 + u * 40 - Math.sin(u * Math.PI) * 26;
        pts.push((i ? "L" : "M") + (x + j(10 + i % 3)).toFixed(1) + " " + (y + j(20 + i % 3)).toFixed(1));
      }
      fleche.setAttribute("d", pts.join(""));
      // la pointe suit la tangente du bout de la courbe : deux traits de 13 px à ±32°
      const ex = 188, ey = 124, dx = 96, dy = 40 + 26 * Math.PI, n = Math.hypot(dx, dy), ux = dx / n, uy = dy / n;
      const barbe = (a, k) => { const c = Math.cos(a), s = Math.sin(a); return [(ex - 13 * (ux * c - uy * s) + j(k)).toFixed(1), (ey - 13 * (ux * s + uy * c) + j(k + 1)).toFixed(1)]; };
      const [ax, ay] = barbe(0.56, 4), [bx, by] = barbe(-0.56, 6);
      pointe.setAttribute("d", p >= 1 ? `M${ax} ${ay}L${ex + j(8)} ${ey + j(9)}L${bx} ${by}` : "");
    };
  };

  // 4. CARTE « S'ABONNER » : le curseur vise le bouton, se pose, clique ; le bouton encaisse puis passe à « Abonné ».
  UI.abonner = (conteneur, o) => {
    o = Object.assign({ nom: "Ta chaîne", info: "12,4 k abonnés" }, o);
    const sc = scene(conteneur);
    const carte = el("div", `position:absolute;left:60px;top:66px;width:240px;height:88px;border-radius:24px;background:#fff;box-shadow:${OMBRE};display:flex;align-items:center;gap:12px;padding:0 16px`, sc);
    el("div", "width:46px;height:46px;border-radius:50%;background:linear-gradient(135deg,#D1D1D6,#AEAEB2);flex:none", carte);
    const tx = el("div", "display:grid;line-height:1.2;flex:1;min-width:0", carte);
    el("div", "font-size:14px;font-weight:700", tx, o.nom);
    el("div", "font-size:11px;color:#6E6E73", tx, o.info);
    const bouton = el("div", "height:32px;padding:0 14px;border-radius:16px;background:#1D1D1F;color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;gap:5px;white-space:nowrap", carte, "S'abonner");
    const curseur = sv("svg", { width: 22, height: 22, viewBox: "0 0 22 22", style: "position:absolute;left:0;top:0;overflow:visible" }, sc);
    sv("path", { d: "M2 1v16l4.2-4 2.8 6.4 2.8-1.2-2.8-6.2H15z", fill: "#000", stroke: "#fff", "stroke-width": 1.4, "stroke-linejoin": "round" }, curseur);
    const T_CLIC = 1.55;
    return t => {
      const e = M.entree(t);
      if (!e) { carte.style.opacity = 0; curseur.style.opacity = 0; return; }
      const R = M.reaction(t - T_CLIC - 0.05, 1);
      pose(carte, e.x * 0.5, e.y * 0.5 + R.y, M.derive(t - 0.6) * R.echelle, R.rotation, e.opacite);
      // le curseur vise le CENTRE RÉEL du bouton, mesuré à chaque image
      const rb = bouton.getBoundingClientRect(), rs = sc.getBoundingClientRect(), z = rs.width / 360 || 1;
      const bx = (rb.left + rb.width / 2 - rs.left) / z, by = (rb.top + rb.height / 2 - rs.top) / z;
      const u = M.COURBES.ekin.f((t - 0.6) / 0.75);             // arrivée posée 0,2 s avant le clic
      const cx = lerp(330, bx, u) + Math.sin(u * Math.PI) * -18, cy = lerp(200, by, u);
      curseur.style.opacity = t > 0.5 ? 1 : 0;
      curseur.style.transform = `translate(${cx - 2}px,${cy - 1}px)`;
      // appui : −8 % en 1 image, tenu 2 images, retour en 5
      const w = t - T_CLIC, appui = w < 0 ? 1 : w < 1 / 30 ? 0.92 : w < 3 / 30 ? 0.92 : lerp(0.92, 1, M.COURBES.ekin.f((w - 3 / 30) / (5 / 30)));
      bouton.style.transform = `scale(${appui})`;
      const abonne = w >= 0;
      bouton.style.background = abonne ? "#E5E5EA" : "#1D1D1F";
      bouton.style.color = abonne ? "#1D1D1F" : "#fff";
      bouton.textContent = abonne ? "🔔 Abonné" : "S'abonner";
    };
  };

  // 5. PILULE QUI SE DÉPLIE : un point d'accent grandit dans un cercle blanc, puis la pilule s'ouvre et le texte monte.
  UI.pilule = (conteneur, o) => {
    o = Object.assign({ texte: "Rendu terminé", couleur: "#0A84FF" }, o);
    const sc = scene(conteneur);
    const pil = el("div", `position:absolute;top:88px;height:44px;border-radius:22px;background:#fff;box-shadow:${OMBRE};overflow:hidden`, sc);
    const point = el("div", `position:absolute;left:12px;top:12px;width:20px;height:20px;border-radius:50%;background:${o.couleur}`, pil);
    const mots = o.texte.split(" ").map((m, i) => el("span", `position:absolute;top:12px;font-size:15px;font-weight:700;white-space:nowrap;letter-spacing:-.01em`, pil, m));
    let largeurs = null;
    return t => {
      if (!largeurs) { let x = 42; largeurs = mots.map(m => { const w = m.offsetWidth || m.textContent.length * 8; const p = x; x += w + 5; return p; }); largeurs.fin = x + 12; }
      const c = M.COURBES.ekin.f((t - 0.2) / 0.3), W = lerp(44, largeurs.fin, M.COURBES.ekin.f((t - 0.6) / 0.5));
      pil.style.width = W + "px"; pil.style.left = (180 - W / 2) + "px";
      pil.style.opacity = t > 0.2 ? 1 : 0; pil.style.transform = `scale(${lerp(0.4, 1, c) * M.derive(t - 1.1)})`;
      point.style.transform = `scale(${M.COURBES.ekin.f((t - 0.33) / 0.13)})`;     // le point grandit en 4 images
      mots.forEach((m, i) => { const a = M.motAMot(t - 0.95, i, { hauteur: 14 }); m.style.left = largeurs[i] + "px"; m.style.opacity = a.opacite; m.style.transform = `translateY(${a.y}px)`; });
    };
  };

  // 6. SÉLECTION MACOS : un mot se sélectionne, aplat bleu clair à coins droits, poignées bleues.
  UI.selection = (conteneur, o) => {
    o = Object.assign({ avant: "Le", mot: "rythme", apres: "décide tout." }, o);
    const sc = scene(conteneur);
    const ligne = el("div", "position:absolute;left:0;right:0;top:86px;text-align:center;font-size:30px;font-weight:700;letter-spacing:-.025em;white-space:nowrap", sc);
    ligne.append(o.avant + " ");
    const zone = el("span", "position:relative;display:inline-block", ligne);
    const aplat = el("span", "position:absolute;left:-2px;top:2px;bottom:-2px;width:0;background:#CFE0FB", zone);
    el("span", "position:relative", zone, o.mot);
    const g = el("span", "position:absolute;left:-3px;top:-2px;width:2px;bottom:-4px;background:#2E6BE6", zone);
    el("span", "position:absolute;left:-4px;top:-7px;width:8px;height:8px;border-radius:50%;background:#2E6BE6", g);
    const d = el("span", "position:absolute;width:2px;top:2px;bottom:-4px;background:#2E6BE6", zone);
    el("span", "position:absolute;left:-3px;bottom:-7px;width:8px;height:8px;border-radius:50%;background:#2E6BE6", d);
    ligne.append(" " + o.apres);
    return t => {
      const p = balaie((t - 0.8) / 0.5), W = (zone.offsetWidth || 90) + 4;
      aplat.style.width = (p * W) + "px";
      g.style.opacity = d.style.opacity = t > 0.8 ? 1 : 0;
      d.style.left = (p * W - 3) + "px";
      ligne.style.transform = `scale(${M.derive(t)})`;
    };
  };

  UI.LISTE = [
    ["rappels", "Liste qui se coche", "Récaps, feuilles de route, étapes d'un tuto."],
    ["enchainement", "Enchaînement d'outils", "Un workflow étape par étape ; toute la pile réagit à chaque carte."],
    ["stylet", "Annotation au stylet", "Montrer un détail : un mot et une flèche tracée main, en 15 i/s."],
    ["abonner", "Carte « S'abonner »", "Le curseur vise le vrai bouton, se pose, clique."],
    ["pilule", "Pilule qui se déplie", "Un statut, une confirmation : du point à la pilule."],
    ["selection", "Sélection macOS", "Mettre un mot en évidence, comme dans l'OS."],
  ];

  if (typeof module !== "undefined" && module.exports) module.exports = UI;
  else racine.UI = UI;
})(typeof window !== "undefined" ? window : globalThis);
