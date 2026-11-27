#!/usr/bin/env python3
"""
Robot Noms : le nom français de chaque ville (« Pise » et non « Pisa », « Cologne » et non « Köln ») et le bon
élément Wikidata de chaque ville.

Source : Wikidata (CC0), par l'identifiant GeoNames de la ville (P1566), par paquets de 250 villes.
Quand plusieurs éléments Wikidata portent le même identifiant GeoNames (la commune, un quartier, une gare…),
le robot garde celui qui a le plus d'articles Wikipédia : c'est la ville elle-même. Le robot Encyclopédie s'en
sert pour corriger ses correspondances (Pisa était rattachée à un mauvais élément), et build.py pour afficher
le nom français. Le nom choisi à la main dans robot_villes.py (NOMS_FR) reste prioritaire.

Rythme : toutes les villes tous les 60 jours.

  python3 robots/robot_noms.py --duree-max 40
"""
import argparse, json, time, urllib.parse
from datetime import datetime
import commun as c

SPARQL = "https://query.wikidata.org/sparql"
FREQUENCE = 60
REQUETE = """SELECT ?gn ?item ?liens ?fr WHERE { VALUES ?gn { %s } ?item wdt:P1566 ?gn ; wikibase:sitelinks ?liens .
  OPTIONAL { ?item rdfs:label ?fr FILTER(LANG(?fr) = "fr") } }"""
DEBUT = time.monotonic()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--duree-max", type=int, default=40, help="minutes")
    a = p.parse_args()
    V = c.villes()
    noms = c.lire_gz_brut("noms.json.gz") or {}
    villes, suivi = noms.get("villes", {}), noms.get("suivi", {})
    t = c.maintenant()
    lot = [str(v["id"]) for v in sorted(V, key=lambda v: -v["population"])
           if not suivi.get(str(v["id"])) or (t - datetime.fromisoformat(suivi[str(v["id"])])).days >= FREQUENCE]
    print(f"{len(lot)} villes à relire.")
    lus = ech = changes = 0
    for i in range(0, len(lot), 250):
        if time.monotonic() - DEBUT > a.duree_max * 60:
            print("Durée maximale atteinte : la suite passera la prochaine fois.")
            break
        paquet = lot[i:i + 250]
        brut = c.http(SPARQL, donnees=urllib.parse.urlencode({"query": REQUETE % " ".join(f'"{g}"' for g in paquet), "format": "json"}).encode(),
                      delai=20, timeout=90)
        if not brut:
            ech += 1
            continue
        meilleur = {}
        for r in json.loads(brut)["results"]["bindings"]:
            g, q, n = r["gn"]["value"], r["item"]["value"].rsplit("/", 1)[-1], int(r["liens"]["value"])
            if g not in meilleur or n > meilleur[g][1]:
                meilleur[g] = (q, n, r.get("fr", {}).get("value", ""))
        h = c.horodatage()
        for g in paquet:
            if g in meilleur:
                q, _, fr = meilleur[g]
                nouveau = [q, fr]
                if villes.get(g) != nouveau:
                    changes += 1
                villes[g] = nouveau
            suivi[g] = h
        lus += len(paquet)
    if lus:
        c.ecrire_gz("noms.json.gz", {"date": c.horodatage(), "villes": villes, "suivi": suivi})
    V_id = {str(v["id"]): v for v in V}
    differents = sum(1 for g, (q, fr) in villes.items() if fr and g in V_id and fr != V_id[g]["nom"])
    print(f"{lus} villes relues, {changes} changements, {differents} villes dont le nom français diffère du nom actuel.")
    c.journal("noms", "ok" if not ech else ("partiel" if lus else "échec"), relues=lus, changements=changes,
              villes=len(villes), noms_francais_differents=differents, paquets_en_echec=ech)


if __name__ == "__main__":
    main()
