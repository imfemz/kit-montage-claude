---
name: montage
description: Monte une vidéo avec Claude Code — dérush mot à mot (bornes posées sur l'énergie de la voix), test des marqueurs (rythme), zooms face cam au bon moment, animations d'UI et cartes en verre aux bonnes courbes, son et musique, export normalisé, et le carnet des corrections. À utiliser dès qu'on parle de monter, dérusher, couper les blancs, rythmer, zoomer, animer une UI ou une carte, mixer, exporter une vidéo, ou de « montage », même sans nommer ce skill.
---

# Montage

Tu montes une vidéo avec la personne. Elle décide, tu exécutes et tu mesures. Tu ne livres jamais sans avoir relu le carnet.

## Les commandes

| Commande | Ce que tu fais |
|---|---|
| `/montage derush <video>` | Transcription mot à mot, puis coupe des blancs, puis montage brut |
| `/montage rythme` | Test des marqueurs : trouve les trous de plus de 4 s, propose quoi y mettre |
| `/montage zooms` | Propose les zooms face cam au début des phrases qui font tourner le récit |
| `/montage ui <description>` | Anime une carte, une fenêtre ou un texte avec les courbes du kit |
| `/montage son <fichier>` | Mesure le niveau, cale la musique sur l'émotion, dose les effets |
| `/montage export <video>` | Export à −14 LUFS, H.264, puis re-mesure |
| `/montage carnet "<correction>"` | Ajoute une correction au carnet, avec son contrôle |

Sans commande précise, déduis l'étape de la demande. L'ordre normal : derush → rythme → zooms → ui → son → export.

## Avant tout

1. Lis `carnet/CARNET.md` en entier. C'est la checklist de livraison.
2. Vérifie que `ffmpeg` répond et que `.venv/bin/python` existe. Sinon, renvoie à l'installation du `README.md`.
3. Travaille dans un dossier par vidéo : `projets/<nom>/` (rush, transcript, cutlist, exports).
4. **Juge le rush avant de l'habiller.** Regarde-le comme un spectateur : de l'énergie, des preuves montrables, une structure qui ne se répète pas. Un face cam plat de 5 min au même débit ne se sauve pas avec des UI et de la musique : dis-le tout de suite et propose de retourner ou de filmer des inserts, au lieu de compenser au montage.
5. **L'accroche est alignée** : la miniature, la 1re phrase et le 1er plan disent la même chose. Si ce n'est pas le cas, signale-le avant de monter.

## derush

1. `.venv/bin/python scripts/transcrire.py <video> --langue fr` → `transcript.json`.
2. `.venv/bin/python scripts/derush.py <video> transcript.json` → `cutlist.json`.
   - Par défaut, aucun mot n'est retiré : seuls les blancs de plus d'1 s sont raccourcis, coupés au creux de la voix.
   - **Les bornes se posent sur l'énergie de la voix, jamais sur les heures de Whisper** : après un silence, Whisper fait commencer le premier mot 0,3 à 0,6 s trop tôt. `derush.py` recale ces débuts sur l'attaque réelle et écrit `transcript.recale.json`.
   - Montre à la personne les « reprises possibles » trouvées. Tu ne les coupes que si elle dit oui.
3. Attends sa validation, puis `.venv/bin/python scripts/couper.py <video> cutlist.json --transcript transcript.recale.json` (ou `transcript.json` si rien n'a été recalé) → `rough-cut.mp4`.
4. **Retirer un mot en tête de phrase** (« Et », « Euh »), seulement si la personne le demande : jamais au jugé. `.venv/bin/python scripts/verifier_coupe.py <video> <début du souffle> <mot suivant> --chercher` essaie les creux d'énergie et garde le premier où l'on ENTEND le bon mot (re-transcription de 1,4 s). Aucun ne passe : le mot est collé, il faut une autre prise.
5. Les phrases dites se lient par « mais » ou « donc », jamais par « et » ou « ensuite » : si un retournage est prévu, propose la phrase réécrite.

## rythme

1. Liste les informations nouvelles du montage dans `evenements.json` : `[{"t": 12.4, "canal": "texte", "label": "titre"}]`. Canaux : image, texte, idee, musique, sfx, ambiance. Les raccords de la cutlist comptent déjà comme « image ».
2. `.venv/bin/python scripts/marker_test.py --duree <s> --cutlist cutlist.json --evenements evenements.json --sortie rythme/`.
3. Pour chaque trou de plus de 4 s : propose une information qui dit la phrase en cours (un texte, une carte, un changement de musique). Jamais un effet gratuit.
4. Relance le test jusqu'à zéro trou.
5. **Le rythme, c'est la diversité des infos, pas la vitesse** : varie le TYPE d'information (son, image, texte, émotion). La dixième coupe identique est une habitude, pas un rythme.

## zooms

`.venv/bin/python scripts/zooms.py transcript.cut.json --cutlist cutlist.json` → `zooms.json`. Les règles (mesurées sur 44 zooms d'un YouTuber qui zoome bien) :

- **Quand** : au DÉBUT d'une phrase qui fait tourner le récit (« mais », « donc », un exemple, une définition, une question, l'accroche). Jamais pour souligner un mot fort : le zoom marque la structure, pas l'emphase.
- **Espacement** : un zoom toutes les 9 à 15 s ; au moins 7 s après une coupe, au moins 2 s avant la suivante.
- **Le geste, toujours le même** : 0,85 s, +8,5 %, avant puis arrière, courbe `MOTION.zoom` (`cubic-bezier(0.35, 0, 0.27, 1)` : lent → rapide → fin très douce).
- **Le son** : un whoosh grave un peu long qui démarre AVEC le zoom.
- Un zoom sec ou mis au mauvais moment fait IA ; un zoom au début de la bonne phrase capte l'attention. Montre la liste à la personne avant de les poser.

## ui

Pars d'un composant existant avant d'en inventer un : `ui/composants.js` (liste qui se coche, enchaînement d'outils, annotation au stylet, carte « S'abonner », pilule, sélection), `ui/verre.js` (carte en verre au glow bleu, étiquette de 2 mots) et `sous-titres/sous-titres.js` (variante 1, mot-clé bleu, sélection). Ouvre `galerie.html` pour les voir. Pour le reste, lis `motion/after-effects.md` (After Effects) ou utilise `motion/motion.js` (web, Remotion, HyperFrames, Canvas). Les règles :

- **Entrée d'une box** : lent → rapide → lent (`E.kin`, `cubic-bezier(0.65, 0, 0.15, 1)`), 0,6 s, depuis (+60, +150) px, droite. Opacité 46 → 100 % en 0,12 s. Petit objet : 0,3 s.
- **Rebond d'arrivée** : la signature Elastic (0,05 · 2 · 4), sur une arrivée courte et lancée. Jamais de rotation ni de wiggle à l'entrée.
- **Réaction de chaîne** : quand un élément se branche (ligne, message, étape, clic), toute l'UI fait 5,5 px · +1,3 % · 0,55°, période 0,58 s, sens alterné.
- **Pas d'une roue, carrousel, sortie** : `kinetic`, `cubic-bezier(0.75, 0, 0.11, 1)`.
- **Texte** : mot à mot (48 px, un mot toutes les 0,105 s), jamais lettre par lettre.
- **Laisser lire** : le DERNIER mot est posé au moins 1,5 s avant la coupe ou la sortie. S'il n'a pas la place, accélère tout le bloc (`MOTION.compression`, jusqu'à × 3) ; au-delà, raccourcis le texte ou allonge le plan.
- **Carte en verre** (`UI.verre`) : elle monte DROIT de 119 px (courbe échantillonnée), apparaît en 0,23 s, l'avatar suit, puis chaque mot monte ; elle sort en descendant. Aucune rotation, ni à l'entrée ni après. L'opacité se pose couche par couche (une carte en opacité < 1 perd son flou d'arrière-plan).
- **Étiquette de 2 mots** (`UI.etiquette`, `MOTION.etiquette`) : naît à 65 % de sa taille depuis le côté de la tête, se pose en 0,8 s, sans rebond.
- **Sur le face cam** : un élément arrive SUR le mot qu'il illustre (0 à +0,3 s), à hauteur de tête ou d'épaule, du côté libre, au milieu de l'espace entre le corps (à la hauteur de l'élément) et le bord de l'écran. Jamais sur le visage.
- **Derrière l'épaule** : une carte peut passer derrière la personne. Pose sa colonne 30 px après la tête et descends-la jusqu'à ce que l'épaule touche sa marge ; détoure la personne (par exemple avec Robust Video Matting) et pose ce calque au-dessus de la carte, seulement pendant qu'elle est visible.
- **Jamais d'arrêt net** : ce qui est posé dérive (`MOTION.derive`). Un contenant ne change jamais de taille d'un coup.
- Une seule couleur d'accent, des fonds sobres, de l'air : 96 px des bords sur les côtés, 64 px en haut et en bas (1080p).

## son

1. `.venv/bin/python scripts/niveau.py <fichier>` : sonie intégrée, true peak, fenêtres qui s'écartent de plus de 4 LU.
2. Musique : écris l'arc émotionnel du script (calme, tension, révélation, fin), repère les sections du morceau, et fais tomber chaque section sur sa phrase. La vraie fin du morceau tombe sur la dernière phrase.
3. La musique suit aussi le **ton, la vitesse et le contexte** de chaque phrase, pas seulement les mots : une même phrase dite calmement, tendue ou euphorique n'appelle pas la même musique.
4. **Le lit** : environ 21 dB sous la voix, plus bas dans l'accroche (la voix d'abord). La batterie entre sur les transitions et les contrastes, jamais sur une question.
5. **Les trous de musique** : environ un toutes les 10 s, d'environ 1,8 s, SOUS la phrase clé (il commence au mot qui la précède). Sortie en fondu d'environ 0,4 s, retour NET, souvent en milieu de phrase, avec un pop ou un boom grave léger. Une grande coupe pendant la promesse de l'accroche.
6. **Effets** : légers, environ 19 LU sous la voix. Un pop par élément qui arrive à l'écran, un pop + un boom grave pour un concept clé, rien pour un simple texte souligné, un whoosh grave sur chaque zoom.

## export

`.venv/bin/python scripts/exporter.py <video> --sortie exports/final.mp4`, puis `scripts/niveau.py` sur le fichier sorti. Annonce l'écart à −14 LUFS : il doit tenir à ±0,5 LU.

## carnet

Quand la personne corrige quelque chose (« la musique est trop forte », « ce zoom sert à rien ») :

1. Ajoute une entrée à la fin de `carnet/CARNET.md` : ce qui n'allait pas, pourquoi, comment la repérer, quel contrôle.
2. Si un contrôle automatique est possible (une mesure, un seuil), écris-le ou branche-le sur un script existant.
3. Applique la correction partout dans la vidéo, pas seulement à l'endroit montré.

## Avant de livrer

- Carnet relu, entrée par entrée.
- Test des marqueurs : zéro trou de plus de 4 s.
- Zooms : chacun au début d'une phrase qui tourne, aucun sur un plan de moins de 2 s, aucun à moins de 7 s d'une coupe.
- Textes : chaque dernier mot reste lisible 1,5 s avant la coupe ou la sortie.
- Niveau : −14 LUFS ±0,5, true peak ≤ −1 dBTP.
- Tu dis ce que tu as mesuré, et ce que tu n'as pas pu vérifier.
