# Feuille de route de Dix Mille Escales

Chantiers demandés par Pablo le 27 novembre 2026 (« fais tout »). La tâche « Amélioration » du matin en réalise **un par
jour** (point 3, avant toute autre idée), le teste, puis le coche ici avec la date et une ligne de bilan. Ordre conseillé.

## À faire
- [ ] **Questions sans réponse** : traiter chaque matin `sans_reponse` de data/ia-a-verifier.json (questions que le site n'a pas su traiter) : réponse vérifiée dans static/reponses.json, ou mieux, nouveau type de question dans static/questions.js quand plusieurs se ressemblent. Déplacer chaque élément traité dans `sans_reponse_traites` ([slug, q, d]). *(tous les jours, pas seulement une fois)*
- [x] **Deuxième espace de 1 Go** (fait le 28/11/2026) : build.py (preparer_espace2) copie lieux.json.gz et donnees.json.gz des villes dans espace2/, robots.yml les pousse sur la branche espace2, le dépôt pablopacaut17-sudo.github.io les publie toutes les heures si nouvelle version (publier.yml) sous https://pablopacaut17-sudo.github.io/dme-donnees/. Le navigateur lit d'abord cette adresse, avec repli sur l'ancienne (ESPACE2_JS dans tetes()). Résultat : site principal 869 → 128 Mo, deuxième espace 601 Mo (taille réelle, du --apparent-size).
- [x] **Allègement → déplacement** (fait le 28/11/2026) : les gros fichiers sont déplacés vers le deuxième espace au lieu d'être réduits ; alleger() ne sert plus qu'en dernier recours, sur le site principal ou sur le deuxième espace (racine=) s'il dépasse 950 Mo, et le compteur le signale (« allegement », « allegement_espace2 »).
- [x] **Liens vers Cotes & Routes** (fait le 27/11/2026, build.py CR_AERO) : chaque aéroport de la section « S’y rendre » mène à sa fiche https://pablopacaut17-sudo.github.io/cotes-et-routes/#aeroport=<IATA> ; site/liens-aeroports.json donne la ville la plus proche de chaque aéroport à Cotes & Routes.
- [x] **Sites UNESCO détaillés** (fait le 28/11/2026) : robot_encyclopedie.py lit l'année d'inscription (qualificatif P580), les critères (P2614) et l'identifiant UNESCO (P757 → lien whc.unesco.org/fr/list/N) → unesco_details ; repli sur la liste simple si la requête échoue. Affiché dans la fiche (build.py unesco_li, fiche.js) et la boîte à questions. Les fiches se complètent au fil des passages du robot.
- [~] **Plages et qualité des eaux de baignade** : plages et baignades affichées et interrogeables (fait le 28/11/2026). Reste la qualité de l'eau : source trouvée, service cartographique de l'Agence européenne pour l'environnement (water.discomap.eea.europa.eu/arcgis/rest/services/BathingWater/BathingWater_Dyna_WM/MapServer, couche des sites, 2 000 résultats par page ; données des États membres) : nouveau robot à écrire et tester depuis GitHub Actions (réseau), par la tâche Amélioration.
- [x] **Marchés, randonnées, quartiers et sport** (fait le 28/11/2026) : robot_lieux.py collecte aussi place=suburb|neighbourhood|quarter, route=hiking dans la ville, shop=sports|outdoor|bicycle, leisure=sports_centre|fitness_centre|swimming_pool|stadium, sport=climbing, amenity=bicycle_rental (lieux privés écartés) ; build.py → donnees plages, marches, randonnees, sport, quartiers (listes compactes + nombre) ; section « Plages, marchés, randonnées, sport et quartiers » dans la fiche ; questions « randonnées à X », « magasin de sport à X », « quartiers de X ». Les adresses de sport ont leur propre quota (30) dans lieux.json.gz. Visible à mesure que robot_lieux repasse sur les villes.
- [x] **« Que faire en 2 jours à X »** (fait le 28/11/2026) : static/questions.js, fonction programme() : 1 à 5 jours ou « week-end », lieux à voir de la fiche (incontournables d'abord) regroupés par secteur, parcours de proche en proche, une adresse pour manger près de chaque journée ; aucun fichier ajouté (0 octet de plus sur le site).
- [x] **Carnet hors ligne** (fait le 28/11/2026) : static/sw.js copié à la racine du site ; carnet.js l'enregistre et lui demande de garder la page, donnees.json.gz et lieux.json.gz (site et deuxième espace) de chaque ville mise dans le carnet ; sans réseau, ces fiches s'ouvrent depuis le cache ; page de secours pour les autres.
- [x] **Autour de mon hôtel** (fait le 28/11/2026) : « restaurants dans un rayon de 1 km autour de l'hôtel X / du centre de Bordeaux / de moi » (questions.js rayonQ/autourDe : lieux de la fiche à vol d'oiseau, par rubrique, minutes à pied, horaires lisibles ; « moi » = position du téléphone si autorisée).
- [x] **Horaires lisibles** (fait le 28/11/2026) : « horaires Intersport Chalon-sur-Saône » → horaires OpenStreetMap traduits (« lun.-sam. 9 h 30-19 h ; dim. fermé »).
- [x] **« Ce que vous pouvez faire ici »** (fait le 28/11/2026) : bloc d'exemples cliquables sur l'accueil (templates/accueil.html, #mode-emploi).

## Regard du voyageur (à relire chaque matin par la tâche Amélioration)
Chaque matin, la tâche Amélioration se met à la place d'un touriste (famille, sportif, petit budget, personne âgée ou à mobilité réduite, voyage d'affaires), ajoute ici au moins une idée nouvelle de ce qui lui manque, puis réalise la première idée non cochée (demande de Pablo du 28/11/2026 : « que le site s'améliore en continu sans que je donne les idées »). Idées notées le 28/11/2026, à traiter une par une, du plus utile au moins utile :
- [ ] Qualité des eaux de baignade (voir plus haut).
- [ ] Accessibilité : lieux accessibles en fauteuil (déjà dans les données : champ « fauteuil ») mis en avant, question « accessible en fauteuil à X ».
- [ ] Avec des enfants : aires de jeux (leisure=playground), parcs, zoos, aquariums ; question « que faire avec des enfants à X ».
- [ ] Petit budget : musées gratuits (fee=no), points d'eau potable (amenity=drinking_water), toilettes publiques (amenity=toilets).
- [ ] Ouvert maintenant / dimanche : à partir des horaires OpenStreetMap (« restaurants ouverts maintenant à X »).
- [ ] Wi-Fi et recharge : cafés avec internet_access=wlan, bornes de recharge pour véhicules électriques (amenity=charging_station).
- [ ] Sécurité au quotidien : pharmacies de garde non disponibles en données ouvertes partout ; à vérifier pays par pays.
- [ ] Événements datés (concerts, marchés de Noël) : chercher une source ouverte fiable.

## Fait
- [x] 27/11 : comparaison de deux villes (distance, durée de vol, décalage, climat), soleil pour un mois donné, question à voix haute, bouton « Signaler une erreur », sauvegarde hebdomadaire des données (Release GitHub), robots Noms et Chiffres, testeur de questions.

## Robots ajoutés le 27/11/2026 (à vérifier le 28/11)
- [x] **Liens cassés** (robots/robot_liens.py, groupe « decouvertes ») : 4 000 sites de lieux testés par jour ; mort après deux échecs nets à un jour d'écart ; build.py masque les liens morts. État : liens.json.gz (branche donnees-decouvertes).
- Déjà en place avant (pas refaits) : jours fériés (robot_feries.py, Nager.Date) et niveau de sécurité par pays (robot_securite.py, Département d'État américain + lien vers les Conseils aux voyageurs français).
