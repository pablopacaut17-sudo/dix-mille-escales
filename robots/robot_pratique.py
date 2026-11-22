#!/usr/bin/env python3
"""
Robot Pratique : informations pratiques par pays d'après Wikidata (CC0) : types de prises électriques (P2853),
tension (P2884), fréquence (P2144), sens de circulation (P1622). Une fois par mois.

  python3 robots/robot_pratique.py
"""
import argparse, json, re, urllib.parse
from datetime import datetime
import commun as c

SPARQL = "https://query.wikidata.org/sparql"
REQUETE = """SELECT ?iso ?priseLabel ?tension ?frequence ?conduiteLabel WHERE {
  ?pays wdt:P297 ?iso .
  OPTIONAL { ?pays wdt:P2853 ?prise }
  OPTIONAL { ?pays wdt:P2884 ?tension }
  OPTIONAL { ?pays wdt:P2144 ?frequence }
  OPTIONAL { ?pays wdt:P1622 ?conduite }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    ancien = c.lire("pratique.json")
    if ancien and not a.demo and (c.maintenant() - datetime.fromisoformat(ancien["date"].replace("Z", "+00:00"))).days < 30:
        print("Informations pratiques à jour.")
        return
    if a.demo:
        lignes = [{"iso": {"value": "IN"}, "priseLabel": {"value": "prise de type D"}, "tension": {"value": "230"}, "frequence": {"value": "50"}, "conduiteLabel": {"value": "circulation à gauche"}},
                  {"iso": {"value": "IN"}, "priseLabel": {"value": "prise de type C"}}]
    else:
        brut = c.http(SPARQL + "?" + urllib.parse.urlencode({"query": REQUETE, "format": "json"}), timeout=180, delai=30)
        if not brut:
            c.journal("pratique", "echec", raison="Wikidata injoignable")
            raise SystemExit("Wikidata injoignable : informations précédentes conservées.")
        lignes = json.loads(brut)["results"]["bindings"]
    res = {}
    for l in lignes:
        iso = l["iso"]["value"].upper()
        r = res.setdefault(iso, {"prises": [], "tension": None, "frequence": None, "conduite": None})
        pr = l.get("priseLabel", {}).get("value", "")
        m = re.search(r"\b(?:type|Type)\s+([A-N])\b", pr) or re.fullmatch(r"([A-N])", pr.strip())
        if m and m.group(1) not in r["prises"]:
            r["prises"].append(m.group(1))
        for k in ("tension", "frequence"):
            v = l.get(k, {}).get("value")
            if v and r[k] is None:
                try:
                    r[k] = round(float(v))
                except ValueError:
                    pass
        cd = l.get("conduiteLabel", {}).get("value", "").lower()
        if "gauche" in cd or "left" in cd:
            r["conduite"] = "gauche"
        elif ("droite" in cd or "right" in cd) and r["conduite"] is None:
            r["conduite"] = "droite"
    for r in res.values():
        r["prises"].sort()
    if len(res) < 50 and not a.demo:
        c.journal("pratique", "echec", raison=f"seulement {len(res)} pays lus")
        raise SystemExit("Réponse incomplète.")
    c.ecrire("pratique.json", {"date": c.horodatage(), "source": "Wikidata", "pays": res})
    c.journal("pratique", "ok", pays=len(res), mode="démo" if a.demo else "réel")
    print(f"Informations pratiques : {len(res)} pays.")


if __name__ == "__main__":
    main()
