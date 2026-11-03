# État — Chants plaqués (Edge Banding) 0.1.0

Au 2026-11-03. [vérifié] = constaté dans Fusion ; [supposé] = pas encore vu dans Fusion. **Rien n'a encore tourné dans Fusion.**

## Fait

| Partie | État | Preuve |
|---|---|---|
| Reconnaître un chant, le mesurer, le ranger par côté, totaux, débit, chants disparus | fait, testé | `tests/test_chants.py` |
| CSV Excel français, page HTML, bibliothèque et réglages, traductions en, fr, ja, de | fait, testé | `tests/test_sorties.py` |
| Couche Fusion sur une fausse géométrie (mesures, marquage, couleurs, tableau, registre) | testé hors Fusion | `tests/test_fusion_api.py` |
| Pinceau : clic, gomme, composant utilisé deux fois, face refusée | logique testée hors Fusion | `tests/test_pinceau.py` |
| Chargement de l'add-in, 4 boutons, dialogues | testé avec un faux `adsk` | `tests/test_chargement.py` |
| Tout ce qui touche Fusion (survol, sélection, attributs, apparences, graphiques, contact) | écrit, [supposé] | recette V1–V7, P1–P3 |
| Icônes (5) | faites (16, 32, @2x, clair, sombre) ; non vues dans Fusion | `docs/icones/HISTORIQUE.md`, geste M1 |

Tests : 42 verts sous Python 3.13.18 et 3.14.6 (`python -m pytest`), `compileall` sans erreur.

## À faire

1. Jouer la recette (`essai/recette/MESSAGE.md`) et reporter le JSON ici ; corriger ce qui échoue.
2. Selon P2 (entaille dans un chant) : si l'attribut se perd, retrouver le chant par position et normale (repli de l'étude).
3. Selon P4 (mise en plan) : si la couleur n'y paraît pas, le tableau des chants reste la voie pour l'atelier.
4. Relire le japonais et l'allemand (traduits par l'IA).
5. v2 : suppression d'une référence de la bibliothèque ; changer la référence d'un chant sans gomme.

## Points [supposé] à surveiller

- `Attributes.add` sur une face existante met à jour la valeur au lieu d'échouer.
- `face.appearance = None` retire la surcharge d'apparence d'une face (repli : apparence du corps).
- `BRepFace.appearance` sur la face d'un composant utilisé deux fois change les deux occurrences (P3).
- Les graphiques dessinés dans `executePreview` disparaissent seuls à chaque nouvel aperçu.
- Une commande sans champ s'exécute dès le clic (surbrillance, retrait des couleurs) ; les graphiques créés dans
  `execute` restent affichés après la commande.
- `SelectionCommandInput` : cliquer une face déjà sélectionnée la retire (gomme native) ; `addSelection` dans
  `inputChanged` est permis.
- Filtre de sélection `SolidFaces`.
