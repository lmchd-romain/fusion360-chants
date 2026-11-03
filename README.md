# Chants plaqués (Edge Banding) — add-in Autodesk® Fusion

Version 0.1.0 · Windows (Mac non essayé) · nom provisoire, dossier d'add-in définitif : `EdgeBanding`.

## Ce que fait le plugin

1. **Pinceau** : SOLIDE → Modifier → **Chants plaqués**. Choisir la référence de chant (ABS 2 mm blanc, ABS 0,8 mm,
   placage chêne 0,6 mm…), puis cliquer les chants : un clic plaque, un nouveau clic retire (gomme). Seuls les chants
   s'allument au survol. Bouton **Tous les chants visibles** : plaque d'un coup tous les chants des panneaux visibles,
   sauf ceux au contact d'une autre pièce. Résumé dans le dialogue : « 6 chants · ABS 2 mm blanc · 3,40 m ».
2. **Couleur** : à OK, chaque chant prend la couleur de sa référence (couleur réelle sur la face, enregistrée dans le
   fichier). Menu **Retirer les couleurs des chants** pour revenir aux apparences d'origine ; menu **Surbrillance des
   chants** pour les voir en couleur sans rien modifier.
3. **Tableau des chants** (menu du panneau Modifier) : longueurs par référence avec marge de coupe, petit schéma par pièce
   (4 côtés), cotes de débit en option (cote finie − épaisseur du chant), export **CSV** pour Excel et page imprimable.

Les chants sont gardés **dans le fichier** (attribut sur chaque face). Si une pièce est modifiée et qu'un chant marqué
disparaît, le pinceau et le tableau le signalent. Aucune API en preview : le fichier reste sain sans le plugin.

## Installation

1. Récupérer ce dépôt (GitHub Desktop : *Clone*).
2. Fusion → Utilitaires → **Scripts et compléments** → onglet **Compléments** → **+** → choisir le dossier `EdgeBanding`.
3. **Exécuter** ; cocher **Exécuter au démarrage**.

## Utilisation

- Pinceau : voir ci-dessus. La référence choisie vaut pour les **prochains** clics ; pour changer la référence d'un chant
  déjà plaqué, le recliquer (il part) puis le recliquer avec la nouvelle référence.
- Nouvelle référence : liste **Chant** → « + Nouvelle référence… », puis groupe **Réglage de la référence** (nom,
  épaisseur, couleur d'affichage). La bibliothèque est gardée pour les prochaines fois.
- Un composant utilisé plusieurs fois (deux portes identiques) partage ses chants : plaquer l'une plaque l'autre.
- Sorties du tableau : dossier `Documents\EdgeBanding\<document> - chants.csv / .html`.

## Limites

- Chants reconnus : faces planes perpendiculaires au panneau, et chants cintrés (cylindres) ; pas les chanfreins.
- Le tableau range les chants droits sur les 4 côtés de la pièce ; un chant cintré ou oblique va dans « Autres chants ».
- Mises en plan : la couleur des chants y apparaît-elle ? À vérifier (recette, geste M4).
- Builds Fusion validés : aucun pour l'instant (recette à jouer).
- Japonais et allemand traduits par l'IA, à relire par un natif.

## Dépannage

- Rien ne se passe au clic : lire `EdgeBanding/demarrage.log` (panne au démarrage), puis `EdgeBanding/journal.log`.
- Recharger : Scripts et compléments → EdgeBanding → Arrêter, puis Exécuter. Icône absente : redémarrer Fusion.

## Développement

- Noyau pur (sans `adsk`, testé) : `edgebanding/chants.py` (reconnaître, mesurer, totaliser, débit, chants disparus),
  `export.py` (CSV et page HTML), `reglages.py` (réglages, bibliothèque, couleurs), `textes.py`, `journal.py`.
- Couche Fusion : `fusion_api.py` (chants, attributs, apparences, surbrillance, lecture du tableau), `interface.py`
  (boutons), `pinceau.py`, `tableau.py`, `actions.py` (surbrillance, retrait des couleurs), `recette.py`.
- Tests : `python -m pytest` (Python 3.13 et 3.14), dont un chargement complet avec un faux module `adsk`.
- Recette dans Fusion : `essai/recette/MESSAGE.md` (un message à coller dans Claude Desktop, connecteur Fusion MCP).
- Icônes : `python docs/icones/generer_icones.py && node docs/icones/rendre_png.js`.
- Docs : `docs/ETAT.md`, `docs/DECISIONS.md`, `docs/icones/HISTORIQUE.md`. Étude d'origine :
  `docs/idees/chants-plaques/faisabilite-pinceau.md` du dépôt `fusion360-ecosystem-plugin`.
