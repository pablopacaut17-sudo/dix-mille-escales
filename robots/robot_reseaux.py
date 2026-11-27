#!/usr/bin/env python3
"""
Robot Réseaux de transport : pour chaque ville, les réseaux de transport en commun qui la desservent
(bus, tram, métro, trains régionaux, ferries) et les services de vélos ou trottinettes en libre-service.

Source : catalogue mondial de la Mobility Database (MobilityData, organisme à but non lucratif),
fichier https://files.mobilitydatabase.org/feeds_v2.csv, environ 6 000 réseaux dans le monde.
Un réseau est rattaché à une ville si la ville est dans sa zone de desserte (pour les réseaux urbains
et régionaux) ou si la commune indiquée porte le nom de la ville (pour les très grands réseaux).
Les réseaux arrêtés ou en test sont ignorés. Le fichier complet est relu chaque semaine.

  python3 robots/robot_reseaux.py
  python3 robots/robot_reseaux.py --demo
"""
import argparse, csv, io, math, unicodedata
from datetime import datetime
import commun as c

URL = "https://files.mobilitydatabase.org/feeds_v2.csv"
FREQUENCE = 7
MAX_PAR_VILLE = 12
GRANDE_ZONE = 4.0  # degrés² : au-delà, la zone est trop vaste (réseau national) pour rattacher toutes les villes


def simple(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return "".join(ch for ch in t if ch.isalnum())


def col(entete, *noms):
    """Nom réel d'une colonne, quelle que soit la façon dont le catalogue l'écrit (location.country_code, country_code…)."""
    for n in noms:
        for h in entete:
            if h.lower().replace(" ", "_") == n:
                return h
    for n in noms:
        for h in entete:
            if h.lower().endswith(n):
                return h
    return None


def flottant(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def lire_catalogue(brut):
    lignes = list(csv.DictReader(io.StringIO(brut.decode("utf-8-sig"))))
    if not lignes:
        return [], []
    e = list(lignes[0].keys())
    k = {"type": col(e, "data_type"), "pays": col(e, "location.country_code", "country_code"),
         "commune": col(e, "location.municipality", "municipality"), "region": col(e, "location.subdivision_name", "subdivision_name"),
         "exploitant": col(e, "provider"), "nom": col(e, "name"), "statut": col(e, "status"), "officiel": col(e, "is_official"),
         "lat_min": col(e, "location.bounding_box.minimum_latitude", "minimum_latitude"),
         "lat_max": col(e, "location.bounding_box.maximum_latitude", "maximum_latitude"),
         "lon_min": col(e, "location.bounding_box.minimum_longitude", "minimum_longitude"),
         "lon_max": col(e, "location.bounding_box.maximum_longitude", "maximum_longitude"),
         "redirige": col(e, "redirect.id", "redirect"), "licence": col(e, "urls.license", "license")}
    reseaux = []
    for r in lignes:
        g = lambda cle: (r.get(k[cle]) or "").strip() if k.get(cle) else ""
        typ = g("type").lower()
        if typ not in ("gtfs", "gbfs") or g("statut").lower() in ("deprecated", "inactive", "development") or g("redirige"):
            continue
        boite = [flottant(g(x)) for x in ("lat_min", "lat_max", "lon_min", "lon_max")]
        reseaux.append({"type": typ, "pays": g("pays").upper(), "commune": g("commune"), "region": g("region"),
                        "exploitant": g("exploitant")[:90], "nom": g("nom")[:90], "officiel": g("officiel").lower() == "true",
                        "boite": boite if None not in boite else None})
    return reseaux, e


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    p.add_argument("--forcer", action="store_true")
    a = p.parse_args()
    ancien = c.lire("reseaux.json")
    if ancien and not (a.demo or a.forcer) and (c.maintenant() - datetime.fromisoformat(ancien["date"].replace("Z", "+00:00"))).days < FREQUENCE:
        print("Réseaux de transport : données de moins d’une semaine, rien à faire.")
        return
    if a.demo:
        brut = ("id,data_type,location.country_code,location.subdivision_name,location.municipality,provider,name,status,is_official,"
                "location.bounding_box.minimum_latitude,location.bounding_box.maximum_latitude,location.bounding_box.minimum_longitude,"
                "location.bounding_box.maximum_longitude\n"
                "mdb-1,gtfs,PT,Lisboa,Lisboa,Carris,Bus et tram,active,True,38.69,38.80,-9.24,-9.08\n"
                "mdb-2,gbfs,PT,Lisboa,Lisboa,GIRA,Vélos partagés,,,38.70,38.79,-9.22,-9.09\n").encode()
    else:
        brut = c.http(URL, delai=30, timeout=300)
    if not brut:
        c.journal("reseaux", "échec", raison="catalogue de la Mobility Database injoignable")
        print("Catalogue injoignable.")
        return
    reseaux, entete = lire_catalogue(brut)
    V = c.villes()
    par_pays = {}
    for v in V:
        par_pays.setdefault(v["pays"], []).append(v)
    res = {}
    for r in reseaux:
        candidates = par_pays.get(r["pays"], [])
        b = r["boite"]
        surface = (b[1] - b[0]) * (b[3] - b[2]) if b else None
        if b and surface is not None and 0 <= surface <= GRANDE_ZONE:
            villes_r = [v for v in candidates if b[0] - .02 <= v["lat"] <= b[1] + .02 and b[2] - .02 <= v["lon"] <= b[3] + .02]
        else:
            nom = simple(r["commune"])
            villes_r = [v for v in candidates if nom and (simple(v["nom"]) == nom or simple(v.get("nom_local", "")) == nom)]
        for v in villes_r:
            res.setdefault(str(v["id"]), []).append(r)
    sortie = {}
    for vid, liste in res.items():
        vus, garde = set(), []
        for r in sorted(liste, key=lambda r: (r["type"] != "gtfs", not r["officiel"], r["exploitant"])):
            cle = (r["type"], simple(r["exploitant"]))
            if cle in vus or not r["exploitant"]:
                continue
            vus.add(cle)
            garde.append({"t": r["type"], "e": r["exploitant"], "n": r["nom"] if simple(r["nom"]) != simple(r["exploitant"]) else "",
                          "o": 1 if r["officiel"] else 0})
        sortie[vid] = garde[:MAX_PAR_VILLE]
    c.ecrire("reseaux.json", {"date": c.horodatage(), "villes": sortie}, compact=True)
    nb = sum(len(x) for x in sortie.values())
    c.journal("reseaux", "ok", reseaux_lus=len(reseaux), villes_desservies=len(sortie), liens_ville_reseau=nb,
              colonnes=entete[:40], mode="démo" if a.demo else "réel")
    print(f"Réseaux de transport : {len(reseaux)} réseaux actifs, {len(sortie)} villes desservies ({nb} rattachements).")


if __name__ == "__main__":
    main()
