#!/usr/bin/env python3
"""
Robot Climat : normales mensuelles de chaque ville (températures, pluie, jours de pluie, ensoleillement),
calculées sur les 2 dernières années complètes de l'archive météo ERA5.
Les villes à moins de 15 km d'une ville déjà calculée reprennent son climat (même maille météo).
Le climat change peu : chaque ville n'est calculée qu'une fois, puis recalculée tous les 2 ans.
Source : NASA POWER (normales mensuelles sur 30 ans, données ouvertes de la NASA, sans restriction d’usage).
Les appels d'archive sont « lourds » pour Open-Meteo : on traite peu de villes par nuit.

  python3 robots/robot_climat.py --max-villes 30
  python3 robots/robot_climat.py --demo
"""
import argparse, json, os, time, urllib.parse
from datetime import date, datetime
import commun as c


ANNEES = 2            # (ancienne source Open-Meteo, gardée en secours)
RAYON_PARTAGE = 25    # km : les villes plus proches partagent le même climat (mailles de la NASA d'environ 50 km)
POWER = "https://power.larc.nasa.gov/api/temporal/climatology/point"
MOIS_POWER = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
JOURS = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


# Températures : T2M_MAX / T2M_MIN (et même T2M_MAX_AVG / T2M_MIN_AVG) sont, dans les normales POWER, les valeurs
# EXTRÊMES du mois (Paris en juillet : 39,6 °C ; Calcutta en janvier : 3,4 °C la nuit), pas les moyennes des
# après-midi et des nuits. Vérifié le 28/11/2026 par le chasseur d'erreurs. On calcule donc :
#   max moyen = T2M (moyenne) + T2M_RANGE (écart moyen jour/nuit) / 2 ; min moyen = T2M - T2M_RANGE / 2
# (Paris : 25 °C / 14 °C en juillet ; Calcutta : 24 °C / 10 °C en janvier, proches des normales des stations).
METHODE = "T2M±T2M_RANGE/2"


def url_power(v):
    q = {"parameters": "T2M,T2M_RANGE,PRECTOTCORR", "community": "AG", "longitude": round(v["lon"], 3),
         "latitude": round(v["lat"], 3), "format": "JSON"}
    return POWER + "?" + urllib.parse.urlencode(q)


def normales_power(rep):
    """Normales mensuelles NASA POWER (moyennes sur 30 ans) -> format du guide."""
    p = rep["properties"]["parameter"]
    mois = []
    for i, m in enumerate(MOIS_POWER):
        moy, ecart, pluie_jour = p["T2M"].get(m), p["T2M_RANGE"].get(m), p["PRECTOTCORR"].get(m)
        if moy is None or ecart is None or pluie_jour is None or min(moy, ecart, pluie_jour) < -900 or not 0 <= ecart <= 30:
            return None
        tmax, tmin = moy + ecart / 2, moy - ecart / 2
        mois.append({"tmax": round(tmax, 1), "tmin": round(tmin, 1), "pluie_mm": round(max(0, pluie_jour) * JOURS[i]),
                     "jours_pluie": None, "soleil_h": None})
    return mois


PERIODE = "2001-2025"  # période des normales POWER (message de l'API : « January 2001 - December 2025 »)


def a_jour(f):
    """Fichier de climat juste : archive Open-Meteo (moyennes journalières), ou NASA POWER calculé avec la bonne méthode."""
    return f.get("source") != "NASA POWER" or f.get("methode") == METHODE


def normales(d):  # (ancienne source Open-Meteo, plus utilisée)
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
    p.add_argument("--max-villes", type=int, default=8000, help="nombre maximal de calculs (appels à NASA POWER) par nuit")
    p.add_argument("--duree-max", type=float, default=320, help="minutes : au-delà, arrêt propre")
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
            if not ancien or not a_jour(ancien) or (c.maintenant() - datetime.fromisoformat(ancien["date"].replace("Z", "+00:00"))).days > 730:
                lot.append(v)
    ok = ech = partages = appels = 0
    debut_t = time.monotonic()
    for v in lot:
        if time.monotonic() - debut_t > a.duree_max * 60:
            print("Durée maximale atteinte : la suite passera la nuit prochaine.")
            break
        if not a.demo:
            w = voisin_calcule(v)
            if w and w["id"] != v["id"]:
                ref = c.lire(f"climat/{w['id']}.json")
                if ref and "mois" in ref and a_jour(ref):
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
            brut = c.http(url_power(v), delai=60, essais=2)
            mois = None
            if brut:
                try:
                    mois = normales_power(json.loads(brut))
                except (ValueError, KeyError, TypeError):
                    mois = None
            if not mois:
                ech += 1
                continue
        c.ecrire(f"climat/{v['id']}.json", {"date": c.horodatage(), "periode": PERIODE if not a.demo else "démo",
                                             "source": "NASA POWER", "methode": METHODE, "mois": mois}, compact=True)
        grille.setdefault((round(v["lat"] / 0.2), round(v["lon"] / 0.2)), []).append(v)
        ok += 1
        print(f"{v['nom']} : normales calculées")
        if not a.demo:
            time.sleep(2.2)  # environ 27 demandes par minute, sous la limite de NASA POWER
    c.journal("climat", "ok" if ech == 0 else "partiel", villes_calculees=ok, villes_partagees=partages, echecs=ech, mode="démo" if a.demo else "réel")


if __name__ == "__main__":
    main()
