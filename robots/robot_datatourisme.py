#!/usr/bin/env python3
"""
Robot DATAtourisme : l'offre touristique officielle des villes françaises (métropole et outre-mer).

Source : DATAtourisme, base nationale des données touristiques (offices de tourisme, agences
départementales et comités régionaux du tourisme), Licence Ouverte 2.0, exports CSV par région publiés
chaque jour sur data.gouv.fr (jeu « datatourisme-la-plateforme-nationale-des-donnees-touristiques »).

Pour chaque ville française du guide, le robot garde :
  - les sites et activités : musées, monuments et patrimoine, parcs et sites naturels, loisirs et visites
    (pas les restaurants ni les hôtels, déjà fournis par OpenStreetMap) ;
  - les événements à venir (fêtes, concerts, expositions, marchés…), dans les 6 prochains mois.
Un lieu est rattaché à la ville du guide la plus proche, à moins de 8 km.
Les colonnes des fichiers sont reconnues automatiquement ; la liste des colonnes lues est notée dans le journal.

  python3 robots/robot_datatourisme.py
  python3 robots/robot_datatourisme.py --demo
"""
import argparse, csv, io, json, math, re, sys, unicodedata
from datetime import date, datetime, timedelta
import commun as c

JEU = "datatourisme-la-plateforme-nationale-des-donnees-touristiques"
API = f"https://www.data.gouv.fr/api/1/datasets/{JEU}/"
RAYON_KM = 8
NOMBRE = {"phare": (40, 25), "intermediaire": (30, 20), "autre": (14, 10)}  # (sites, événements) gardés par ville
PAYS_FR = {"FR", "GP", "MQ", "GF", "RE", "YT", "PM", "BL", "MF", "NC", "PF", "WF"}
CATEGORIES = [  # (catégorie du guide, mots du type DATAtourisme) — dans l'ordre de priorité
    ("Musées et expositions", ("museum", "musee", "exposition", "galerie", "interpretation", "ecomusee")),
    ("Patrimoine", ("monument", "patrimoine", "chateau", "eglise", "cathedrale", "abbaye", "religious", "castle", "remarkable",
                    "historique", "archaeolog", "fort", "citadelle", "chapelle", "basilique", "pont", "moulin", "phare")),
    ("Nature et jardins", ("parc", "parkandgarden", "naturalpark", "jardin", "garden", "naturel", "natural", "plage", "beach", "lac", "cascade", "grotte",
                           "point_de_vue", "pointofview", "viewpoint", "foret", "reserve")),
    ("Visites et loisirs", ("visite", "tour", "loisir", "leisure", "sport", "activite", "activity", "zoo", "aquarium", "attraction",
                            "degustation", "cave", "vineyard", "nautique", "randonnee", "itineraire", "cinema", "theatre", "spectacle",
                            "entertainment", "culturalsite", "culturelle")),
]
EVENEMENTS = ("entertainmentandevent", "event", "evenement", "manifestation", "fete", "festival", "concert", "fma", "marche",
              "salon", "foire", "competition", "sportsevent", "culturalevent", "saleevent", "socialevent")
EXCLUS = ("restaurant", "foodestablishment", "accommodation", "hebergement", "hotel", "camping", "gite", "chambredhote",
          "rentalaccommodation", "bar", "store", "commerce", "service", "boutique", "localbusiness", "touristinformation",
          "office", "parking", "toilette", "publicservice")
DATE = re.compile(r"(20\d\d)-(\d\d)-(\d\d)")


def simple(t):
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()


def col(entete, *mots, sauf=()):
    """Première colonne dont le nom contient l'un des mots (dans l'ordre des mots)."""
    for m in mots:
        for h in entete:
            s = simple(h).replace(" ", "_")
            if m in s and not any(x in s for x in sauf):
                return h
    return None


def flottant(x):
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None


def grille(villes):
    g = {}
    for v in villes:
        g.setdefault((int(v["lat"] * 10), int(v["lon"] * 10)), []).append(v)
    return g


