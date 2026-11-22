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
COMMONS = "https://commons.wikimedia.org/w/api.php"
VERSION = 2  # 2 : photos des lieux (Wikimedia Commons) ; à chaque nouvelle version, tous les lieux sont retraités
RUBRIQUES = ("voir", "faire", "alentours", "acheter")
# Caractéristiques tirées de Wikidata : propriété -> (clé, genre)
PROPRIETES = {"P2048": ("hauteur", "q"), "P2046": ("superficie", "q"), "P2043": ("longueur", "q"), "P2044": ("altitude", "q"),
              "P2049": ("largeur", "q"), "P1174": ("visiteurs_an", "n"), "P571": ("creation", "t"), "P580": ("debut", "t"),
              "P1619": ("ouverture", "t"), "P84": ("architecte", "i"), "P149": ("style", "i"), "P1435": ("protection", "i")}
UNITES = {"Q11573": ("m", 1), "Q828224": ("m", 1000), "Q174728": ("m", 0.01), "Q3710": ("m", 0.3048),
          "Q25343": ("m2", 1), "Q712226": ("m2", 1e6), "Q35852": ("m2", 1e4), "Q81292": ("m2", 4046.86), "Q232291": ("m2", 2.59e6)}


def sans_html(t):
    import re, html
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()


def photos(fichiers):
    """Vignette, auteur et licence de fichiers Wikimedia Commons (par paquets de 50)."""
    out = {}
    liste = sorted(fichiers)
    for k in range(0, len(liste), 50):
        rep = api(COMMONS, action="query", titles="|".join("File:" + f for f in liste[k:k + 50]), prop="imageinfo",
                  iiprop="url|extmetadata", iiurlwidth=480, iiextmetadatafilter="Artist|LicenseShortName|Credit")
        q_ = (rep or {}).get("query", {})
        norm_ = {n["to"]: n["from"] for n in q_.get("normalized", [])}
        for pg in q_.get("pages", []):
            ii = (pg.get("imageinfo") or [{}])[0]
            if not ii.get("thumburl"):
                continue
            md = ii.get("extmetadata", {})
            nom = norm_.get(pg["title"], pg["title"])[5:]
            out[nom] = {"u": ii["thumburl"], "page": ii.get("descriptionurl", ""),
                        "a": sans_html(md.get("Artist", {}).get("value", ""))[:80] or "Wikimedia Commons",
                        "l": md.get("LicenseShortName", {}).get("value", "")}
        time.sleep(0.2)
    return out


def caracteristiques(claims):
    """Valeurs utiles d'une entité Wikidata (dimensions en mètres ou m², années, éléments à nommer, photo)."""
    out, a_nommer = {}, set()
    for cl in (claims.get("P18") or [])[:1]:  # image principale
        v = ((cl.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(v, str):
            out["_photo"] = v.replace(" ", "_")
    for p, (cle, genre) in PROPRIETES.items():
        for cl in (claims.get(p) or [])[:3]:
            dv = (cl.get("mainsnak") or {}).get("datavalue") or {}
            v = dv.get("value")
            if v is None:
                continue
            if genre == "q" and isinstance(v, dict):
                u = UNITES.get(v.get("unit", "").rsplit("/", 1)[-1])
                if u:
                    out[cle] = round(float(v["amount"]) * u[1], 2)
                    break
            elif genre == "n" and isinstance(v, dict):
                out[cle] = int(float(v["amount"]))
                break
            elif genre == "t" and isinstance(v, dict) and v.get("time"):
                an = int(v["time"][:5].replace("+", "") or 0) if v["time"][0] in "+-" else None
                if an:
                    out[cle] = an if v["time"][0] == "+" else -an
                    break
            elif genre == "i" and isinstance(v, dict) and v.get("id"):
                out.setdefault(cle, []).append(v["id"]); a_nommer.add(v["id"])
    return out, a_nommer


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
    if vus.get("_version") != VERSION:
        vus = {"_version": VERSION}
    tous = qids_des_lieux()
    a_faire = sorted(q for q in tous if q != "_version" and (not vus.get(q) or (t0 - datetime.fromisoformat(vus[q])).days > 180))
    print(f"{len(tous)} lieux célèbres, {len(a_faire)} à traiter.")
    faits = sans = 0
    for k in range(0, len(a_faire), 50):
        if time.monotonic() - debut > a.duree_max * 60:
            print("Durée maximale atteinte : la suite passera la nuit prochaine.")
            break
        paquet = a_faire[k:k + 50]
        rep = api(WIKIDATA, action="wbgetentities", ids="|".join(paquet), props="sitelinks|claims", sitefilter="frwiki")
        titres, carac, a_nommer = {}, {}, set()
        for q in paquet:
            ent = (rep or {}).get("entities", {}).get(q, {})
            cr, an_ = caracteristiques(ent.get("claims") or {})
            if cr:
                carac[q] = cr; a_nommer |= an_
        imgs = photos({cr["_photo"] for cr in carac.values() if cr.get("_photo")})
        for q, cr in list(carac.items()):
            ph = cr.pop("_photo", None)
            if ph and ph in imgs:
                cr["photo"] = imgs[ph]
            elif ph:
                pass
            if not cr:
                del carac[q]
        if a_nommer:  # noms en français des architectes, styles, protections
            noms_ = {}
            liste_ = sorted(a_nommer)
            for z in range(0, len(liste_), 50):
                rl = api(WIKIDATA, action="wbgetentities", ids="|".join(liste_[z:z + 50]), props="labels", languages="fr|en")
                for i_, e_ in ((rl or {}).get("entities") or {}).items():
                    lb = e_.get("labels", {})
                    noms_[i_] = (lb.get("fr") or lb.get("en") or {}).get("value", "")
            for q, cr in carac.items():
                for k in ("architecte", "style", "protection"):
                    if k in cr:
                        cr[k] = [noms_[x] for x in cr[k] if noms_.get(x)][:3]
                        if not cr[k]:
                            del cr[k]
        for q in paquet:
            sl = ((rep or {}).get("entities", {}).get(q, {}).get("sitelinks", {}) or {}).get("frwiki")
            if sl:
                titres[sl["title"]] = q
            else:
                vus[q] = t0.isoformat(); sans += 1
                if q in carac:  # pas d'article en français, mais des caractéristiques utiles
                    seaux[seau(q)][q] = {"t": "", "r": "", "f": carac[q]}
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
                    seaux[seau(q)][q] = {"t": pg["title"], "r": ex, **({"f": carac[q]} if q in carac else {})}
                elif q in carac:
                    seaux[seau(q)][q] = {"t": pg["title"], "r": "", "f": carac[q]}
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
