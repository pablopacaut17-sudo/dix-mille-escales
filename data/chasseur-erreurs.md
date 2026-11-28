# Journal du chasseur d'erreurs

Tâche quotidienne : trouver les erreurs du site et les corriger à leur source. Ce journal sert à faire tourner les
vérifications d'un jour à l'autre (pays, types d'information) sans refaire les mêmes.

Outils :
- `robots/robot_controle.py` (workflow `.github/workflows/controle.yml`, chaque jour à 6 h 20 UTC) : contrôles sans IA,
  rapport dans `journal/controle.json` (branche `donnees-controle`). `--demo` vérifie que chaque contrôle trouve son erreur.
- `data/corrections.json` : corrections locales vérifiées à la main quand Wikidata/Wikipédia se trompe (appliquées par build.py).

## Rotation prévue

| Jour | Fiches de villes (≈ 20) | Lieux célèbres (≈ 15) | Questions (≈ 15) |
|---|---|---|---|
| 28/11/2026 | Afrique + Amérique du Sud | monuments très connus (monde) | types variés (visa, heure, climat, prix, langue, hauteur) |
| prochain | Asie (Chine, Inde, Japon, Asie du Sud-Est) | sites antiques (dates av. J.-C.) | jours fériés, change, sécurité |
| ensuite | Europe (hors France) | gares, aéroports, stades (fréquentation, capacité) | comparaisons de villes, alentours |
| ensuite | France et outre-mer | musées, cathédrales (France) | questions de lecteurs (reponses.json) |
| ensuite | Amérique du Nord, Océanie | ponts, tours, gratte-ciel | lieux ambigus, homonymes |

## 2026-11-28 (premier passage)

Vérifié : 20 fiches (Dakar, Abidjan, Nairobi, Addis-Abeba, Casablanca, Tunis, Accra, Lagos, Kinshasa, Johannesbourg, Lima,
Bogota, Quito, Buenos Aires, Montevideo, La Paz, Asunción, Caracas, Antananarivo + Phoenix/Denver), 17 lieux célèbres
(Grande Muraille, Sainte-Sophie, Central Park, Big Ben, porte de Brandebourg, Tower Bridge, Times Square, Chichén Itzá,
Acropole, Notre-Dame de Paris, Opéra de Sydney, Saint-Basile, Taj Mahal, Angkor Vat, Sagrada Família, tours Petronas,
Colisée, statue de la Liberté, pyramide de Khéops), 41 questions sur une copie locale du site (Playwright), l'issue
« Robot testeur » n° 13 (4 réponses à revoir), et toutes les données avec le nouveau robot de contrôle.
Signalements des visiteurs : aucun en attente.

Erreurs trouvées et corrigées :
1. **Climat de 60 210 villes faux** (NASA POWER) : T2M_MAX/T2M_MIN sont les extrêmes du mois, pas les moyennes
   (Calcutta 3 °C la nuit en janvier, Jeddah 48 °C en juillet). Vérifié par une requête de diagnostic depuis GitHub
   (T2M_MAX_AVG est aussi un extrême). robot_climat calcule maintenant moyenne ± écart jour/nuit / 2 (T2M, T2M_RANGE),
   période 2001-2025 ; les anciennes normales sont masquées par build.py et recalculées en priorité (≈ 4 jours).
2. **Page d'accueil : boîte à questions cassée** depuis le déménagement des données vers le deuxième espace
   (« Impossible de charger la fiche ») : templates/accueil.html n'avait pas le relais ESPACE2_JS. Ajouté par build.py.
3. **Altitudes en pieds affichées en mètres** (Phoenix « 1 086 m » au lieu de 331 m ; Highlands Ranch 5 920 m) et
   superficies en miles carrés, nulles ou négatives : robot_encyclopedie convertit les unités Wikidata ; les anciennes
   valeurs des pays concernés sont masquées et relues en priorité ; build.py écarte altitudes > 5 100 m et superficies ≤ 0.
4. **Boîte à questions, lieux célèbres** : « Monument de la Paix à Washington » répondait le Washington Monument
   (mots dans le désordre), « Saut de la Cuve à Épinal » le Saut des Cuves de Gérardmer, « Sa Perda Pinta » introuvable
   (premier mot de 2 lettres), et « hauteur de X à Nuoro » répondait l'altitude de Nuoro. Corrigé dans questions.js.
5. **204 biographies de personnes** affichées comme histoire d'un lieu (statue étiquetée avec le Wikidata de la
   personne : « Gandhi, hauteur 1,64 m ») : écartées par build.py (est_biographie).
6. **Dates avant J.-C. sans signe moins** (Erebouni « 782 », Skara Brae « 3180 »…) : 46 remises au bon signe par build.py.
7. **Dates au siècle près lues comme une année** (Angkor Vat « 1200 » pour XIIᵉ siècle) : robot_histoires ignore
   désormais les dates de précision siècle/millénaire.
8. **Langues des pays** : GeoNames donnait les langues parlées même minoritaires (Qatar « arabe, espagnol »,
   Argentine « anglais, italien ») et l'Afrique du Sud perdait l'anglais : langues officielles du CLDR (robot_villes,
   data/pays.json mis à jour).
9. **22 000 sites web de lieux** non affichés car écrits sans « https:// » : complétés par build.py.
10. **« null »** dans la colonne « Jours de pluie » des fiches construites par fiche.js.
11. Corrections locales (data/corrections.json) : Colisée (construction 70, inauguration 80), statue de la Liberté
    (Bartholdi et Eiffel, pas Viollet-le-Duc), pyramide de Khéops (2560 av. J.-C.), Angkor Vat (1113).
12. Dates « construction · ouverture » affichées séparément (tour Eiffel 1887 · 1889) au lieu d'une « date » ambiguë.

Reste à faire (prochains passages) :
- Vérifier le premier rapport du robot de contrôle (journal/controle.json, branche donnees-controle) et ses fausses alertes.
- Suivre le recalcul du climat NASA (alerte « climat_a_recalculer ») et la relecture des altitudes des États-Unis.
- 16 doublons de villes GeoNames (Kāshān, Texarkana, Benito Juárez…) : choisir quelle fiche garder.
- Dhekelia rattachée au Royaume-Uni (base souveraine à Chypre : c'est juste, alerte à exclure du contrôle).
- ≈ 970 résumés Wikipédia qui finissent sans point (coupés ?) : voir comment robot_encyclopedie les découpe.
- Dates de précision siècle déjà enregistrées (avant la correction du robot) : repérer les années rondes suspectes.
- Formalités : « eta » pour la Côte d'Ivoire (passeport français) à vérifier sur France Diplomatie.
- Prix estimés (café « ≈ 2 € » à Lisbonne) : méthode d'estimation à revoir.
