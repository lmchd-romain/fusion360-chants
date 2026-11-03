# Décisions

(décidé) = Romain ; (mon choix) = l'agent, contestable. Questions produit posées le 2026-11-03, groupées à l'orchestrateur :
tant que Romain ne répond pas, le choix recommandé s'applique.

| # | Sujet | Décision | Date |
|---|---|---|---|
| 1 | Plugin | Pinceau pour plaquer les chants, couleur, tableau des chants ; inspiré de JoinerCAD, pages publiques seulement (décidé, Q36) | 2026-11-02 |
| 2 | Nom | Provisoire : « Edge Banding » (en), « Chants plaqués » (fr), « エッジバンド » (ja), « Bekantung » (de). Dossier d'add-in **définitif** `EdgeBanding`, pour éviter un renommage plus tard (décidé) | 2026-11-03 |
| 3 | Boutons | SOLIDE → Modifier : « Chants plaqués » promu ; « Tableau des chants », « Surbrillance des chants », « Retirer les couleurs des chants » dans le menu du panneau (mon choix) | 2026-11-03 |
| 4 | Couleur par défaut | Couleur réelle sur les faces (voie 1 de l'étude) : visible partout, peut-être sur les plans ; la surbrillance (voie 2) reste disponible par le menu. Réglable dans le dialogue (« Couleur des chants ») (mon choix) | 2026-11-03 |
| 5 | Couleurs d'affichage | Couleurs repères vives, pas la teinte réelle du chant (un chant blanc sur un panneau blanc serait invisible) : ABS 2 mm blanc orange, ABS 0,8 mm blanc jaune, ABS 2 mm noir violet, placage chêne 0,6 vert, placage noyer 0,6 rouge ; 10 couleurs au choix (mon choix) | 2026-11-03 |
| 6 | Bibliothèque | 5 références par défaut ; « + Nouvelle référence… » et réglage nom / épaisseur / couleur dans le dialogue ; gardée dans `derniers_reglages.json` (pas de suppression en 0.1.0) (mon choix) | 2026-11-03 |
| 7 | Changer la référence d'un chant | Gomme puis nouveau clic avec la nouvelle référence ; la référence choisie vaut pour les prochains clics (mon choix) | 2026-11-03 |
| 8 | Ce qu'est un chant | Face plane perpendiculaire au panneau (axe d'épaisseur = normale de la plus grande face plane), ou face cylindrique d'axe parallèle (chant cintré), à 1,1° près. Le survol n'allume que ces faces (mon choix) | 2026-11-03 |
| 9 | Longueur d'un chant | Aire de la face / épaisseur du panneau : exact pour un chant droit ou cintré (mon choix) | 2026-11-03 |
| 10 | Contact | « Tous les chants visibles » exclut un chant si un point à 0,05 mm devant lui (3 points le long du chant) est dans un autre corps visible ; pré-tri par boîtes englobantes (mon choix) | 2026-11-03 |
| 11 | Composant utilisé plusieurs fois | Ses chants sont partagés (attribut et couleur sur la face du composant) ; le tableau multiplie par le nombre d'occurrences (mon choix ; à confirmer par P3) | 2026-11-03 |
| 12 | Marquage | Attribut JSON `lmchdEdgeBanding/chant` sur la face native : identifiant, référence, épaisseur, couleur, apparence d'origine. Registre `lmchdEdgeBanding/registre` sur le design pour repérer les chants disparus (mon choix) | 2026-11-03 |
| 13 | Tableau | Marge par chant 40 mm par défaut (20 mm de débord à chaque bout), réglable ; débit en option, décoché par défaut ; CSV UTF-8 avec BOM, « ; », virgule décimale (Excel français, quelle que soit la langue de Fusion) ; page HTML ouverte dans le navigateur (mon choix) | 2026-11-03 |
| 14 | Côtés du schéma | Long 1 / Long 2 = côtés longs, Court 1 / Court 2 = bouts ; débit = longueur − chants des bouts, largeur − chants des côtés longs (mon choix) | 2026-11-03 |
| 15 | Pas de fonction personnalisée | Rien dans la timeline : attributs et apparences seulement ; une seule étape d'annulation par OK (mon choix) | 2026-11-03 |
| 16 | Identifiants | Préfixe `lmchdEdgeBanding` (commandes, groupe d'attributs, graphiques), GUID propre au manifest (mon choix) | 2026-11-03 |
