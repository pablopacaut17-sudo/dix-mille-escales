# Feuille de route de Dix Mille Escales

Chantiers demandés par Pablo le 27 novembre 2026 (« fais tout »). La tâche « Amélioration » du matin en réalise **un par
jour** (point 3, avant toute autre idée), le teste, puis le coche ici avec la date et une ligne de bilan. Ordre conseillé.

## À faire
- [ ] **Questions sans réponse** : traiter chaque matin `sans_reponse` de data/ia-a-verifier.json (questions que le site n'a pas su traiter) : réponse vérifiée dans static/reponses.json, ou mieux, nouveau type de question dans static/questions.js quand plusieurs se ressemblent. Déplacer chaque élément traité dans `sans_reponse_traites` ([slug, q, d]). *(tous les jours, pas seulement une fois)*
- [x] **Deuxième espace de 1 Go** (fait le 28/11/2026) : build.py (preparer_espace2) copie lieux.json.gz et donnees.json.gz des villes dans espace2/, robots.yml les pousse sur la branche espace2, le dépôt pablopacaut17-sudo.github.io les publie toutes les heures si nouvelle version (publier.yml) sous https://pablopacaut17-sudo.github.io/dme-donnees/. Le navigateur lit d'abord cette adresse, avec repli sur l'ancienne (ESPACE2_JS dans tetes()). Résultat : site principal 869 → 128 Mo, deuxième espace 601 Mo (taille réelle, du --apparent-size).
- [x] **Allègement → déplacement** (fait le 28/11/2026) : les gros fichiers sont déplacés vers le deuxième espace au lieu d'être réduits ; alleger() ne sert plus qu'en dernier recours, sur le site principal ou sur le deuxième espace (racine=) s'il dépasse 950 Mo, et le compteur le signale (« allegement », « allegement_espace2 »).
- [x] **Liens vers Cotes & Routes** (fait le 27/11/2026, build.py CR_AERO) : chaque aéroport de la section « S’y rendre » mène à sa fiche https://pablopacaut17-sudo.github.io/cotes-et-routes/#aeroport=<IATA> ; site/liens-aeroports.json donne la ville la plus proche de chaque aéroport à Cotes & Routes.
- [ ] **Sites UNESCO détaillés** (Wikidata P1435 = Q9259) : nom, année d'inscription, critères, lien whc.unesco.org, dans la fiche et la boîte à questions.
- [ ] **Plages et qualité des eaux de baignade** (Agence européenne pour l'environnement, données ouvertes) pour les villes européennes.
- [ ] **Marchés, randonnées et quartiers** (OpenStreetMap : amenity=marketplace, route=hiking, place=suburb|neighbourhood) : compacts (nom + coordonnées), comptés.
- [x] **« Que faire en 2 jours à X »** (fait le 28/11/2026) : static/questions.js, fonction programme() : 1 à 5 jours ou « week-end », lieux à voir de la fiche (incontournables d'abord) regroupés par secteur, parcours de proche en proche, une adresse pour manger près de chaque journée ; aucun fichier ajouté (0 octet de plus sur le site).
- [ ] **Carnet hors ligne** : petit service worker qui garde en cache les fiches mises dans le carnet (sans dépasser quelques Mo dans le navigateur).

## Fait
- [x] 27/11 : comparaison de deux villes (distance, durée de vol, décalage, climat), soleil pour un mois donné, question à voix haute, bouton « Signaler une erreur », sauvegarde hebdomadaire des données (Release GitHub), robots Noms et Chiffres, testeur de questions.

## Robots ajoutés le 27/11/2026 (à vérifier le 28/11)
- [x] **Liens cassés** (robots/robot_liens.py, groupe « decouvertes ») : 4 000 sites de lieux testés par jour ; mort après deux échecs nets à un jour d'écart ; build.py masque les liens morts. État : liens.json.gz (branche donnees-decouvertes).
- Déjà en place avant (pas refaits) : jours fériés (robot_feries.py, Nager.Date) et niveau de sécurité par pays (robot_securite.py, Département d'État américain + lien vers les Conseils aux voyageurs français).
