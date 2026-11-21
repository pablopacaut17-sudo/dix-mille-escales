# Dix Mille Escales

Le guide de voyage des 10 000 plus grandes villes du monde, mis à jour chaque nuit par des robots.

Ce dossier contient **tout le site** : les données des 10 000 villes, les robots, le générateur de pages et la tâche automatique qui fait tourner l’ensemble. Une fois en ligne, vous n’avez plus rien à faire : chaque nuit, les robots collectent de nouvelles données et le site se met à jour tout seul.

---

## Mise en ligne, pas à pas (environ 20 minutes, une seule fois)

Le site sera hébergé gratuitement par **GitHub**, qui fera aussi tourner les robots.

### 1. Créer un compte GitHub

Allez sur https://github.com/signup et créez un compte gratuit. Votre pseudo apparaîtra dans l’adresse du site (par exemple `pablo-pacaut.github.io`).

### 2. Créer le dépôt du projet

1. En haut à droite, cliquez sur **+** puis **New repository**.
2. Nom : `dix-mille-escales`.
3. Choisissez **Public** (nécessaire pour l’hébergement et les robots gratuits).
4. Cochez **Add a README file**, puis **Create repository**.

### 3. Créer les fichiers (copier-coller)

Pour chaque fichier de la liste :

1. Cliquez sur **Add file** puis **Create new file**.
2. Dans la case du nom, collez le chemin du fichier (par exemple `robots/robot_lieux.py`) : les dossiers se créent tout seuls.
3. Collez le code dans la grande zone de texte.
4. Cliquez sur **Commit changes**, puis encore sur **Commit changes**.

Les données (liste des 10 000 villes, pays, visas…) ne sont pas à copier : les robots les fabriquent au premier lancement.

### 4. Autoriser la publication et les robots

1. Onglet **Settings** du dépôt, puis **Pages** dans le menu de gauche : dans **Source**, choisissez **GitHub Actions**.
2. Toujours dans **Settings**, ouvrez **Actions** puis **General** : tout en bas, dans **Workflow permissions**, cochez **Read and write permissions** et enregistrez.

### 5. Lancer la première fois

1. Onglet **Actions**, cliquez sur **Robots et publication** à gauche.
2. Bouton **Run workflow**, puis **Run workflow**.
3. Attendez que les deux étapes passent au vert (de quelques minutes à quelques heures la première fois, selon le nombre de villes explorées).

Votre site est en ligne à l’adresse : `https://VOTRE-PSEUDO.github.io/dix-mille-escales/`

Ensuite, tout se fait seul, chaque nuit.

---

## Ce que font les robots

| Robot | Ce qu’il collecte | Source | Rythme |
|---|---|---|---|
| Climat | Normales mois par mois : températures, pluie, jours de pluie, ensoleillement, meilleurs mois | Open-Meteo (archive ERA5) | 30 villes par nuit, une fois tous les 2 ans par ville |
| Sécurité | Niveau d’alerte de 1 à 4 par pays, bandeau sur les fiches des pays à risque | Département d’État américain | Chaque nuit |
| Formalités | Visa ou non et durée de séjour pour les passeports français, belge, suisse et canadien | Passport Index Data | Chaque nuit |
| Coût de la vie | Niveau des prix comparé à la France, prix estimés (café, repas, transport, hôtel, budget par jour) | Banque mondiale | Chaque nuit |
| Rédaction | « Notre avis » : accroche, raisons d’y aller, conseils d’initiés, erreurs à éviter, programmes 1 et 3 jours | Claude (Anthropic), à partir des données des autres robots | 40 villes phares par nuit, chacune tous les 30 jours |
| Encyclopédie | Histoire, frise des événements, fondation, anciens noms, surnoms, photo, blason, maire, altitude, superficie, patrimoine UNESCO, personnalités nées dans la ville, villes jumelées, sections Wikipédia (histoire, géographie, patrimoine, culture, gastronomie, économie, sport, transports) | Wikidata, Wikipédia, Wikimedia Commons | 300 villes par nuit : phares tous les mois, intermédiaires tous les 3 mois, autres tous les 6 mois |
| Lieux | Monuments, musées, restaurants, cafés, bars, hôtels, boutiques et activités (plages, sports nautiques, parcs d’attractions, golf, ski) dans un cercle urbain d’au moins 7 km pour les villes phares ; sites notables, randonnées et patrimoine mondial dans un rayon de 50 km, avec idées d’excursions | OpenStreetMap | 60 villes par nuit : phares chaque semaine, intermédiaires chaque mois, autres tous les 3 mois |
| Météo | Prévisions à 7 jours et qualité de l’air | Open-Meteo | Chaque nuit, villes phares et intermédiaires |
| Jours fériés | Jours fériés nationaux | Nager.Date | Chaque pays une fois par mois |
| Change | Taux de l’euro | Banque centrale européenne | Chaque nuit |

