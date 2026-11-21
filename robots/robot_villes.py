#!/usr/bin/env python3
"""
Robot Villes : fabrique la liste des 10 000 villes du guide (data/villes.json) et la fiche de chaque
pays (data/pays.json), à partir des fichiers officiels de GeoNames (CC BY 4.0).
Il ne tourne qu'une fois : si data/villes.json existe déjà, il ne fait rien (les adresses des pages
restent ainsi stables). Pour forcer une reconstruction : --forcer.
Noms des pays, langues et monnaies en français : bibliothèque Babel (données Unicode CLDR).

  pip install babel
  python3 robots/robot_villes.py
"""
import argparse, io, os, re, unicodedata, zipfile
import commun as c

VILLES_URL = "https://download.geonames.org/export/dump/cities15000.zip"
PAYS_URL = "https://download.geonames.org/export/dump/countryInfo.txt"
NB = 10000
PHARES = {1261481, 1273874, 1279259} | set([148730, 184745, 250441, 264371, 281184, 290030, 292223, 292968, 293397, 360630, 498817, 524901, 658225, 745044, 756135, 993800, 1153671, 1269515, 1273294, 1275339, 1283240, 1566083, 1581130, 1609350, 1642911, 1645528, 1668341, 1701668, 1735161, 1796236, 1816670, 1819729, 1835848, 1850147, 1853909, 1857910, 1880252, 2147714, 2158177, 2193733, 2253354, 2267057, 2464470, 2509954, 2510911, 2542997, 2548885, 2553604, 2618425, 2643743, 2650225, 2657896, 2660646, 2673730, 2735943, 2759794, 2761369, 2800866, 2800931, 2867714, 2950159, 2964574, 2988507, 2990440, 2995469, 2996944, 3031582, 3054643, 3067696, 3094802, 3117735, 3128760, 3143244, 3164603, 3169070, 3172394, 3173435, 3176959, 3190261, 3369157, 3413829, 3435910, 3448439, 3451190, 3530597, 3531673, 3553478, 3687238, 3688689, 3871336, 3936456, 3941584, 4140963, 4164138, 4335045, 4887398, 4930956, 5128581, 5368361, 5391959, 5506956, 6077243, 6167865, 6173331, 6325494])
# Villes de moins de 15 000 habitants ajoutées à la main (absentes du fichier GeoNames utilisé)
EXTRAS = [{"id": 99000001, "nom": "Manali", "nom_local": "Manali", "pays": "IN", "lat": 32.2432, "lon": 77.1892, "population": 8096,
           "fuseau": "Asia/Kolkata", "niveau": "phare", "slug": "manali-in", "alts": ["Manāli", "Old Manali"],
           "qid_recherche": "Manali, Himachal Pradesh"}]
ALTS_EN_PLUS = {1273874: ["Cochin"]}
NOMS_FR = {1816670: 'Pékin', 1809858: 'Canton', 1566083: 'Hô Chi Minh-Ville', 1275339: 'Bombay', 3530597: 'Mexico', 524901: 'Moscou', 1185241: 'Dacca', 1835848: 'Séoul', 360630: 'Le Caire', 1799962: 'Nankin', 2643743: 'Londres', 5128581: 'New York', 1581130: 'Hanoï', 3688689: 'Bogota', 98182: 'Bagdad', 112931: 'Téhéran', 1880252: 'Singapour', 498817: 'Saint-Pétersbourg', 361058: 'Alexandrie', 3871336: 'Santiago du Chili', 3369157: 'Le Cap', 1275004: 'Calcutta', 1298824: 'Rangoun', 108410: 'Riyad', 344979: 'Addis-Abeba', 292223: 'Dubaï', 703448: 'Kiev', 2507480: 'Alger', 587084: 'Bakou', 3469058: 'Brasilia', 3553478: 'La Havane', 170063: 'Alep', 1512569: 'Tachkent', 2911298: 'Hambourg', 276781: 'Beyrouth', 683506: 'Bucarest', 292968: 'Abou Dabi', 756135: 'Varsovie', 2761369: 'Vienne', 3128760: 'Barcelone', 1701668: 'Manille', 4560349: 'Philadelphie', 170654: 'Damas', 1283240: 'Katmandou', 2548885: 'Fès', 2618425: 'Copenhague', 616052: 'Kentron', 611717: 'Tbilissi', 2800866: 'Bruxelles', 2542997: 'Marrakech', 281184: 'Jérusalem', 3687238: 'Carthagène', 2028462: 'Oulan-Bator', 2509954: 'Valence', 3094802: 'Cracovie', 2510911: 'Séville', 1645528: 'Denpasar (Bali)', 264371: 'Athènes', 2925533: 'Francfort', 1216265: 'Samarcande', 3176219: 'Gênes', 2267057: 'Lisbonne', 2650225: 'Édimbourg', 3099434: 'Gdansk', 293397: 'Tel-Aviv', 3941584: 'Cuzco', 2657896: 'Zurich', 3703443: 'Panama', 4335045: 'La Nouvelle-Orléans', 2660646: 'Genève', 146268: 'Nicosie', 2661604: 'Bâle', 4744091: 'Alexandrie', 2661552: 'Berne', 3413829: 'Reykjavik', 2800931: 'Bruges', 2449067: 'Tombouctou', 3164603: 'Venise'}


