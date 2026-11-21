#!/usr/bin/env python3
"""
Robot Climat : normales mensuelles de chaque ville (températures, pluie, jours de pluie, ensoleillement),
calculées sur les 2 dernières années complètes de l'archive météo ERA5.
Les villes à moins de 15 km d'une ville déjà calculée reprennent son climat (même maille météo).
Le climat change peu : chaque ville n'est calculée qu'une fois, puis recalculée tous les 2 ans.
Source : Open-Meteo, API d'archive (CC BY 4.0). Usage commercial : clé OPENMETEO_KEY obligatoire.
Les appels d'archive sont « lourds » pour Open-Meteo : on traite peu de villes par nuit.

  python3 robots/robot_climat.py --max-villes 30
  python3 robots/robot_climat.py --demo
"""
import argparse, json, os, time, urllib.parse
from datetime import date, datetime
import commun as c


ANNEES = 2            # années complètes d'archive par ville (Open-Meteo compte les longues périodes comme plusieurs appels)
RAYON_PARTAGE = 25    # km : l'archive ERA5 a des mailles d'environ 25 km, les villes plus proches partagent le même climat


def url(v, debut, fin):
    cle = os.environ.get("OPENMETEO_KEY")
    base = "https://customer-archive-api.open-meteo.com/v1/archive" if cle else "https://archive-api.open-meteo.com/v1/archive"
    q = {"latitude": v["lat"], "longitude": v["lon"], "start_date": debut, "end_date": fin, "timezone": "auto",
         "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,sunshine_duration"}
    if cle:
        q["apikey"] = cle
    return base + "?" + urllib.parse.urlencode(q)


def normales(d):
    mois = [{"tmax": [], "tmin": [], "pluie": {}, "jp": {}, "soleil": []} for _ in range(12)]
    for i, jour in enumerate(d["time"]):
        an, m = jour[:4], int(jour[5:7]) - 1
        x = mois[m]
        if d["temperature_2m_max"][i] is not None:
            x["tmax"].append(d["temperature_2m_max"][i]); x["tmin"].append(d["temperature_2m_min"][i])
        p = d["precipitation_sum"][i] or 0
        x["pluie"][an] = x["pluie"].get(an, 0) + p
        x["jp"][an] = x["jp"].get(an, 0) + (1 if p >= 1 else 0)
        if d["sunshine_duration"][i] is not None:
            x["soleil"].append(d["sunshine_duration"][i] / 3600)
    moy = lambda l: round(sum(l) / len(l), 1) if l else None
    return [{"tmax": moy(x["tmax"]), "tmin": moy(x["tmin"]), "pluie_mm": round(moy(list(x["pluie"].values())) or 0),
             "jours_pluie": round(moy(list(x["jp"].values())) or 0), "soleil_h": moy(x["soleil"])} for x in mois]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-villes", type=int, default=100, help="nombre maximal d'appels à l'archive météo par nuit")
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    V = c.villes()
    an = date.today().year
    debut, fin = f"{an - ANNEES}-01-01", f"{an - 1}-12-31"
    # Index des climats déjà calculés (pour les partager avec les villes voisines)
    calcules = {}
    import os, math
    dossier = os.path.join(c.DATA, "climat")
    if os.path.isdir(dossier):
        for fn in os.listdir(dossier):
            if fn.endswith(".json"):
                calcules[int(fn[:-5])] = None
    par_id = {v["id"]: v for v in V}
    grille = {}
    for i in calcules:
        if i in par_id:
            w = par_id[i]
            grille.setdefault((round(w["lat"] / 0.2), round(w["lon"] / 0.2)), []).append(w)

    def voisin_calcule(v):
        gi, gj = round(v["lat"] / 0.2), round(v["lon"] / 0.2)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for w in grille.get((gi + di, gj + dj), []):
                    d = math.hypot((w["lat"] - v["lat"]) * 110.57, (w["lon"] - v["lon"]) * 111.32 * math.cos(math.radians(v["lat"])))
                    if d < RAYON_PARTAGE:
                        return w
        return None

    if a.demo:
        lot = [v for v in V if v["slug"] in ("lisbonne-pt", "porto-pt", "tokyo-jp")]
    else:
        lot = []
        for v in sorted(V, key=lambda v: ({"phare": 0, "intermediaire": 1, "autre": 2}[v["niveau"]], -v["population"])):
            ancien = c.lire(f"climat/{v['id']}.json")
            if not ancien or (c.maintenant() - datetime.fromisoformat(ancien["date"].replace("Z", "+00:00"))).days > 730:
                lot.append(v)
    ok = ech = partages = appels = 0
    for v in lot:
        if not a.demo:
            w = voisin_calcule(v)
            if w and w["id"] != v["id"]:
                ref = c.lire(f"climat/{w['id']}.json")
                if ref and "mois" in ref:
                    c.ecrire(f"climat/{v['id']}.json", dict(ref, partage_avec=w["nom"]), compact=True)
                    partages += 1
                    continue
            if appels >= a.max_villes:
                continue
            appels += 1
        if a.demo:
            base = [15, 16, 18, 20, 22, 26, 28, 28, 26, 22, 18, 15]
            mois = [{"tmax": t, "tmin": t - 7, "pluie_mm": [100, 90, 60, 65, 50, 15, 5, 5, 30, 95, 110, 110][k],
                     "jours_pluie": [11, 10, 8, 9, 6, 3, 1, 1, 4, 9, 11, 12][k], "soleil_h": [5, 6, 7, 8, 10, 11, 12, 11, 9, 7, 5, 5][k]}
                    for k, t in enumerate(base)]
        else:
            brut = c.http(url(v, debut, fin), delai=60)
            if not brut:
                ech += 1
                continue
            d = json.loads(brut).get("daily")
            if not d:
                ech += 1
                continue
            mois = normales(d)
        c.ecrire(f"climat/{v['id']}.json", {"date": c.horodatage(), "periode": f"{an - ANNEES}-{an - 1}", "mois": mois}, compact=True)
        grille.setdefault((round(v["lat"] / 0.2), round(v["lon"] / 0.2)), []).append(v)
        ok += 1
        print(f"{v['nom']} : normales calculées")
        if not a.demo:
            time.sleep(5)
    c.journal("climat", "ok" if ech == 0 else "partiel", villes_calculees=ok, villes_partagees=partages, echecs=ech, mode="démo" if a.demo else "réel")


if __name__ == "__main__":
    main()
