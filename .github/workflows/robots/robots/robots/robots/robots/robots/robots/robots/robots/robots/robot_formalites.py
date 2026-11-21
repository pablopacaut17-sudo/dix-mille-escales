#!/usr/bin/env python3
"""
Robot Formalités : visa nécessaire ou non, et durée de séjour autorisée, pour les passeports
français, belge, suisse et canadien, vers chaque pays du guide.
Source : Passport Index Data (licence MIT), jeu de données ouvert mis à jour régulièrement.
Les règles changent : le site renvoie toujours vers la source officielle avant de partir.

  python3 robots/robot_formalites.py
  python3 robots/robot_formalites.py --demo
"""
import argparse, csv, io
import commun as c

SOURCE = "https://raw.githubusercontent.com/imorte/passport-index-data/main/passport-index-tidy-iso2.csv"
PASSEPORTS = ["FR", "BE", "CH", "CA"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    if a.demo:
        texte = "Passport,Destination,Requirement\nFR,PT,visa free\nFR,JP,90\nBE,JP,90\nCH,JP,90\nCA,JP,90\nBE,PT,visa free\nCH,PT,visa free\nCA,PT,90\n"
    else:
        brut = c.http(SOURCE)
        if not brut:
            c.journal("formalites", "echec")
            raise SystemExit("Source injoignable, formalités conservées.")
        texte = brut.decode("utf-8")
    res = {pp: {} for pp in PASSEPORTS}
    for l in csv.DictReader(io.StringIO(texte)):
        if l["Passport"] in res:
            res[l["Passport"]][l["Destination"]] = l["Requirement"]
    if not res["FR"]:
        c.journal("formalites", "echec")
        raise SystemExit("Données vides : format changé ?")
    c.ecrire("formalites.json", {"date": c.horodatage(), "source": "Passport Index Data (MIT)", "passeports": res}, compact=True)
    c.journal("formalites", "ok", destinations=len(res["FR"]), mode="démo" if a.demo else "réel")
    print(f"Formalités : {len(res['FR'])} destinations pour le passeport français.")


if __name__ == "__main__":
    main()
  
