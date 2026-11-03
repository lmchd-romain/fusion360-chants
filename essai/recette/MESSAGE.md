# Recette Chants plaqués (Edge Banding) — message à coller dans Claude Desktop

**Avant (une seule fois)** : Fusion ouvert ; Utilitaires → Scripts et compléments → onglet Compléments → « + » →
choisir le dossier `EdgeBanding` du dépôt `fusion360-chants` → Exécuter (cocher « Exécuter au démarrage »).
Le connecteur Fusion (Fusion MCP) doit être actif dans Claude Desktop.

Puis copiez **tout le bloc ci-dessous** dans Claude Desktop.

---

```text
Tu joues la recette automatique de l'add-in Fusion « Chants plaqués » (Edge Banding), version 0.1.0, avec le connecteur
Fusion MCP. Règles : ne modifie ni n'enregistre aucun document existant ; la recette crée elle-même un nouveau document,
que tu n'enregistres pas. Ne change aucune préférence de Fusion. Réponds en français, simplement : l'utilisateur n'est pas
développeur.

1. Vérifie que l'add-in tourne : exécute dans Fusion ce script Python et lis le résultat.
   import sys
   print("edgebanding.recette" in sys.modules, sys.modules.get("edgebanding") and sys.modules["edgebanding"].VERSION)
   Si le résultat est False : l'add-in n'est pas démarré. Dis à l'utilisateur, en une ligne :
   « Utilitaires → Scripts et compléments → Compléments → EdgeBanding → Exécuter », puis recommence l'étape 1.

2. Lance la recette (elle construit un petit caisson, une étagère, deux portes identiques, un plateau rond et 10 tasseaux,
   plaque les chants, les colore, écrit le tableau des chants, modifie une pièce, puis vérifie tout) :
   import sys, json
   r = sys.modules["edgebanding.recette"].jouer()
   print(json.dumps(r, ensure_ascii=False, indent=1))
   Si l'exécution renvoie une erreur ou dépasse le délai, relance-la une fois, puis rapporte l'erreur telle quelle.

3. Fais deux captures d'écran de la vue de Fusion : vue d'ensemble, puis zoom sur le caisson (deux côtés et un dessous).
   Les chants doivent être orange (et jaunes sur un tasseau) ; les deux chants du dessous qui touchent les côtés ne sont
   pas colorés. Décris en une phrase ce que tu vois.

4. Gestes à la main, à demander à l'utilisateur un par un (attends sa réponse avant le suivant) :
   M1. SOLIDE → Modifier : le bouton « Chants plaqués » est-il là, avec l'icône d'un panneau au chant bleu ? Le menu du
       panneau Modifier montre-t-il aussi « Tableau des chants », « Surbrillance des chants », « Retirer les couleurs des
       chants » ? (oui / non)
   M2. Ouvrir « Chants plaqués » : au survol, le dessus d'une étagère reste-t-il éteint et un chant s'allume-t-il ?
       Cliquer 3 chants libres du plateau rond et des tasseaux : le résumé compte-t-il les chants et les mètres ?
       Recliquer un chant déjà plaqué : part-il ? Les clics restent-ils fluides (pas d'attente) ? Puis Annuler.
       (oui / non pour chaque)
   M3. Dans « Chants plaqués », bouton « Tous les chants visibles » : combien de temps avant que ça réponde (à l'œil) ?
       Puis Annuler.
   M4. (facultatif, sonde P4) Si l'utilisateur veut bien enregistrer ce document d'essai dans un dossier d'essai :
       Fichier → Nouvelle mise en plan → depuis la conception, vue de base en style « ombré ». Les chants colorés
       apparaissent-ils en couleur sur la mise en plan ? (oui / non / pas essayé)
   M5. Menu « Surbrillance des chants » deux fois : les chants s'allument-ils puis s'éteignent-ils ? Menu « Retirer les
       couleurs des chants » : les chants reprennent-ils la couleur du bois ? Ctrl+Z : les couleurs reviennent-elles ?
   M6. Menu « Tableau des chants » → OK : la page s'ouvre-t-elle dans le navigateur avec un schéma par pièce ? Ouvrir le
       fichier CSV (dossier Documents\EdgeBanding) dans Excel : colonnes séparées et accents corrects ?
   M7. Thème sombre (seulement si l'utilisateur l'utilise déjà) : les icônes restent-elles lisibles ?

5. Rapport final, court :
   - un tableau : scénario → OK / échec → détail en quelques mots (lis « bilan » et chaque scénario du JSON) ;
   - les réponses M1 à M7 ;
   - le chemin du fichier « fichier » du JSON ;
   - puis le JSON complet dans un bloc de code, pour que l'utilisateur le recopie à la session qui développe le plugin.
```

---

## Ce que la recette vérifie

| Scénario | Question | Réussite |
|---|---|---|
| construction | Pièces d'essai construites par script dans un document neuf | caisson (2 côtés + dessous entre eux), étagère, porte ×2 (même composant), plateau rond, 10 tasseaux à la racine |
| V1_detection | Seuls les chants sont reconnus, bien mesurés | 4 chants par panneau, 1 chant cintré de π × 400 mm sur le plateau ; côté 720 × 560 × 18 |
| V2_tous_les_chants_visibles | Les chants au contact sont exclus | 59 chants uniques, 2 exclus (bouts du dessous contre les côtés) |
| P1_fluidite_50_chants | Travail d'un clic, aperçu de 50 chants, OK sur tous | < 100 ms par clic, aperçu < 1 s ; durées relevées |
| V3_couleur_sur_les_faces | Apparence copiée et recolorée posée sur la face seule | couleur orange exacte, 2 apparences créées, dessus du panneau inchangé |
| P3_composant_deux_fois | Une couleur posée sur une porte change-t-elle l'autre ? | réponse relevée (attendu : les deux changent) |
| V4_tableau_csv | Tableau : quantités, dimensions, débit, CSV avec BOM | porte × 2, dessous 564 × 560 × 18, débit 564 × 556, 4 chants ABS 0,8 |
| V5_surbrillance | Bascule de la surbrillance | un graphique par apparition de chant, puis plus rien |
| P2_survie_des_attributs | L'attribut survit-il à une modification de la pièce ? | a : épaisseur changée, b : timeline reculée puis remise → 1 face ; c : entaille dans le chant, relevé |
| V6_chants_disparus | Corps supprimé → chants signalés disparus | 4 chants du tasseau 0 |
| V7_retirer_couleurs | Apparences d'origine rendues, chants gardés | plus aucune face colorée, marques présentes |

La recette recolore les chants à la fin pour que les captures montrent le résultat. P4 (mise en plan) : geste M4.
