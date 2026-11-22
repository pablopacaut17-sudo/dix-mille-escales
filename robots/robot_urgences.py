#!/usr/bin/env python3
"""
Robot Urgences : numéros d'urgence de chaque pays (police, ambulance, pompiers…), d'après Wikidata (licence CC0),
propriété « numéro de téléphone d'urgence » (P2852) des pays. Le site rappelle toujours de vérifier sur place.
Une fois par mois.

  python3 robots/robot_urgences.py
"""
import argparse, json, re, urllib.parse
from datetime import datetime
import commun as c

SPARQL = "https://query.wikidata.org/sparql"
REQUETE = """SELECT ?iso ?numLabel ?usageLabel WHERE {
  ?pays wdt:P297 ?iso ; p:P2852 ?st .
  ?st ps:P2852 ?num .
  FILTER NOT EXISTS { ?st wikibase:rank wikibase:DeprecatedRank }
  OPTIONAL { ?st pq:P366 ?usage }
  OPTIONAL { ?st pq:P642 ?usage }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    ancien = c.lire("urgences.json")
    if ancien and not a.demo and (c.maintenant() - datetime.fromisoformat(ancien["date"].replace("Z", "+00:00"))).days < 30:
        print("Numéros d'urgence à jour : rien à faire.")
        return
    if a.demo:
        lignes = [{"iso": {"value": "FR"}, "numLabel": {"value": "112"}}, {"iso": {"value": "FR"}, "numLabel": {"value": "15"}, "usageLabel": {"value": "aide médicale urgente"}},
                  {"iso": {"value": "IN"}, "numLabel": {"value": "112"}}]
    else:
        brut = c.http(SPARQL + "?" + urllib.parse.urlencode({"query": REQUETE, "format": "json"}), timeout=120, delai=30)
        if not brut:
            c.journal("urgences", "echec", raison="Wikidata injoignable")
            raise SystemExit("Wikidata injoignable : numéros précédents conservés.")
        lignes = json.loads(brut)["results"]["bindings"]
    res = {}
    for l in lignes:
        iso, num = l["iso"]["value"].upper(), l["numLabel"]["value"].strip()
        if not re.fullmatch(r"[0-9 +*#]{2,12}", num):
            continue  # libellé qui n'est pas un numéro
        usage = l.get("usageLabel", {}).get("value", "")
        if re.fullmatch(r"Q\d+", usage):
            usage = ""
        liste = res.setdefault(iso, [])
        exist = next((x for x in liste if x["numero"] == num), None)
        if exist:
            if usage and usage not in exist["services"]:
                exist["services"].append(usage)
        else:
            liste.append({"numero": num, "services": [usage] if usage else []})
    if len(res) < 50 and not a.demo:
        c.journal("urgences", "echec", raison=f"seulement {len(res)} pays lus")
        raise SystemExit("Réponse incomplète : numéros précédents conservés.")
    c.ecrire("urgences.json", {"date": c.horodatage(), "source": "Wikidata (P2852)", "pays": res})
    c.journal("urgences", "ok", pays=len(res), mode="démo" if a.demo else "réel")
    print(f"Numéros d'urgence : {len(res)} pays.")


if __name__ == "__main__":
    main()
