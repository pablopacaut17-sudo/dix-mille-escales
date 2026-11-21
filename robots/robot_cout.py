#!/usr/bin/env python3
"""
Robot Coût de la vie : niveau des prix de chaque pays comparé à la France, d'après l'indicateur
« ratio du niveau des prix » de la Banque mondiale (PA.NUS.PPPC.RF, licence CC BY 4.0).
Le site en déduit une estimation des prix courants (repas, café, transport, hôtel, budget par jour).
C'est une moyenne nationale : les grandes villes touristiques sont souvent plus chères.

  python3 robots/robot_cout.py
  python3 robots/robot_cout.py --demo
"""
import argparse, json
import commun as c

URL = "https://api.worldbank.org/v2/country/all/indicator/PA.NUS.PPPC.RF?format=json&per_page=20000&mrnev=1"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    iso3 = {p["iso3"]: cc for cc, p in c.lire("pays.json", {}).items() if p.get("iso3")}  # code à 3 lettres -> 2 lettres
    if a.demo:
        lignes = [{"countryiso3code": "FRA", "value": 0.83, "date": "2024"}, {"countryiso3code": "PRT", "value": 0.62, "date": "2024"},
                  {"countryiso3code": "JPN", "value": 0.55, "date": "2024"}]
    else:
        brut = c.http(URL, timeout=180)
        if not brut:
            c.journal("cout", "echec")
            raise SystemExit("Banque mondiale injoignable, données conservées.")
        rep = json.loads(brut)
        lignes = rep[1] if isinstance(rep, list) and len(rep) > 1 else []
    brut = {}
    for l in lignes or []:
        cc = iso3.get(l.get("countryiso3code", ""))
        if cc and l.get("value"):
            brut[cc] = (l["value"], l.get("date", ""))
    if "FR" not in brut:
        c.journal("cout", "echec")
        raise SystemExit("Valeur de la France absente : impossible de comparer.")
    fr = brut["FR"][0]
    res = {cc: {"indice": round(v / fr, 3), "annee": an} for cc, (v, an) in brut.items()}
    c.ecrire("cout.json", {"date": c.horodatage(), "source": "Banque mondiale, PA.NUS.PPPC.RF", "pays": res})
    c.journal("cout", "ok", pays=len(res), mode="démo" if a.demo else "réel")
    print(f"Coût de la vie : {len(res)} pays.")


if __name__ == "__main__":
    main()
