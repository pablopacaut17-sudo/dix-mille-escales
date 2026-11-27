# Feuille de route de Dix Mille Escales

Chantiers demandés par Pablo le 27 novembre 2026 (« fais tout »). La tâche « Amélioration » du matin en réalise **un par
jour** (point 3, avant toute autre idée), le teste, puis le coche ici avec la date et une ligne de bilan. Ordre conseillé.

## À faire
- [ ] **Questions sans réponse** : traiter chaque matin `sans_reponse` de data/ia-a-verifier.json (questions que le site n'a pas su traiter) : réponse vérifiée dans static/reponses.json, ou mieux, nouveau type de question dans static/questions.js quand plusieurs se ressemblent. Déplacer chaque élément traité dans `sans_reponse_traites` ([slug, q, d]). *(tous les jours, pas seulement une fois)*
- [ ] **Liens vers Cotes & Routes** : sur chaque fiche de ville, l'aéroport le plus proche (data/airports.json de Cotes & Routes : code IATA, nom, distance) avec un lien vers https://pablopacaut17-sudo.github.io/cotes-et-routes/#accueil et la question « distance <ville> <autre ville> ».
- [ ] **Sites UNESCO détaillés** (Wikidata P1435 = Q9259) : nom, année d'inscription, critères, lien whc.unesco.org, dans la fiche et la boîte à questions.
- [ ] **Plages et qualité des eaux de baignade** (Agence européenne pour l'environnement, données ouvertes) pour les villes européennes.
- [ ] **Marchés, randonnées et quartiers** (OpenStreetMap : amenity=marketplace, route=hiking, place=suburb|neighbourhood) : compacts (nom + coordonnées), comptés.
- [ ] **« Que faire en 2 jours à X »** : programme jour 1 / jour 2 construit dans static/questions.js à partir des lieux incontournables déjà présents (proches les uns des autres le même jour), sans stockage.
- [ ] **Carnet hors ligne** : petit service worker qui garde en cache les fiches mises dans le carnet (sans dépasser quelques Mo dans le navigateur).
- [ ] **Deuxième espace de 1 Go** : quand le dépôt pablopacaut17-sudo.github.io existe (Pablo doit le créer), y déplacer les gros fichiers villes/*/donnees.json.gz (voir l'entrée du 27/11 dans data/ameliorations.md).

## Fait
- [x] 27/11 : comparaison de deux villes (distance, durée de vol, décalage, climat), soleil pour un mois donné, question à voix haute, bouton « Signaler une erreur », sauvegarde hebdomadaire des données (Release GitHub), robots Noms et Chiffres, testeur de questions.
