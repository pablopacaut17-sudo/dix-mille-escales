#!/usr/bin/env python3
"""
Robot Jours fériés : jours fériés de l'année en cours et de la suivante, pour chaque pays du guide.
Source : Nager.Date (API publique gratuite). Les pays non couverts par la source sont ignorés.
Ne retélécharge un pays que si ses données ont plus de 30 jours.

  python3 robots/robot_feries.py
  python3 robots/robot_feries.py --demo
"""
import argparse, json, time
from datetime import date, datetime
import commun as c


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    pays = sorted({v["pays"] for v in c.villes()})
    if a.demo:
        pays = ["PT", "JP"]
    an = date.today().year
    ok = absents = ech = 0
    for cc in pays:
        ancien = c.lire(f"feries/{cc}.json")
        if ancien and not a.demo and (c.maintenant() - datetime.fromisoformat(ancien["date"].replace("Z", "+00:00"))).days < 30:
            continue
        jours = []
        for y in (an, an + 1):
            if a.demo:
                jours += [{"date": f"{y}-01-01", "nom": "Jour de l’an", "nom_local": "Ano Novo"},
                          {"date": f"{y}-12-25", "nom": "Noël", "nom_local": "Natal"}]
                continue
            brut = c.http(f"https://date.nager.at/api/v3/PublicHolidays/{y}/{cc}", delai=10)
            if brut is None:
                break
            if brut == b"":
                continue
            for h in json.loads(brut):
                if h.get("global", True):  # fériés nationaux seulement
                    jours.append({"date": h["date"], "nom": h.get("name", ""), "nom_local": h.get("localName", "")})
            time.sleep(0.5)
        if jours:
            c.ecrire(f"feries/{cc}.json", {"date": c.horodatage(), "jours": jours})
            ok += 1
        else:
            absents += 1
    c.journal("feries", "ok", pays_a_jour=ok, pays_non_couverts=absents, mode="démo" if a.demo else "réel")
    print(f"Jours fériés : {ok} pays mis à jour, {absents} non couverts par la source.")


if __name__ == "__main__":
    main()