La page **État des robots** du site (`/etat/`) montre le dernier passage de chaque robot et la couverture des villes.

Au début, la plupart des fiches contiennent seulement les données de base (pays, population, heure, distance, monnaie, langues, villes proches). Elles s’enrichissent au fil des nuits. Avec 60 villes par nuit, les 105 villes phares sont explorées dès les premiers jours, et l’ensemble des 10 000 villes en quelques mois.

---

## Réglages facultatifs

Dans **Settings**, puis **Secrets and variables**, puis **Actions** :

| Réglage | Onglet | Valeur | Effet |
|---|---|---|---|
| `MAX_VILLES` | Variables | par exemple `120` | Nombre de villes explorées par nuit (60 par défaut) |
| `MAX_ENCYCLO` | Variables | par exemple `500` | Nombre de villes enrichies par le robot Encyclopédie par nuit (300 par défaut) |
| `SITE_URL` | Variables | par exemple `https://dixmilleescales.fr` | Active le plan du site pour Google |
| `MAX_CLIMAT` | Variables | par exemple `60` | Villes dont le climat est calculé par nuit (30 par défaut) |
| `ANTHROPIC_API_KEY` | Secrets | votre clé API Claude (console.anthropic.com) | Active le robot Rédaction. Sans clé, il reste inactif et le reste du site fonctionne |
| `CLAUDE_MODEL` | Variables | nom d’un modèle Claude | Modèle utilisé pour la rédaction (par défaut `claude-sonnet-5-5`) |
| `MAX_REDACTION` | Variables | par exemple `105` | Villes rédigées par nuit (40 par défaut) |
| `OPENMETEO_KEY` | Secrets | votre clé Open-Meteo | **Obligatoire dès que le site gagne de l’argent** (publicité, affiliation) : l’API gratuite d’Open-Meteo est réservée aux usages non commerciaux |

**Nom de domaine** : achetez-le chez un registraire (environ 10 € par an), puis dans **Settings**, **Pages**, renseignez **Custom domain** et suivez les indications de GitHub.

---

## Modifier le site

- **Une fiche rédigée à la main** : placez un fichier HTML complet dans `pages/`, nommé comme l’adresse de la ville (par exemple `pages/porto-pt.html`). Il remplace la fiche automatique. C’est le cas de Lisbonne.
- **Le style des pages de villes** : `static/style.css`.
- **La page d’accueil** : `templates/accueil.html`.
- **Le contenu des fiches automatiques** : `build.py`, fonction `page_ville`.

Chaque modification déposée sur GitHub republie le site automatiquement en quelques minutes.

---

## Limites à connaître

- Le serveur public d’OpenStreetMap est partagé : restez raisonnable sur `MAX_VILLES`. Pour aller plus vite, il faudra plus tard un serveur à vous, avec les fichiers OpenStreetMap par pays.
- Les lieux d’OpenStreetMap sont de qualité inégale selon les pays : très complets en Europe, plus minces ailleurs.
- Les données s’accumulent dans le dépôt. Au-delà d’environ 1 Go, il faudra passer à un stockage dédié.
- Les conseils « Notre avis » sont rédigés par IA à partir des données : relisez au moins ceux des villes phares.
- Le niveau de sécurité vient des autorités américaines ; la page renvoie toujours vers les Conseils aux voyageurs du ministère français, qui font foi.
- Le budget est une estimation fondée sur le niveau des prix national, pas sur des relevés en ville.

## Sources et licences

Villes : GeoNames (CC BY 4.0). Histoire et faits : Wikidata (CC0). Textes : Wikipédia (CC BY-SA 4.0). Photos : Wikimedia Commons (licence propre à chaque image). Lieux : © contributeurs OpenStreetMap (ODbL). Météo : Open-Meteo (CC BY 4.0). Jours fériés : Nager.Date. Change : Banque centrale européenne. Visas : Passport Index Data (MIT). Sécurité : U.S. Department of State. Niveau des prix : Banque mondiale (CC BY 4.0). Noms de pays, langues et monnaies : CLDR (Unicode). Ces mentions figurent sur la page « Nos sources » du site et doivent y rester.
