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
