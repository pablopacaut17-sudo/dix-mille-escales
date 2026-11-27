#!/usr/bin/env python3
"""
Robot Fêtes et festivals : les festivals et événements qui reviennent chaque année dans chaque ville
(festivals de musique, de cinéma, carnavals, fêtes traditionnelles, foires, salons…).

Source : Wikidata (licence CC0). Sont retenus les éléments « festival » ou « événement récurrent »
situés dans la ville (propriétés P276 « lieu » ou P131 « localisation administrative »), sauf les éditions
d'une année donnée et les événements disparus.

Rythme : toutes les villes tous les 60 jours, par lots de 80 villes par requête.

  python3 robots/robot_fetes.py --max-villes 20000 --duree-max 120
  python3 robots/robot_fetes.py --demo
"""
import argparse, json, time, urllib.parse
from datetime import datetime
import commun as c

SPARQL = "https://query.wikidata.org/sparql"
FREQUENCE = 60
NOMBRE = {"phare": 25, "intermediaire": 15, "autre": 8}
REQUETE = """SELECT ?v ?f ?fLabel ?desc ?site ?debut ?mois WHERE {
  VALUES ?v { %s }
  { ?f wdt:P276 ?v } UNION { ?f wdt:P131 ?v }
  ?f wdt:P31/wdt:P279* ?classe .
  VALUES ?classe { wd:Q132241 wd:Q15275719 }
  FILTER NOT EXISTS { ?f wdt:P31 wd:Q27968055 }
  FILTER NOT EXISTS { ?f wdt:P179 ?serie }
  FILTER NOT EXISTS { ?f wdt:P576 ?fin }
  OPTIONAL { ?f schema:description ?desc FILTER(LANG(?desc) = "fr") }
  OPTIONAL { ?f wdt:P856 ?site }
  OPTIONAL { ?f wdt:P571 ?debut }
  OPTIONAL { ?f wdt:P2922 ?m . ?m rdfs:label ?mois FILTER(LANG(?mois) = "fr") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en,[AUTO_LANGUAGE]". }
} LIMIT 4000"""
DEBUT = time.monotonic()


def sparql(requete):
    brut = c.http(SPARQL, donnees=urllib.parse.urlencode({"query": requete, "format": "json"}).encode(), delai=30, timeout=90)
    return json.loads(brut)["results"]["bindings"] if brut else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-villes", type=int, default=20000)
    p.add_argument("--duree-max", type=int, default=120, help="minutes")
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    V = c.villes()
    suivi = c.lire("fetes/_suivi.json", {})
    t = c.maintenant()
    table = c.lire("encyclo/_qid.json", {}) or {}
    if a.demo:
        lot = [v for v in V if v["slug"] in ("lisbonne-pt", "porto-pt")]
    else:
        lot = [v for v in sorted(V, key=lambda v: ({"phare": 0, "intermediaire": 1, "autre": 2}[v["niveau"]], -v["population"]))
               if table.get(str(v["id"])) and (not suivi.get(str(v["id"]))
                                               or (t - datetime.fromisoformat(suivi[str(v["id"])])).days >= FREQUENCE)][:a.max_villes]
    if a.demo:
        table = {str(v["id"]): f"Q{v['id']}" for v in lot}
    par_qid = {table[str(v["id"])]: v for v in lot if table.get(str(v["id"]))}
    ok = fetes = ech = 0
    qids = list(par_qid)
    for i in range(0, len(qids), 80):
        if time.monotonic() - DEBUT > a.duree_max * 60:
            print("Durée maximale atteinte : la suite passera la prochaine fois.")
            break
        paquet = qids[i:i + 80]
        if a.demo:
            res = {v["id"]: [{"nom": "Festival d’exemple", "desc": "festival de musique", "depuis": "1998", "mois": "juin", "qid": "Q1"}] for v in lot}
        else:
            rep = sparql(REQUETE % " ".join("wd:" + q for q in paquet))
            if rep is None:
                ech += 1
                time.sleep(20)
                continue
            res = {}
            for r in rep:
                v = par_qid.get(r["v"]["value"].rsplit("/", 1)[-1])
                fq = r["f"]["value"].rsplit("/", 1)[-1]
                nom = r.get("fLabel", {}).get("value", "")
                if not v or not nom or nom == fq:
                    continue
                liste = res.setdefault(v["id"], {})
                x = liste.setdefault(fq, {"nom": nom, "qid": fq})
                if r.get("desc"):
                    x["desc"] = r["desc"]["value"][:160]
                if r.get("site"):
                    x["site"] = r["site"]["value"]
                if r.get("debut") and r["debut"]["value"][:1] in "12":
                    x["depuis"] = r["debut"]["value"][:4]
                if r.get("mois"):
                    x.setdefault("mois", r["mois"]["value"])
            res = {k: list(d.values()) for k, d in res.items()}
        for q in paquet:
            v = par_qid[q]
            suivi[str(v["id"])] = t.isoformat()
            liste = res.get(v["id"], [])
            if liste:
                liste.sort(key=lambda x: (not x.get("desc"), not x.get("site"), x["nom"]))
                c.ecrire(f"fetes/{v['id']}.json", {"date": c.horodatage(), "fetes": liste[:NOMBRE[v["niveau"]]]}, compact=True)
                ok += 1
                fetes += min(len(liste), NOMBRE[v["niveau"]])
        c.ecrire("fetes/_suivi.json", suivi, compact=True)
        if not a.demo:
            time.sleep(2)
    c.journal("fetes", "ok" if ech == 0 else "partiel", villes_avec_fetes=ok, fetes=fetes, lots_en_echec=ech,
              villes_suivies=len(suivi), mode="démo" if a.demo else "réel")
    print(f"Fêtes et festivals : {fetes} événements pour {ok} villes, {ech} lots en échec.")


if __name__ == "__main__":
    main()