def slugifier(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "ville"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--forcer", action="store_true")
    a = p.parse_args()
    if c.lire("villes.json") and not a.forcer:
        print("La liste des villes existe déjà : rien à faire.")
        return
    try:
        from babel import Locale
        fr = Locale("fr")
    except ImportError:
        raise SystemExit("Installez d’abord Babel : pip install babel")

    brut = c.http(VILLES_URL, timeout=300)
    if not brut:
        raise SystemExit("GeoNames injoignable : réessayez plus tard.")
    texte = zipfile.ZipFile(io.BytesIO(brut)).read("cities15000.txt").decode("utf-8")
    villes = []
    latin = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿĀ-ž' .\-]+$")
    for ligne in texte.splitlines():
        x = ligne.split("\t")
        if len(x) < 18:
            continue
        gid = int(x[0])
        villes.append({"id": gid, "nom_local": x[1], "pays": x[8], "lat": round(float(x[4]), 4), "lon": round(float(x[5]), 4),
                       "population": int(x[14] or 0), "fuseau": x[17],
                       "alts_brut": [n for n in x[3].split(",") if n and latin.match(n) and len(n) < 28]})
    villes.sort(key=lambda v: -v["population"])
    garder = villes[:NB]
    ids = {v["id"] for v in garder}
    garder += [v for v in villes[NB:] if v["id"] in PHARES and v["id"] not in ids]
    while len(garder) > NB:  # place pour les villes phares plus petites : on retire les plus petites des autres
        for i in range(len(garder) - 1, -1, -1):
            if garder[i]["id"] not in PHARES:
                del garder[i]
                break
    garder.sort(key=lambda v: -v["population"])
    sortie, pris, rang = [], set(), 0
    for v in garder:
        nom = NOMS_FR.get(v["id"], v["nom_local"])
        if v["id"] in PHARES:
            niveau = "phare"
        else:
            rang += 1
            niveau = "intermediaire" if rang <= 1000 else "autre"
        slug = slugifier(nom) + "-" + v["pays"].lower()
        if slug in pris:
            slug += "-" + str(v["id"])
        pris.add(slug)
        alts = [n for n in v["alts_brut"] if n not in (nom, v["nom_local"])][:5]
        if nom != v["nom_local"]:
            alts = [v["nom_local"]] + alts
        sortie.append({"id": v["id"], "nom": nom, "nom_local": v["nom_local"], "pays": v["pays"], "lat": v["lat"], "lon": v["lon"],
                       "population": v["population"], "fuseau": v["fuseau"], "niveau": niveau, "slug": slug, "alts": alts})
    for v in sortie:
        v["alts"] = ALTS_EN_PLUS.get(v["id"], []) + v["alts"]
    for x in EXTRAS:
        if not any(v["slug"] == x["slug"] for v in sortie):
            for i in range(len(sortie) - 1, -1, -1):
                if sortie[i]["niveau"] == "autre":
                    del sortie[i]
                    break
            sortie.append(x)
    c.ecrire("villes.json", sortie, compact=True)

    brut = c.http(PAYS_URL)
    if not brut:
        raise SystemExit("Liste des pays injoignable : relancez le robot.")
    pays = {}
    for ligne in brut.decode("utf-8").splitlines():
        if ligne.startswith("#") or not ligne.strip():
            continue
        x = ligne.split("\t")
        cc, monnaie = x[0], x[10]
        langues = []
        for l in x[15].split(","):
            n = fr.languages.get(l.split("-")[0])
            if n and n not in langues:
                langues.append(n)
        pays[cc] = {"nom": fr.territories.get(cc, x[4]), "nom_en": x[4], "iso3": x[1], "continent": x[8], "capitale": x[5],
                    "monnaie": monnaie, "monnaie_nom": (fr.currencies.get(monnaie) or x[11]) if monnaie else "",
                    "langues": langues[:3], "indicatif": ("+" + x[12].lstrip("+")) if x[12] else "",
                    "superficie_km2": float(x[6]) if x[6] else None}
    c.ecrire("pays.json", pays)
    c.journal("villes", "ok", villes=len(sortie), pays=len(pays))
    print(f"{len(sortie)} villes et {len(pays)} pays enregistrés.")


if __name__ == "__main__":
    main()
