# Le carnet

Chaque fois que tu dis « non » à Claude sur un montage, la correction s'écrit ici. Claude relit tout le carnet avant chaque livraison.

Une entrée = quatre lignes. La plus importante est la dernière : lui dire « fais attention » ne sert à rien, il oublie. Un contrôle qui bloque, lui, ne laisse plus passer l'erreur.

```
## N. Titre court de l'erreur
- Ce qui n'allait pas : …
- Pourquoi c'est une erreur : …
- Comment la repérer : …
- Contrôle : … (le script ou la mesure qui bloque la livraison)
```

Les douze premières entrées sont des exemples réels, tirés de vrais montages. Garde-les, modifie-les, ajoute les tiennes à la suite.

---

## 1. Un blanc coupé au milieu d'un mot
- Ce qui n'allait pas : on entend des bouts de syllabes aux raccords, ça fait robot.
- Pourquoi c'est une erreur : l'oreille repère la moindre syllabe tronquée, même sans savoir dire pourquoi.
- Comment la repérer : un point de coupe à moins de 40 ms d'un mot de la transcription.
- Contrôle : `scripts/derush.py` coupe au creux d'énergie de la voix, jamais à l'intérieur d'un mot.

## 2. Un trou de plus de 4 secondes
- Ce qui n'allait pas : un passage où rien de nouveau n'arrive (ni image, ni texte, ni son, ni idée).
- Pourquoi c'est une erreur : c'est là que les gens décrochent.
- Comment la repérer : le test des marqueurs, un marqueur par information nouvelle.
- Contrôle : `scripts/marker_test.py` sort en erreur tant qu'il reste un trou de plus de 4 s.

## 3. La musique plate du début à la fin
- Ce qui n'allait pas : la musique démarre au début et ne bouge plus. Elle ne raconte rien.
- Pourquoi c'est une erreur : la musique porte l'émotion ; plate, elle devient un bruit de fond.
- Comment la repérer : écrire l'arc du script (calme, tension, révélation, fin) et vérifier que la musique change sur ces phrases.
- Contrôle : chaque section de la musique est calée sur une phrase du script, et sa vraie fin tombe sur la dernière phrase.

## 4. Les petits sons couvrent la voix
- Ce qui n'allait pas : un bruit de clavier sur chaque mot des sous-titres, plus fort que la voix.
- Pourquoi c'est une erreur : un effet qui tombe pendant qu'on parle se bat avec la voix.
- Comment la repérer : mesurer l'effet contre le mix au même instant.
- Contrôle : effets seulement sur les mots importants, environ 19 LU sous la voix.

## 5. Le niveau qui saute
- Ce qui n'allait pas : certains passages plus forts que d'autres sans raison.
- Pourquoi c'est une erreur : le spectateur touche au volume, puis part.
- Comment la repérer : la sonie par fenêtres de 10 s.
- Contrôle : `scripts/niveau.py` signale toute fenêtre à plus de 4 LU de la médiane ; `scripts/exporter.py` livre à −14 LUFS, −1 dBTP.

## 6. Un zoom sur un plan de moins de 2 secondes
- Ce qui n'allait pas : un plan d'une seconde avec un zoom dessus, ça fait sursauter.
- Pourquoi c'est une erreur : l'œil n'a pas le temps de lire le cadre avant qu'il change.
- Comment la repérer : la durée de chaque plan qui porte un zoom.
- Contrôle : aucun zoom animé sous 2 s ; un plan court garde le cadre du plan d'avant.

## 7. Un zoom qui ne montre rien
- Ce qui n'allait pas : des zooms posés pour « dynamiser », sur rien de précis.
- Pourquoi c'est une erreur : un zoom sans raison se voit, et il fait IA.
- Comment la repérer : pour chaque zoom, nommer ce qu'il montre.
- Contrôle : un zoom sans cible nommée est retiré.

## 8. Un mot coupé par le bord
- Ce qui n'allait pas : un sous-titre qui touche le bord de l'écran, un mot à moitié caché en haut d'une liste.
- Pourquoi c'est une erreur : un mot coupé se lit comme un bug.
- Comment la repérer : le cadre de chaque texte comparé aux marges.
- Contrôle : marges de 96 px sur les côtés et 64 px en haut et en bas (en 1080p) ; une ligne qui sort s'efface entière.

## 9. Le flash entre deux plans
- Ce qui n'allait pas : une ou deux images du plan d'en dessous passent entre deux images plein écran.
- Pourquoi c'est une erreur : on ne le voit pas vraiment, mais on le sent.
- Comment la repérer : les bornes de chaque plan, à l'image près.
- Contrôle : bornes calées sur les images exactes, jamais arrondies à la milliseconde ; deux pleins écrans qui se suivent se chevauchent d'une image.

## 10. Une animation qui s'arrête net
- Ce qui n'allait pas : une carte arrive, puis se fige d'un coup.
- Pourquoi c'est une erreur : un arrêt net fait mécanique.
- Comment la repérer : la vitesse image par image ; un palier à zéro juste après un mouvement.
- Contrôle : lent → rapide → lent (`motion/motion.js`), puis une dérive lente qui ne s'arrête jamais.

## 11. Une rotation à l'entrée
- Ce qui n'allait pas : les cartes arrivent penchées et tanguent.
- Pourquoi c'est une erreur : ça fait gadget ; une interface d'appli arrive droite.
- Comment la repérer : la rotation de chaque élément pendant son entrée.
- Contrôle : rotation à zéro à l'entrée ; la légère rotation est réservée à la réaction de chaîne.

## 12. Un texte qui part avant d'être lu
- Ce qui n'allait pas : un titre disparaît alors qu'on n'a pas fini de le lire.
- Pourquoi c'est une erreur : le spectateur a l'impression d'avoir raté quelque chose.
- Comment la repérer : le temps entre la fin de l'entrée et le début de la sortie.
- Contrôle : au moins 1,5 s après l'entrée complète, 2,2 s pour un titre.

---

<!-- Ajoute tes corrections ici, à la suite. -->
