#!/usr/bin/env python3
"""
Robot Change : taux de référence de l'euro publiés chaque jour ouvré par la Banque centrale européenne
(une trentaine de devises).

  python3 robots/robot_change.py
  python3 robots/robot_change.py --demo
"""
import argparse, re
import commun as c

URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    if a.demo:
        texte = "<Cube time='2026-11-20'><Cube currency='USD' rate='1.08'/><Cube currency='JPY' rate='165.2'/></Cube>"
    else:
        brut = c.http(URL)
        if brut is None:
            c.journal("change", "echec")
            raise SystemExit("BCE injoignable, taux conservés.")
        texte = brut.decode("utf-8")
    jour = re.search(r"time=['\"]([\d-]+)['\"]", texte)
    taux = {m.group(1): float(m.group(2)) for m in re.finditer(r"currency=['\"](\w{3})['\"]\s+rate=['\"]([\d.]+)['\"]", texte)}
    if not taux:
        c.journal("change", "echec")
        raise SystemExit("Format de la BCE inattendu, taux conservés.")
    c.ecrire("change.json", {"date": c.horodatage(), "jour_bce": jour.group(1) if jour else "", "base": "EUR", "taux": taux})
    c.journal("change", "ok", devises=len(taux), mode="démo" if a.demo else "réel")
    print(f"Change : {len(taux)} devises.")


if __name__ == "__main__":
    main()
  
