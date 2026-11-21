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

INDICATEUR = "PA.NUS.PPPC.RF"
ESSAIS = [  # plusieurs façons de demander la donnée : la plus récente disponible pour chaque pays
    f"https://api.worldbank.org/v2/country/all/indicator/{INDICATEUR}?format=json&per_page=20000&mrnev=1",
    f"https://api.worldbank.org/v2/country/all/indicator/{INDICATEUR}?format=json&per_page=20000&date=2015:2026",
]


def telecharger():
    """Renvoie {code ISO3: (valeur, année)} avec la valeur la plus récente de chaque pays, ou (None, raison)."""
    raison = "pas de réponse"
    for url in ESSAIS:
        brut = c.http(url, timeout=180, delai=20)
        if not brut:
            raison = "Banque mondiale injoignable"
            continue
        try:
            rep = json.loads(brut)
        except ValueError:
            raison = "réponse illisible"
            continue
        if not (isinstance(rep, list) and len(rep) > 1 and rep[1]):
            raison = "réponse vide ou message d’erreur : " + str(rep)[:120]
            continue
        res = {}
        for l in rep[1]:
            cc3, v, an = l.get("countryiso3code"), l.get("value"), l.get("date", "")
            if cc3 and v is not None and (cc3 not in res or an > res[cc3][1]):
                res[cc3] = (v, an)
        if res:
            return res, None
        raison = "aucune valeur dans la réponse"
    return None, raison


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    iso3 = {p["iso3"]: cc for cc, p in c.lire("pays.json", {}).items() if p.get("iso3")}  # code à 3 lettres -> 2 lettres
    if a.demo:
        valeurs = {"FRA": (0.83, "2024"), "PRT": (0.62, "2024"), "JPN": (0.55, "2024")}
    else:
        valeurs, raison = telecharger()
        if valeurs is None:
            c.journal("cout", "echec", raison=raison)
            raise SystemExit(f"Coût de la vie : {raison}. Données précédentes conservées.")
    brut = {}
    for cc3, (v, an) in valeurs.items():
        cc = iso3.get(cc3)
        if cc:
            brut[cc] = (v, an)
    if "FR" not in brut:
        c.journal("cout", "echec", raison="valeur de la France absente")
        raise SystemExit("Valeur de la France absente : impossible de comparer.")
    fr = brut["FR"][0]
    res = {cc: {"indice": round(v / fr, 3), "annee": an} for cc, (v, an) in brut.items()}
    c.ecrire("cout.json", {"date": c.horodatage(), "source": "Banque mondiale, PA.NUS.PPPC.RF", "pays": res})
    c.journal("cout", "ok", pays=len(res), mode="démo" if a.demo else "réel")
    print(f"Coût de la vie : {len(res)} pays.")


if __name__ == "__main__":
    main()
