#!/usr/bin/env python3
"""
Robot Aéroports : pour chaque ville du guide, les aéroports avec vols réguliers les plus proches (jusqu'à 3, à moins de 250 km),
avec leur code, leur distance et le temps de trajet estimé.
Source : OurAirports (domaine public). Recalculé une fois par mois.

  python3 robots/robot_aeroports.py
  python3 robots/robot_aeroports.py --demo
"""
import argparse, csv, io, math
from datetime import datetime
import commun as c

SOURCE = "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv"
RAYON = 250


def dist(a, b):
    t = math.pi / 180
    x = math.sin((b[0] - a[0]) * t / 2) ** 2 + math.cos(a[0] * t) * math.cos(b[0] * t) * math.sin((b[1] - a[1]) * t / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(x))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    p.add_argument("--forcer", action="store_true")
    a = p.parse_args()
    ancien = c.lire("aeroports_meta.json")
    if ancien and not a.forcer and not a.demo and (c.maintenant() - datetime.fromisoformat(ancien["date"].replace("Z", "+00:00"))).days < 30:
        print("Aéroports à jour (moins de 30 jours) : rien à faire.")
        return
    if a.demo:
        texte = ('"type","name","latitude_deg","longitude_deg","iso_country","municipality","scheduled_service","iata_code"\n'
                 '"large_airport","Humberto Delgado Airport",38.7813,-9.1359,"PT","Lisbon","yes","LIS"\n'
                 '"large_airport","Francisco Sá Carneiro Airport",41.2481,-8.6814,"PT","Porto","yes","OPO"\n')
    else:
        brut = c.http(SOURCE, timeout=180)
        if not brut:
            c.journal("aeroports", "echec", raison="OurAirports injoignable")
            raise SystemExit("Source injoignable : données précédentes conservées.")
        texte = brut.decode("utf-8")
    aeros = []
    for l in csv.DictReader(io.StringIO(texte)):
        if l["type"] in ("large_airport", "medium_airport") and l.get("scheduled_service") == "yes" and l.get("iata_code"):
            aeros.append((float(l["latitude_deg"]), float(l["longitude_deg"]), l["iata_code"], l["name"], l["type"] == "large_airport", l.get("municipality", "")))
    grille = {}
    for x in aeros:
        grille.setdefault((int(x[0] // 2), int(x[1] // 2)), []).append(x)
    res = {}
    for v in c.villes():
        gi, gj = int(v["lat"] // 2), int(v["lon"] // 2)
        cand = []
        for di in (-2, -1, 0, 1, 2):
            for dj in (-3, -2, -1, 0, 1, 2, 3):
                for x in grille.get((gi + di, gj + dj), []):
                    d = dist((v["lat"], v["lon"]), (x[0], x[1]))
                    if d <= RAYON:
                        cand.append((d - (25 if x[4] else 0), d, x))  # les grands aéroports passent devant à distance égale
        cand.sort()
        if cand:
            res[str(v["id"])] = [[x[2], x[3], round(d), 1 if x[4] else 0, x[5]] for _, d, x in cand[:3]]
    c.ecrire_gz("aeroports.json.gz", res)
    c.ecrire("aeroports_meta.json", {"date": c.horodatage(), "aeroports": len(aeros), "villes": len(res)})
    c.journal("aeroports", "ok", aeroports=len(aeros), villes_avec_aeroport=len(res), mode="démo" if a.demo else "réel")
    print(f"Aéroports : {len(aeros)} aéroports, {len(res)} villes en ont au moins un à moins de {RAYON} km.")


if __name__ == "__main__":
    main()
