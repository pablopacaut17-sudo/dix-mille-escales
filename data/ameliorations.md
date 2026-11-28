# Journal des améliorations de Dix Mille Escales

Une entrée par jour (tâche « Amélioration » du matin). Le plus récent en haut.

## 28 novembre 2026
- Compteur : 151 755 144 informations (+400 453 en 24 h, rapport du matin n° 12). Taille du site : 729 Mo sur 1 024 Mo.
- Questions de lecteurs : aucune issue « Question » ouverte.
- Réponses de l'IA : 1 traitée (« Fréquentation gare de Lyon ») → ajoutée à static/reponses.json, resserrée sur le seul chiffre vérifié (≈ 102 millions de voyageurs en 2022, données SNCF « Fréquentation en gares », ODbL) ; les chiffres 2023-2025 de l'IA n'ont pas pu être vérifiés et ont été retirés. Questions sans réponse : 0.
- Robot testeur (issue 13) : « hauteur du Monument de la Paix à Washington » donnait le Washington Monument (169 m). Cause : chercherCelebre() préférait le nom le plus long, et « Washington » comptait alors qu'il ne fait que répéter la ville citée. Correction : les mots du nom égaux au nom de la ville comptent pour rien. Question fixe ajoutée.
- Rapport du matin (issue 12) : robot Chiffres sans journal (réponse Wikidata coupée → JSONDecodeError → plantage). Corrigé en parallèle par la session de Pablo (commit be8b537) ; ma correction a été abandonnée au profit de la sienne lors du rebase.
- Chantier du jour : « Que faire en 2 jours à X » (programme jour par jour calculé dans le navigateur, sans stockage). Ajouté aux exemples de la boîte et aux questions fixes du testeur.
- Deuxième espace : étape 2 (bascule) poussée ce matin par la session de Pablo ; taille à confirmer après la prochaine publication (github.io inaccessible depuis cette tâche).