def plus_proche(g, lat, lon):
    meilleur, dmin = None, RAYON_KM
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for v in g.get((int(lat * 10) + di, int(lon * 10) + dj), []):
                d = math.hypot((v["lat"] - lat) * 110.57, (v["lon"] - lon) * 111.32 * math.cos(math.radians(lat)))
                if d < dmin:
                    meilleur, dmin = v, d
    return meilleur, dmin


def nettoyer(t, n):
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t or "")).strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def categorie(types):
    s = simple(types).replace(" ", "")
    if any(x in s for x in EVENEMENTS):
        return "evenement"
    exclu = any(x in s for x in EXCLUS)
    for i, (nom, mots) in enumerate(CATEGORIES):
        if exclu and i == len(CATEGORIES) - 1:
            return None  # restaurant, hôtel, commerce, office de tourisme… : déjà couverts ailleurs
        if any(m in s for m in mots):
            return nom
    return None


def ressources():
    brut = c.http(API, delai=30)
    if not brut:
        return []
    d = json.loads(brut)
    out = []
    for r in d.get("resources", []):
        titre = (r.get("title") or "").lower()
        if titre.startswith("datatourisme-reg-") and titre.endswith(".csv"):
            out.append((titre, f"https://www.data.gouv.fr/api/1/datasets/r/{r['id']}"))
    return out


