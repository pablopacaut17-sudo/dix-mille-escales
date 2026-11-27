#!/usr/bin/env python3
"""
Correction des dates « avant Jésus-Christ » des histoires (une seule fois).

L'ancienne lecture des dates de Wikidata transformait « 3180 av. J.-C. » en « 3180 » (Skara Brae, Caral,
Mycènes…). Le robot Histoires est corrigé, mais il ne revoit chaque lieu que tous les 180 jours : ce script
relit tout de suite, par paquets de 250, les dates de création, de début et d'ouverture de tous les lieux
qui en ont une, et remet le bon signe. Il note sa progression et s'arrête de lui-même une fois tout corrigé.

  python3 robots/corriger_dates.py --duree-max 40
"""
import argparse, json, re, time, urllib.parse
import commun as c

SPARQL = "https://query.wikidata.org/sparql"
PROPS = {"creation": "P571", "debut": "P580", "ouverture": "P1619"}
REQUETE = """SELECT ?i ?p ?d WHERE { VALUES ?i { %s } VALUES (?p ?prop) { ("creation" wdt:P571) ("debut" wdt:P580) ("ouverture" wdt:P1619) }
  ?i ?prop ?d }"""
DEBUT = time.monotonic()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--duree-max", type=int, default=40, help="minutes")
    a = p.parse_args()
    etat = c.lire("histoires/_dates.json", {}) or {}
    if etat.get("fini"):
        print("Dates déjà corrigées.")
        return
    faits = set(etat.get("faits", []))
    seaux = {f"h{i:02d}": c.lire(f"histoires/h{i:02d}.json", {}) or {} for i in range(100)}
    a_voir = [(s, q) for s, d in seaux.items() for q, h in d.items()
              if isinstance(h, dict) and isinstance(h.get("f"), dict) and any(k in h["f"] for k in PROPS) and q not in faits]
    print(f"{len(a_voir)} lieux à relire.")
    corriges = ech = 0
    modifies = set()
    for i in range(0, len(a_voir), 250):
        if time.monotonic() - DEBUT > a.duree_max * 60:
            print("Durée maximale atteinte : la suite passera la prochaine fois.")
            break
        paquet = a_voir[i:i + 250]
        brut = c.http(SPARQL, donnees=urllib.parse.urlencode({"query": REQUETE % " ".join("wd:" + q for _, q in paquet), "format": "json"}).encode(),
                      delai=20, timeout=90)
        if not brut:
            ech += 1
            continue
        dates = {}
        for r in json.loads(brut)["results"]["bindings"]:
            m_ = re.match(r"(-?)(\d+)-", r["d"]["value"])  # en SPARQL, les années av. J.-C. commencent par « - »
            if m_:
                q, k = r["i"]["value"].rsplit("/", 1)[-1], r["p"]["value"]
                an = int(m_.group(2)) * (-1 if m_.group(1) else 1)
                dates.setdefault((q, k), an)
        for s, q in paquet:
            f = seaux[s][q]["f"]
            for k in PROPS:
                juste = dates.get((q, k))
                if k in f and juste is not None and juste < 0 and f[k] == -juste:
                    f[k] = juste
                    corriges += 1
                    modifies.add(s)
            faits.add(q)
    for s in modifies:
        c.ecrire(f"histoires/{s}.json", seaux[s], compact=True)
    fini = len(faits) >= len(faits | {q for _, q in a_voir})
    c.ecrire("histoires/_dates.json", {"fini": fini, "faits": [] if fini else sorted(faits)}, compact=True)
    print(f"{corriges} dates remises avant Jésus-Christ ; {len(faits)} lieux relus ; paquets en échec : {ech}.")
    c.journal("corriger_dates", "ok" if not ech else "partiel", corriges=corriges, relus=len(faits), fini=fini)


if __name__ == "__main__":
    main()
