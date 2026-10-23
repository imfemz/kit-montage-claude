# Kit montage Claude

Une base propre pour monter tes vidéos avec Claude Code : dérush mot à mot, rythme mesuré, animations d'UI aux bonnes courbes, son, export, et un carnet qui retient chacune de tes corrections.

Présentation animée des commandes : https://claude.ai/artifact/LuNdTPL28t9CwLe8UknYeT

## Installation

Il te faut [Claude Code](https://claude.com/claude-code), Python 3.10+ et ffmpeg.

```bash
git clone https://github.com/imfemz/kit-montage-claude.git
cd kit-montage-claude
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

ffmpeg : `brew install ffmpeg` (Mac), `winget install ffmpeg` (Windows), `sudo apt install ffmpeg` (Linux).

## Utilisation

Ouvre Claude Code dans le dossier (`claude`), dépose ta vidéo dans `projets/`, puis :

| Tape | Pour |
|---|---|
| `/montage derush projets/ma-video.mp4` | couper les blancs sans toucher un mot |
| `/montage rythme` | trouver les trous de plus de 4 s |
| `/montage ui une carte titre qui arrive` | animer une UI avec les bonnes courbes |
| `/montage son projets/ma-video.mp4` | mesurer le niveau, caler la musique |
| `/montage export projets/rough-cut.mp4` | sortir à −14 LUFS |
| `/montage carnet "le zoom sert à rien"` | noter une correction pour toujours |

## Ce qu'il y a dedans

```
.claude/skills/montage/   le skill (la méthode)
scripts/                  transcription, dérush, coupe, test des marqueurs, niveau, export
motion/                   les courbes d'animation (web : motion.js, After Effects : after-effects.md)
ui/                       6 UI animées tirées de mes vidéos
sous-titres/              3 styles de sous-titres
galerie.html              tout voir bouger (ouvre-la dans ton navigateur)
carnet/CARNET.md          le carnet des corrections, avec 12 exemples réels
```

## Ce qui est testé, et ce qui ne l'est pas encore

- Les scripts ont 36 tests automatiques (`.venv/bin/python -m pytest`) et ont tourné de bout en bout sur une vraie vidéo.
- Le dérush ne coupe pas un « blanc » qui contient du son (musique, effet) : il te le liste pour écoute. `--couper-blancs-sonores` force la coupe.
- Il n'a pas encore été essayé sur beaucoup de rushs bruts : si une coupe tombe mal, ajoute-la au carnet et ouvre une issue.

## Le carnet

Le prompt parfait n'existe pas. Ce qui marche, c'est un fichier : chaque fois que tu dis « non », Claude note l'erreur, pourquoi c'en est une, comment la repérer, et le contrôle qui la bloque. Il le relit avant chaque livraison.

---

Fait par [Femz](https://imfemz.com). Licence MIT.