def traiter(brut, g, res, aujourdhui, limite, stats):
    texte = brut.decode("utf-8-sig", errors="replace")
    echantillon = texte[:5000]
    sep = max((",", ";", "\t"), key=lambda s: echantillon.splitlines()[0].count(s) if echantillon else 0)
    lecteur = csv.DictReader(io.StringIO(texte), delimiter=sep)
    e = lecteur.fieldnames or []
    stats["colonnes"] = e[:40]
    k = {"nom": col(e, "nom_du_poi", "nom", "label", "name", "titre", sauf=("fichier", "producteur", "createur", "commune")),
         "types": col(e, "categories_de_poi", "categorie", "type", sauf=("producteur",)),
         "lat": col(e, "latitude", "lat"), "lon": col(e, "longitude", "lon"),
         "adresse": col(e, "adresse_postale", "adresse", "street", "rue"),
         "commune": col(e, "commune", "city", "ville"),
         "desc": col(e, "description", "comment", "resume"),
         "site": col(e, "site_web", "url", "web", "contacts", sauf=("uri", "identifiant", "fichier")),
         "periodes": col(e, "periode", "date", "startdate", sauf=("mise_a_jour", "maj", "lastupdate", "creation")),
         "fin": col(e, "date_de_fin", "enddate", "fin")}
    stats["correspondance"] = {x: y for x, y in k.items() if y}
    if not (k["nom"] and k["lat"] and k["lon"]):
        stats["fichiers_illisibles"] = stats.get("fichiers_illisibles", 0) + 1
        return
    for r in lecteur:
        stats["lignes"] = stats.get("lignes", 0) + 1
        lat, lon = flottant(r.get(k["lat"])), flottant(r.get(k["lon"]))
        nom = nettoyer(r.get(k["nom"]), 120)
        if lat is None or lon is None or not nom:
            continue
        cat = categorie(r.get(k["types"], "") if k["types"] else "")
        if cat is None:
            continue
        v, d = plus_proche(g, lat, lon)
        if not v:
            continue
        x = {"n": nom}
        adr = nettoyer(r.get(k["adresse"], "") if k["adresse"] else "", 120)
        if adr:
            x["a"] = adr
        if k["site"]:
            site = re.search(r"https?://[^\s<>|#\"]+", r.get(k["site"]) or "")
            if site:
                x["w"] = site.group(0)[:200]
        if k["desc"]:
            dsc = nettoyer(r.get(k["desc"]), 240)
            if dsc:
                x["d"] = dsc
        x["km"] = round(d, 1)
        cible = res.setdefault(str(v["id"]), {"sites": [], "evenements": []})
        if cat == "evenement":
            brut_dates = " ".join(r.get(h, "") for h in (k["periodes"], k["fin"]) if h)
            dates = sorted({m.group(0) for m in DATE.finditer(brut_dates)})
            avenir = [x_ for x_ in dates if aujourdhui <= x_ <= limite]
            fin = dates[-1] if dates else ""
            if not dates or fin < aujourdhui:
                continue  # événement passé ou sans date
            x["du"] = avenir[0] if avenir else max(dates[0], aujourdhui)
            if x["du"] > limite:
                continue
            x["au"] = fin
            cible["evenements"].append(x)
        else:
            x["c"] = cat
            cible["sites"].append(x)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    V = [v for v in c.villes() if v["pays"] in PAYS_FR]
    g = grille(V)
    niveau = {str(v["id"]): v["niveau"] for v in V}
    aujourdhui = date.today().isoformat()
    limite = (date.today() + timedelta(days=183)).isoformat()
    res, stats = {}, {}
    if a.demo:
        fichiers = [("datatourisme-reg-demo.csv", None)]
    else:
        fichiers = ressources()
        if not fichiers:
            c.journal("datatourisme", "échec", raison="liste des fichiers DATAtourisme introuvable sur data.gouv.fr")
            print("Liste des fichiers introuvable.")
            return
    lus = 0
    for titre, url in fichiers:
        if a.demo:
            v = next(x for x in V if x["nom"] == "Lyon") if any(x["nom"] == "Lyon" for x in V) else V[0]
            brut = ("Nom_du_POI,Categories_de_POI,Latitude,Longitude,Adresse_postale,Code_postal_et_commune,Periodes_regroupees,"
                    "Description,Contacts_du_POI\n"
                    f"Musée d’exemple,https://www.datatourisme.fr/ontology/core#Museum|CulturalSite,{v['lat']},{v['lon']},1 rue X,69001 {v['nom']},,"
                    "Un musée d’exemple.,https://exemple.fr\n"
                    f"Fête d’exemple,https://www.datatourisme.fr/ontology/core#EntertainmentAndEvent,{v['lat']},{v['lon']},,,"
                    f"{(date.today() + timedelta(days=10)).isoformat()}<>{(date.today() + timedelta(days=12)).isoformat()},Une fête.,\n").encode()
        else:
            brut = c.http(url, delai=30, timeout=600)
        if not brut:
            print(f"  {titre} : téléchargement impossible")
            continue
        try:
            traiter(brut, g, res, aujourdhui, limite, stats)
            lus += 1
            print(f"  {titre} : lu ({stats.get('lignes', 0)} lignes au total)")
        except Exception as err:  # un fichier abîmé ne doit pas arrêter le robot
            print(f"  {titre} : {err}", file=sys.stderr)
    nb_sites = nb_evts = 0
    for vid, d in res.items():
        n_sites, n_evts = NOMBRE[niveau[vid]]
        vus, sites = set(), []
        for x in sorted(d["sites"], key=lambda x: ([n for n, _ in CATEGORIES].index(x["c"]), not x.get("d"), x["km"])):
            cle = simple(x["n"])
            if cle not in vus:
                vus.add(cle)
                sites.append(x)
        vus, evts = set(), []
        for x in sorted(d["evenements"], key=lambda x: (x["du"], x["km"])):
            cle = (simple(x["n"]), x["du"])
            if cle not in vus:
                vus.add(cle)
                evts.append(x)
        d["sites"], d["evenements"] = sites[:n_sites], evts[:n_evts]
        nb_sites += len(d["sites"])
        nb_evts += len(d["evenements"])
    if lus:
        c.ecrire_gz("datatourisme.json.gz", {"date": c.horodatage(), "villes": res})
    c.journal("datatourisme", "ok" if lus == len(fichiers) else ("partiel" if lus else "échec"), fichiers_lus=lus,
              fichiers=len(fichiers), villes=len(res), sites=nb_sites, evenements=nb_evts, lignes=stats.get("lignes", 0),
              colonnes=stats.get("colonnes", []), correspondance=stats.get("correspondance", {}), mode="démo" if a.demo else "réel")
    print(f"DATAtourisme : {nb_sites} sites et {nb_evts} événements pour {len(res)} villes ({lus}/{len(fichiers)} fichiers lus).")


if __name__ == "__main__":
    main()
