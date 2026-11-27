#!/usr/bin/env python3
"""
Robot Photos : une galerie de photos pour chaque ville (en plus de la grande photo de la fiche).

Source : Wikimedia Commons (licences libres). Pour chaque ville, le robot lit la « catégorie Commons »
indiquée dans Wikidata (propriété P373), puis choisit les meilleures photos de cette catégorie
(photos JPEG de bonne taille, sans cartes, logos, blasons ni plans). Seuls les liens vers les images
sont enregistrés (les photos restent hébergées par Wikimedia) : le site ne grossit presque pas.

Rythme : villes phares tous les 60 jours, intermédiaires tous les 120 jours, autres tous les 240 jours.

  python3 robots/robot_photos.py --max-villes 4000 --duree-max 150
  python3 robots/robot_photos.py --demo
"""
import argparse, json, re, time, urllib.parse
from datetime import datetime
import commun as c

SPARQL = "https://query.wikidata.org/sparql"
COMMONS = "https://commons.wikimedia.org/w/api.php"
FREQUENCE = {"phare": 60, "intermediaire": 120, "autre": 240}
NOMBRE = {"phare": 16, "intermediaire": 10, "autre": 6}
EXCLUS = re.compile(r"(map|karte|carte|plan|logo|coat|wappen|blason|escudo|flag|drapeau|bandera|seal|sceau|locator|"
                    r"diagram|chart|graph|icon|signature|stamp|timbre|svg|panorama_ch|satellite|sentinel|landsat)", re.I)
DEBUT = time.monotonic()


def sparql(requete):
    brut = c.http(SPARQL, donnees=urllib.parse.urlencode({"query": requete, "format": "json"}).encode(), delai=20)
    return json.loads(brut)["results"]["bindings"] if brut else None


def api(**params):
    params.update(format="json", formatversion=2)
    brut = c.http(COMMONS + "?" + urllib.parse.urlencode(params), delai=15)
    return json.loads(brut) if brut else None


def categories(qids):
    """Catégorie Commons (P373) de chaque élément Wikidata, par lots de 200."""
    out = {}
    qids = [q for q in dict.fromkeys(qids) if q]
    for i in range(0, len(qids), 200):
        rep = sparql("SELECT ?v ?cat WHERE { VALUES ?v { %s } ?v wdt:P373 ?cat . }" % " ".join("wd:" + q for q in qids[i:i + 200]))
        for r in rep or []:
            out.setdefault(r["v"]["value"].rsplit("/", 1)[-1], r["cat"]["value"])
        time.sleep(1)
    return out


def texte(html_):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html_ or "")).strip()


def photos_categorie(cat, n):
    rep = api(action="query", generator="categorymembers", gcmtitle="Category:" + cat, gcmtype="file", gcmlimit=60,
              prop="imageinfo", iiprop="url|size|mime|extmetadata", iiurlwidth=800,
              iiextmetadatafilter="Artist|LicenseShortName|ImageDescription")
    choix = []
    for p in (rep or {}).get("query", {}).get("pages", []):
        ii = (p.get("imageinfo") or [{}])[0]
        titre = p.get("title", "")[5:]
        if ii.get("mime") != "image/jpeg" or EXCLUS.search(titre) or ii.get("width", 0) < 1200 or ii.get("height", 0) < 700:
            continue
        meta = ii.get("extmetadata", {})
        legende = texte(meta.get("ImageDescription", {}).get("value", ""))[:140]
        choix.append({"u": ii.get("thumburl") or ii.get("url"), "page": ii.get("descriptionurl", ""),
                      "a": texte(meta.get("Artist", {}).get("value", ""))[:80] or "Wikimedia Commons",
                      "l": meta.get("LicenseShortName", {}).get("value", ""),
                      "t": legende or re.sub(r"\.[a-z]+$", "", titre, flags=re.I).replace("_", " ")[:140],
                      "_s": ii.get("width", 0) * ii.get("height", 0)})
    choix.sort(key=lambda x: -x["_s"])  # les plus grandes images d'abord (souvent les meilleures)
    for x in choix:
        x.pop("_s")
    return choix[:n]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-villes", type=int, default=4000)
    p.add_argument("--duree-max", type=int, default=150, help="minutes")
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    V = c.villes()
    suivi = c.lire("photos/_suivi.json", {})
    t = c.maintenant()
    if a.demo:
        lot = [v for v in V if v["slug"] in ("lisbonne-pt", "porto-pt")]
    else:
        dues = []
        for v in V:
            d = suivi.get(str(v["id"]))
            retard = (t - datetime.fromisoformat(d)).days - FREQUENCE[v["niveau"]] if d else 10**6
            if retard >= 0:
                dues.append(({"phare": 0, "intermediaire": 1, "autre": 2}[v["niveau"]], -retard, -v["population"], v))
        dues.sort(key=lambda x: x[:3])
        lot = [x[3] for x in dues[:a.max_villes]]
    table = c.lire("encyclo/_qid.json", {}) or {}
    cats = {} if a.demo else categories([table.get(str(v["id"]), "") for v in lot])
    ok = sans = ech = total = 0
    for v in lot:
        if time.monotonic() - DEBUT > a.duree_max * 60:
            print("Durée maximale atteinte : la suite passera la nuit prochaine.")
            break
        try:
            if a.demo:
                ph = [{"u": "https://upload.wikimedia.org/exemple.jpg", "page": "https://commons.wikimedia.org/wiki/File:Exemple.jpg",
                       "a": "Auteur d’exemple", "l": "CC BY-SA 4.0", "t": f"Vue de {v['nom']}"}] * 3
            else:
                cat = cats.get(table.get(str(v["id"]), ""))
                ph = photos_categorie(cat, NOMBRE[v["niveau"]]) if cat else []
        except Exception as err:  # une catégorie atypique ne doit pas arrêter le robot
            print(f"    {v['nom']} : {err}")
            ech += 1
            continue
        suivi[str(v["id"])] = t.isoformat()
        if ph:
            c.ecrire(f"photos/{v['id']}.json", {"date": c.horodatage(), "photos": ph}, compact=True)
            ok += 1
            total += len(ph)
        else:
            sans += 1
        if (ok + sans) % 200 == 0:
            c.ecrire("photos/_suivi.json", suivi, compact=True)
        if not a.demo:
            time.sleep(0.4)
    c.ecrire("photos/_suivi.json", suivi, compact=True)
    c.journal("photos", "ok" if ech == 0 else "partiel", villes_avec_photos=ok, photos=total, sans_photo=sans, echecs=ech,
              villes_suivies=len(suivi), mode="démo" if a.demo else "réel")
    print(f"Photos : {ok} villes illustrées ({total} photos), {sans} sans photo, {ech} échecs.")


if __name__ == "__main__":
    main()
