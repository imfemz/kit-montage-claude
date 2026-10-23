---
name: montage
description: Monte une vidéo avec Claude Code — dérush mot à mot, test des marqueurs (rythme), animations d'UI aux bonnes courbes, son et musique, export normalisé, et le carnet des corrections. À utiliser dès qu'on parle de monter, dérusher, couper les blancs, rythmer, animer une UI ou une carte, mixer, exporter une vidéo, ou de « montage », même sans nommer ce skill.
---

# Montage

Tu montes une vidéo avec la personne. Elle décide, tu exécutes et tu mesures. Tu ne livres jamais sans avoir relu le carnet.

## Les commandes

| Commande | Ce que tu fais |
|---|---|
| `/montage derush <video>` | Transcription mot à mot, puis coupe des blancs, puis montage brut |
| `/montage rythme` | Test des marqueurs : trouve les trous de plus de 4 s, propose quoi y mettre |
| `/montage ui <description>` | Anime une carte, une fenêtre ou un texte avec les courbes du kit |
| `/montage son <fichier>` | Mesure le niveau, cale la musique sur l'émotion, dose les effets |
| `/montage export <video>` | Export à −14 LUFS, H.264, puis re-mesure |
| `/montage carnet "<correction>"` | Ajoute une correction au carnet, avec son contrôle |

Sans commande précise, déduis l'étape de la demande. L'ordre normal : derush → rythme → ui → son → export.

## Avant tout

1. Lis `carnet/CARNET.md` en entier. C'est la checklist de livraison.
2. Vérifie que `ffmpeg` répond et que `.venv/bin/python` existe. Sinon, renvoie à l'installation du `README.md`.
3. Travaille dans un dossier par vidéo : `projets/<nom>/` (rush, transcript, cutlist, exports).

## derush

1. `.venv/bin/python scripts/transcrire.py <video> --langue fr` → `transcript.json`.
2. `.venv/bin/python scripts/derush.py <video> transcript.json` → `cutlist.json`.
   - Par défaut, aucun mot n'est retiré : seuls les blancs de plus d'1 s sont raccourcis, coupés au creux de la voix.
   - Montre à la personne les « reprises possibles » trouvées. Tu ne les coupes que si elle dit oui.
3. Attends sa validation, puis `.venv/bin/python scripts/couper.py <video> cutlist.json --transcript transcript.json` → `rough-cut.mp4`.

## rythme

1. Liste les informations nouvelles du montage dans `evenements.json` : `[{"t": 12.4, "canal": "texte", "label": "titre"}]`. Canaux : image, texte, idee, musique, sfx, ambiance. Les raccords de la cutlist comptent déjà comme « image ».
2. `.venv/bin/python scripts/marker_test.py --duree <s> --cutlist cutlist.json --evenements evenements.json --sortie rythme/`.
3. Pour chaque trou de plus de 4 s : propose une information qui dit la phrase en cours (un texte, une carte, un changement de musique). Jamais un effet gratuit.
4. Relance le test jusqu'à zéro trou.

## ui

Pars d'un composant existant avant d'en inventer un : `ui/composants.js` (liste qui se coche, enchaînement d'outils, annotation au stylet, carte « S'abonner », pilule, sélection) et `sous-titres/sous-titres.js` (variante 1, mot-clé bleu, sélection). Ouvre `galerie.html` pour les voir. Pour le reste, lis `motion/after-effects.md` (After Effects) ou utilise `motion/motion.js` (web, Remotion, HyperFrames, Canvas). Les règles :

- **Entrée d'une box** : lent → rapide → lent (`E.kin`, `cubic-bezier(0.65, 0, 0.15, 1)`), 0,6 s, depuis (+60, +150) px, droite. Opacité 46 → 100 % en 0,12 s. Petit objet : 0,3 s.
- **Rebond d'arrivée** : la signature Elastic (0,05 · 2 · 4), sur une arrivée courte et lancée. Jamais de rotation ni de wiggle à l'entrée.
- **Réaction de chaîne** : quand un élément se branche (ligne, message, étape, clic), toute l'UI fait 5,5 px · +1,3 % · 0,55°, période 0,58 s, sens alterné.
- **Pas d'une roue, carrousel, sortie** : `kinetic`, `cubic-bezier(0.75, 0, 0.11, 1)`.
- **Texte** : mot à mot (48 px, un mot toutes les 0,105 s), jamais lettre par lettre. Au moins 1,5 s de lecture après l'entrée.
- **Jamais d'arrêt net** : ce qui est posé dérive (`MOTION.derive`). Un contenant ne change jamais de taille d'un coup.
- Une seule couleur d'accent, des fonds sobres, de l'air : 96 px des bords sur les côtés, 64 px en haut et en bas (1080p).

## son

1. `.venv/bin/python scripts/niveau.py <fichier>` : sonie intégrée, true peak, fenêtres qui s'écartent de plus de 4 LU.
2. Musique : écris l'arc émotionnel du script (calme, tension, révélation, fin), repère les sections du morceau, et fais tomber chaque section sur sa phrase. La vraie fin du morceau tombe sur la dernière phrase.
3. Effets : légers, seulement sur les moments importants, environ 19 LU sous la voix.

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
- Niveau : −14 LUFS ±0,5, true peak ≤ −1 dBTP.
- Tu dis ce que tu as mesuré, et ce que tu n'as pas pu vérifier.
