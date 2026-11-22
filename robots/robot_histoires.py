#!/usr/bin/env python3
"""
Robot Histoires : l'histoire des lieux célèbres (monuments, musées, sites, parcs…) qui ont une fiche Wikidata :
le résumé de leur article Wikipédia en français (licence CC BY-SA), avec un lien vers l'article complet.
Les lieux sont tirés des fichiers des robots Lieux. Chaque résumé est revérifié tous les 180 jours.

  python3 robots/robot_histoires.py --duree-max 300
"""
import argparse, gzip, json, os, time, urllib.parse
from datetime import datetime
import commun as c

WIKIDATA = "https://www.wikidata.org/w/api.php"
WIKIPEDIA = "https://fr.wikipedia.org/w/api.php"
RUBRIQUES = ("voir", "faire", "alentours", "acheter")


def api(base, **q):
    q.update(format="json", formatversion=2)
    brut = c.http(base + "?" + urllib.parse.urlencode(q), delai=15)
    return json.loads(brut) if brut else None


def qids_des_lieux():
    out = set()
    base = os.path.join(c.DATA, "lieux")
    for racine, _, fichiers in os.walk(base):
        for fn in fichiers:
            if fn.startswith("_") or not (fn.endswith(".json.gz") or fn.endswith(".json")):
                continue
            try:
                ouvrir = gzip.open if fn.endswith(".gz") else open
                with ouvrir(os.path.join(racine, fn), "rt", encoding="utf-8") as f:
                    d = json.load(f)
            except (OSError, ValueError):
                continue
            for x in d.get("lieux", []):
                q = x.get("wikidata", "")
                if x.get("rubrique") in RUBRIQUES and q.startswith("Q") and q[1:].isdigit():
                    out.add(q)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--duree-max", type=float, default=300)
    a = p.parse_args()
    debut, t0 = time.monotonic(), c.maintenant()
    seaux = {}
    def seau(q): return f"h{int(q[1:]) % 100:02d}"
    for i in range(100):
        seaux[f"h{i:02d}"] = c.lire(f"histoires/h{i:02d}.json", {}) or {}
    vus = c.lire("histoires/_suivi.json", {}) or {}
    tous = qids_des_lieux()
    a_faire = sorted(q for q in tous if not vus.get(q) or (t0 - datetime.fromisoformat(vus[q])).days > 180)
    print(f"{len(tous)} lieux célèbres, {len(a_faire)} à traiter.")
    faits = sans = 0
    for k in range(0, len(a_faire), 50):
        if time.monotonic() - debut > a.duree_max * 60:
            print("Durée maximale atteinte : la suite passera la nuit prochaine.")
            break
        paquet = a_faire[k:k + 50]
        rep = api(WIKIDATA, action="wbgetentities", ids="|".join(paquet), props="sitelinks", sitefilter="frwiki")
        titres = {}
        for q in paquet:
            sl = ((rep or {}).get("entities", {}).get(q, {}).get("sitelinks", {}) or {}).get("frwiki")
            if sl:
                titres[sl["title"]] = q
            else:
                vus[q] = t0.isoformat(); sans += 1
        noms = list(titres)
        for j in range(0, len(noms), 20):
            rep = api(WIKIPEDIA, action="query", prop="extracts", exintro=1, explaintext=1, exlimit=20, titles="|".join(noms[j:j + 20]), redirects=1)
            q_ = (rep or {}).get("query", {})
            renvois = {r["from"]: r["to"] for r in q_.get("redirects", [])}
            inverse = {renvois.get(t, t): t for t in noms[j:j + 20]}
            for pg in q_.get("pages", []):
                ex = (pg.get("extract") or "").strip()
                orig = inverse.get(pg.get("title"))
                q = titres.get(orig) if orig else None
                if not q:
                    continue
                vus[q] = t0.isoformat()
                if len(ex) > 80:
                    if len(ex) > 900:
                        coupe = ex[:900].rfind(". ")
                        ex = ex[:coupe + 1] if coupe > 400 else ex[:900] + "…"
                    seaux[seau(q)][q] = {"t": pg["title"], "r": ex}
                    faits += 1
            time.sleep(0.2)
        if k % 2000 == 0:
            for nom, d in seaux.items():
                c.ecrire(f"histoires/{nom}.json", d, compact=True)
            c.ecrire("histoires/_suivi.json", vus, compact=True)
    for nom, d in seaux.items():
        c.ecrire(f"histoires/{nom}.json", d, compact=True)
    c.ecrire("histoires/_suivi.json", vus, compact=True)
    total = sum(len(d) for d in seaux.values())
    c.journal("histoires", "ok", resumes_ajoutes=faits, sans_article=sans, lieux_avec_histoire=total, lieux_celebres=len(tous))
    print(f"Histoires : {faits} résumés ajoutés, {total} lieux avec leur histoire.")


if __name__ == "__main__":
    main()
