# Les sous-titres

Trois styles recréés en code web d'après mes réglages After Effects. Ouvre `../galerie.html` pour les voir.

| Style | Ce qu'il fait |
|---|---|
| `SOUS_TITRES.variante1` | blanc, mot à mot avec un petit rebond, ombre douce, cadence posée à 20 i/s |
| `SOUS_TITRES.motCle` | la variante 1 avec un mot dans le bleu de mes miniatures |
| `SOUS_TITRES.selection` | le mot important se sélectionne façon macOS |

```js
const jouer = SOUS_TITRES.motCle(scene, "Coupe dans les creux", { taille: 64, y: 900, cle: 3 });
jouer(t);   // t = secondes depuis l'arrivée du sous-titre
```

Taille conseillée : 64 px en 16:9, 76 px en 9:16 (en 1080p). Un sous-titre ne touche jamais le bord : 96 px de marge sur les côtés.

La police d'origine (IvyStyle Sans) est remplacée par Plus Jakarta Sans, libre. **La version After Effects d'origine**, avec le grain et les bords adoucis, est dans [MotionLAB](https://www.femzlab.shop/motionlab/).
