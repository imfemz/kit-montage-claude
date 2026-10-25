# Les UI

Six composants tirés de mes vidéos (Tuto IA, Tuto Split), recréés en code web. Ouvre `../galerie.html` pour les voir bouger.

| Composant | Pour |
|---|---|
| `UI.rappels` | une liste qui se coche : récap, feuille de route, étapes |
| `UI.enchainement` | un workflow en cartes qui s'emboîtent ; toute la pile réagit |
| `UI.stylet` | montrer un détail : un mot et une flèche tracée main |
| `UI.abonner` | la carte « S'abonner », avec un curseur qui vise le vrai bouton |
| `UI.pilule` | un statut qui se déplie depuis un point |
| `UI.selection` | un mot sélectionné comme dans macOS |

## Utiliser

```html
<script src="motion/motion.js"></script>
<script src="ui/composants.js"></script>
<script>
  const jouer = UI.rappels(document.querySelector("#scene"), { titre: "Le montage", lignes: ["Dérush", "Rythme", "Export"] });
  jouer(1.2);   // l'état à 1,2 s : appelle-la à chaque image (navigateur, Remotion, HyperFrames…)
</script>
```

Ou demande à Claude : `/montage ui une liste qui se coche avec mes 3 étapes`.

Chaque composant suit les règles du kit : entrée lent → rapide → lent, rebond seulement en réaction de chaîne, jamais d'arrêt net, un contenant qui s'ouvre au lieu de sauter de taille.

## Le verre (`verre.js`)

Mes cartes en glassmorphisme au glow bleu, celles de mes vidéos YouTube. Tout vient d'une de mes comps After Effects, échantillonnée image par image :

| Composant | Pour |
|---|---|
| `UI.verre` | un commentaire, une citation, un avis : avatar blanc à liseré bleu, pseudo, texte blanc mot à mot |
| `UI.etiquette` | 2 mots qui apparaissent sur le mot dit, à côté de ta tête |
| `UI.habiller` | ta propre boîte (carte, pilule, fenêtre) dans le même verre, avec un light sweep en option |

- **Le look** : un dégradé noir → blanc à 32 % sur un flou d'arrière-plan (22 px), une brume bleue, un reflet bleu en diagonale, l'arête du haut bleue, un halo froid au-dessus, un scintillement de ±3 % et un grain léger. Le verre a besoin d'une image derrière lui : ta vidéo (dans la galerie, un fond sombre uni).
- **L'entrée** : la carte monte DROIT de 119 px et apparaît en 0,23 s, l'avatar suit 0,17 s après, chaque mot monte de 90 px sur un ressort, un mot toutes les 0,101 s. **Aucune rotation.** La sortie descend de 112 px en accélérant.
- **Laisser lire** : le texte est accéléré (jusqu'à × 3) pour que le dernier mot soit posé 1,5 s avant la sortie.
- **Deux pièges réglés** : l'opacité se pose sur chaque couche (une carte en opacité < 1 perd son flou d'arrière-plan) ; les lumières sont des couleurs semi-transparentes, pas un mode de fusion « plus-lighter » qui ne voit pas l'image derrière une carte isolée.
- **Le placement** : à hauteur de tête ou d'épaule, du côté libre, au milieu de l'espace entre ton corps et le bord de l'écran ; elle peut passer derrière ton épaule si tu détoures ton plan et le poses au-dessus pendant qu'elle est là.

```html
<script src="motion/motion.js"></script>
<script src="ui/verre.js"></script>
<script>
  // scène de 1920 × 1080 px, posée par-dessus ta vidéo ; la carte arrive à 0,3 s et sort à 5,6 s
  const jouer = UI.verre(document.querySelector("#scene"), { pseudo: "@quelqu_un", texte: "Ton commentaire ici", x: 1000, y: 330, t0: 0.3, t1: 5.6 });
  jouer(1.2);
</script>
```

