#!/usr/bin/env python3
"""
Robot Chiffres : les grands chiffres des lieux, pour répondre à « fréquentation de la gare de Lyon »,
« capacité du Stade de France » ou « visiteurs du Louvre » sans que la ville soit citée.

Source : Wikidata (licence CC0), pays par pays :
  - fréquentation annuelle (P3872 : gares, aéroports, stations), la valeur la plus récente avec son année ;
  - visiteurs par an (P1174 : musées, monuments, parcs), la plus récente avec son année ;
  - capacité (P1083 : stades, salles, théâtres).
Seuls les lieux qui ont un nom en français et des coordonnées sont gardés ; chacun est rattaché à la ville
du guide la plus proche (moins de 15 km). Les autres noms français du lieu (« gare de Lyon » pour
« gare de Paris-Gare-de-Lyon ») sont aussi indexés.

Le résultat (chiffres.json.gz) complète l'index des lieux célèbres construit par build.py.
Rythme : chaque semaine, tous les pays (une requête par pays).

  python3 robots/robot_chiffres.py --duree-max 60
  python3 robots/robot_chiffres.py --demo
"""
import argparse, json, math, time, urllib.parse
import commun as c

SPARQL = "https://query.wikidata.org/sparql"
RAYON_KM = 15
DEBUT = time.monotonic()
REQUETE = """SELECT ?i ?l ?coord ?prop ?val ?date WHERE {
  ?pays wdt:P297 "%s" .
  ?i wdt:P17 ?pays .
  { ?i p:P3872 ?st . ?st ps:P3872 ?val . BIND("fr" AS ?prop) OPTIONAL { ?st pq:P585 ?date } }
  UNION { ?i p:P1174 ?st . ?st ps:P1174 ?val . BIND("vi" AS ?prop) OPTIONAL { ?st pq:P585 ?date } }
  UNION { ?i wdt:P1083 ?val . BIND("ca" AS ?prop) }
  ?i wdt:P625 ?coord .
  ?i rdfs:label ?l FILTER(LANG(?l) = "fr")
}"""
ALIAS = """SELECT ?i ?a WHERE { VALUES ?i { %s } ?i skos:altLabel ?a FILTER(LANG(?a) = "fr") }"""


def sparql(requete):
    brut = c.http(SPARQL, donnees=urllib.parse.urlencode({"query": requete, "format": "json"}).encode(), delai=30, timeout=90)
    return json.loads(brut)["results"]["bindings"] if brut else None


def grille(villes):
    g = {}
    for v in villes:
        g.setdefault((int(v["lat"] * 5), int(v["lon"] * 5)), []).append(v)
    return g


def plus_proche(g, lat, lon):
    meilleur, dmin = None, RAYON_KM
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for v in g.get((int(lat * 5) + di, int(lon * 5) + dj), []):
                d = math.hypot((v["lat"] - lat) * 110.57, (v["lon"] - lon) * 111.32 * math.cos(math.radians(lat)))
                if d < dmin:
                    meilleur, dmin = v, d
    return meilleur


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--duree-max", type=int, default=60, help="minutes")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--forcer", action="store_true")
    a = p.parse_args()
    V = [v for v in c.villes() if v.get("lat") is not None]
    g = grille(V)
    pays = sorted({v["pays"] for v in V})
    ancien = c.lire_gz_brut("chiffres.json.gz")
    if isinstance(ancien, dict) and ancien.get("complet") and not a.demo and not a.forcer:
        from datetime import datetime
        try:
            age = (c.maintenant() - datetime.fromisoformat(ancien["complet"])).days
        except (TypeError, ValueError):
            age = 99
        if age < 7:
            print(f"Chiffres relus il y a {age} jours : prochain passage dans {7 - age} jours.")
            return
    lieux = {}
    if isinstance(ancien, dict):  # on garde les pays non relus cette fois (durée maximale atteinte, requête en échec)
        for x in ancien.get("lieux", []):
            lieux[x["q"]] = x
    lus = ech = 0
    for code in (["FR"] if a.demo else pays):
        if time.monotonic() - DEBUT > a.duree_max * 60:
            print("Durée maximale atteinte : la suite passera la prochaine fois.")
            break
        if a.demo:
            v = next((x for x in V if x["nom"] == "Paris"), V[0])
            rep = [{"i": {"value": "http://www.wikidata.org/entity/Q1"}, "l": {"value": "gare d’exemple"},
                    "coord": {"value": f"Point({v['lon']} {v['lat']})"}, "prop": {"value": "fr"}, "val": {"value": "110000000"},
                    "date": {"value": "2023-01-01T00:00:00Z"}}]
        else:
            rep = sparql(REQUETE % code)
        if rep is None:
            ech += 1
            print(f"  {code} : échec")
            time.sleep(10)
            continue
        lus += 1
        trouves = {}
        for r in rep:
            q = r["i"]["value"].rsplit("/", 1)[-1]
            try:
                lon, lat = map(float, r["coord"]["value"][6:-1].split())
                val = float(r["val"]["value"])
            except (ValueError, KeyError):
                continue
            if val <= 0:
                continue
            x = trouves.get(q)
            if not x:
                v = plus_proche(g, lat, lon)
                if not v:
                    continue
                x = trouves[q] = {"q": q, "t": r["l"]["value"], "s": v["slug"], "v": v["nom"], "m": {}}
            prop, an = r["prop"]["value"], int(r["date"]["value"][:4]) if r.get("date") else 0
            if prop == "ca":
                x["m"]["ca"] = max(x["m"].get("ca", 0), int(val))
            elif an >= x["m"].get(prop + "_an", -1):  # la valeur la plus récente
                x["m"][prop], x["m"][prop + "_an"] = int(val), an
        for q, x in trouves.items():
            for k in ("fr", "vi"):
                if x["m"].get(k + "_an") == 0:
                    del x["m"][k + "_an"]
        ids = list(trouves)
        for i in range(0, len(ids), 300):  # autres noms français
            if a.demo:
                break
            r2 = sparql(ALIAS % " ".join("wd:" + q for q in ids[i:i + 300]))
            for r in r2 or []:
                x = trouves[r["i"]["value"].rsplit("/", 1)[-1]]
                al = x.setdefault("a", [])
                if len(al) < 4 and r["a"]["value"].lower() != x["t"].lower():
                    al.append(r["a"]["value"])
        lieux = {q: x for q, x in lieux.items() if x.get("p") != code}
        for q, x in trouves.items():
            x["p"] = code
            lieux[q] = x
        print(f"  {code} : {len(trouves)} lieux")
    if lus:
        fini = lus + ech == len(pays) and not ech
        c.ecrire_gz("chiffres.json.gz", {"date": c.horodatage(), "complet": c.horodatage() if fini else (ancien or {}).get("complet"),
                                         "lieux": list(lieux.values())})
    n = lambda k: sum(1 for x in lieux.values() if k in x["m"])
    c.journal("chiffres", "ok" if not ech else ("partiel" if lus else "échec"), pays_lus=lus, pays_en_echec=ech, lieux=len(lieux),
              frequentation=n("fr"), visiteurs=n("vi"), capacite=n("ca"), mode="démo" if a.demo else "réel")


if __name__ == "__main__":
    main()
