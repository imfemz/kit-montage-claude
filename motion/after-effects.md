# Les mêmes courbes dans After Effects

Copie-colle. Chaque bloc dit où il va.

## E.kin : entrée lent → rapide → lent

Deux clés de position. Clic droit sur les clés → Assistant d'image clé → Éditeur de vitesse :

| Clé | Influence sortante | Influence entrante | Vitesse |
|---|---|---|---|
| 1re (départ, +150 px, à la verticale) | 65 % | — | 0 |
| 2e (posée) | — | 85 % | 0 |

Durée : 0,6 s pour une box, 0,3 s pour un petit objet. Opacité : 46 → 100 % en 0,12 s.

## Kinetic : pas d'une roue, d'un carrousel, sortie

Même principe, influences **75 %** en sortie et **89 %** en entrée, environ 0,6 s par pas.

## Signature Elastic (rebond d'arrivée)

À coller sur la propriété (Alt-clic sur le chronomètre). La dernière clé doit arriver **lancée** : arrivée courte (0,12 à 0,28 s), interpolation linéaire en entrée de la dernière clé.

```js
amp = 0.05; freq = 2.0; decay = 4.0;
n = 0;
if (numKeys > 0) { n = nearestKey(time).index; if (key(n).time > time) n--; }
t = (n == 0) ? 0 : time - key(n).time;
if (n > 0 && t < 1) {
  v = velocityAtTime(key(n).time - thisComp.frameDuration / 10);
  value + v * amp * Math.sin(freq * t * 2 * Math.PI) / Math.exp(decay * t);
} else value;
```

Variantes : `freq = 3` (plus vif), `freq = 3.5; decay = 6` (nerveux, petits objets).

## Réaction de chaîne

Quand un élément se branche dans une UI, toute l'UI réagit. Sur le null parent de l'UI, une clé de temps `t0` au moment du branchement :

```js
// Position (ajoute 5,5 px vers le bas au pic)
t0 = 2.0;               // heure du branchement, en secondes
w = time - t0; P = 0.58; z = 0.42;
k = 0;
if (w > 0) {
  wd = 2 * Math.PI / P; wn = wd / Math.sqrt(1 - z * z); tp = Math.atan(wd / (z * wn)) / wd;
  k = Math.exp(-z * wn * w) * Math.sin(wd * w) / (Math.exp(-z * wn * tp) * Math.sin(wd * tp));
}
value + [0, 5.5 * k];
```

Même calcul de `k` pour l'échelle (`value * (1 + 0.013 * k)`) et la rotation (`value + 0.55 * k`, sens alterné d'un branchement à l'autre).

## Zoom face cam (mesuré sur 44 zooms d'un YouTuber, 24/10/2026)

Deux clés d'échelle : 100 → 108,5 % (ou l'inverse) en **0,85 s**. Éditeur de vitesse :

| Clé | Influence sortante | Influence entrante | Vitesse |
|---|---|---|---|
| 1re | 35 % | — | 0 |
| 2e | — | 73 % | 0 |

Même courbe en web : `cubic-bezier(0.35, 0, 0.27, 1)` (25 / 75 / 95 % du trajet à 25 / 50 / 75 % du temps). Au début d'une phrase qui fait tourner le récit, jamais sur le mot accentué, avec un whoosh grave qui démarre avec la clé.

## Étiquette de 2 mots (même source)

Échelle 65 → 100 % en **0,8 s**, sans dépasser : 1re clé à vitesse ≈ 39 %/s et influence 28 %, 2e clé à vitesse 0 et influence 92 %. En web : `cubic-bezier(0.28, 0.25, 0.08, 1)` (85 % de la taille à 0,2 s, 98 % à 0,5 s). Elle apparaît sur le mot dit (0 à +0,3 s), avec un pop léger.

## Règles qui ne bougent pas

- Jamais de rotation ni de wiggle à l'entrée. La légère rotation n'existe que dans la réaction de chaîne.
- Jamais d'arrêt net : ce qui est posé continue de dériver (+1 % d'échelle qui s'installe, puis +0,12 %/s).
- Un contenant ne change jamais de taille d'un coup : il s'ouvre en E.kin (0,4 à 0,5 s) et son contenu apparaît dedans.
- Texte : mot par mot, jamais lettre par lettre. Le dernier mot est posé au moins 1,5 s avant la coupe ou la sortie.
