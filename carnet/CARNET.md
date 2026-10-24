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

Les dix-sept premières entrées sont des exemples réels, tirés de vrais montages. Garde-les, modifie-les, ajoute les tiennes à la suite.

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
- Ce qui n'allait pas : un titre disparaît, ou le plan change, alors que les derniers mots arrivent encore.
- Pourquoi c'est une erreur : le spectateur a l'impression d'avoir raté quelque chose.
- Comment la repérer : l'heure où le DERNIER mot est posé, comparée à la coupe ou à la sortie qui suit.
- Contrôle : le dernier mot posé au moins 1,5 s avant (2,2 s pour un titre) ; sinon le bloc s'accélère (`MOTION.compression`, jusqu'à × 3), sinon on raccourcit le texte.

---

## 13. Un zoom posé au hasard
- Ce qui n'allait pas : des zooms secs, sur des mots pris au hasard ; « un zoom crie pas IA, un zoom sec et au mauvais moment, oui ».
- Pourquoi c'est une erreur : le zoom doit capter l'attention au moment où le récit tourne ; ailleurs, il se voit comme un effet.
- Comment la repérer : pour chaque zoom, la phrase qui commence à cet instant et son rôle (contraste, conséquence, exemple, définition, question).
- Contrôle : `scripts/zooms.py` : au début d'une phrase qui tourne, 9 à 15 s entre deux, 7 s après une coupe ; toujours le même geste (0,85 s, +8,5 %, `MOTION.zoom`) et un whoosh grave.

## 14. Une coupe calée sur l'heure de Whisper
- Ce qui n'allait pas : on garde un bout de silence avant la phrase, ou on mange le début du premier mot.
- Pourquoi c'est une erreur : après un silence, Whisper fait commencer le premier mot 0,3 à 0,6 s trop tôt ; ses heures ne sont pas la voix.
- Comment la repérer : l'énergie de la voix autour de chaque borne.
- Contrôle : `scripts/derush.py` recale le début des mots sur l'attaque réelle (`transcript.recale.json`) avant de couper.

## 15. Un « Et » coupé au jugé
- Ce qui n'allait pas : pour retirer un « Et » en tête de phrase, la coupe gardait la fin du « Et » ou mangeait le mot suivant.
- Pourquoi c'est une erreur : le creux d'énergie le plus bas n'est pas forcément entre les deux mots ; l'oreille l'entend tout de suite.
- Comment la repérer : re-transcrire 1,4 s à partir du point de coupe : le premier mot entendu doit être le bon.
- Contrôle : `scripts/verifier_coupe.py <video> <t> <mot> --chercher` ; aucun creux ne passe → le mot est collé, il faut une autre prise.

## 16. La carte loin de la personne, collée au bord
- Ce qui n'allait pas : une carte posée contre le bord droit, avec un grand vide entre elle et la personne.
- Pourquoi c'est une erreur : l'œil fait l'aller-retour entre deux zones au lieu de lire une seule image.
- Comment la repérer : à la hauteur de la carte, l'écart corps → carte comparé à l'écart carte → bord.
- Contrôle : la carte au milieu de l'espace entre le corps (à sa hauteur, bras compris) et le bord de l'écran, à hauteur de tête ou d'épaule ; elle peut passer derrière l'épaule si la personne est détourée au-dessus.

## 17. Habiller un rush plat
- Ce qui n'allait pas : trois versions du montage, de plus en plus habillées, sur une prise face cam au même débit pendant 5 minutes ; « même moi j'arrive pas à regarder jusqu'au bout ».
- Pourquoi c'est une erreur : les UI, la musique et les coupes s'ajoutent par-dessus l'énergie de la prise, elles ne la créent pas.
- Comment la repérer : regarder le rush brut comme un spectateur avant de monter (énergie, preuves montrables, structure qui ne se répète pas).
- Contrôle : un rush plat se dit AVANT d'habiller ; on propose un retournage (script en mots-clés, phrases liées par « mais » / « donc ») ou des inserts à filmer.

<!-- Ajoute tes corrections ici, à la suite. -->
