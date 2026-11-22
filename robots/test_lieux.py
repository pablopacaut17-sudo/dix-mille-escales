#!/usr/bin/env python3
"""
Test rapide du robot Lieux : interroge les serveurs OpenStreetMap pour quelques villes et mesure le temps et le résultat,
sans rien modifier dans les données du guide. Résultat écrit dans test/lieux.json (branche « donnees-test »).

  python3 robots/test_lieux.py paris-fr lisbonne-pt manali-in
"""
import json, sys, time
import commun as c
import robot_lieux as L


def main():
    slugs = sys.argv[1:]
    V = {v["slug"]: v for v in c.villes()}
    res, serveur = [], 0
    for s in slugs:
        v = V.get(s)
        if not v:
            res.append({"ville": s, "erreur": "inconnue"}); continue
        t0, elements, ok = time.monotonic(), [], True
        for q in L.requetes(v):
            r, serveur = L.interroger(q, serveur)
            if r is None:
                ok = False; break
            elements += r
        t1 = time.monotonic()
        autour = []
        if ok:
            autour, serveur = L.interroger(L.requete_alentours(v), serveur)
            autour = autour or []
        date = c.horodatage()
        fiches = [f for f in (L.normaliser(e, date, v) for e in elements) if f]
        res.append({"ville": v["nom"], "niveau": v["niveau"], "rayon_km": round(L.rayon_km(v), 1), "reussi": ok,
                    "lieux": len({f["id"] for f in fiches}), "informations": sum(f["infos"] for f in fiches),
                    "sites_alentours": len(autour), "secondes": round(time.monotonic() - t0), "secondes_ville": round(t1 - t0),
                    "serveur": L.SERVEURS[serveur].split("/")[2]})
        print(res[-1], flush=True)
        c.ecrire("test/lieux.json", {"date": date, "resultats": res})


if __name__ == "__main__":
    main()
