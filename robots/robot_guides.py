#!/usr/bin/env python3
"""
Robot Guides : les conseils de voyage de Wikivoyage en français (licence CC BY-SA), le guide de voyage libre
écrit par des voyageurs : Comprendre, S'y rendre, Se déplacer, Voir, Faire, Acheter, Manger, Sortir, Se loger,
Sécurité, Santé, Aux environs… Repris par sections, avec lien vers l'article et mention de la licence.

Les villes sont retrouvées grâce à leur élément Wikidata (fichier encyclo/_qid.json du robot Encyclopédie).
Rythme : villes phares tous les 30 jours, intermédiaires tous les 90 jours, autres tous les 180 jours.

  python3 robots/robot_guides.py --max-villes 5000
  python3 robots/robot_guides.py --demo
"""
import argparse, json, re, time, urllib.parse
from datetime import datetime
import commun as c

WIKIDATA = "https://www.wikidata.org/w/api.php"
WIKIVOYAGE = "https://fr.wikivoyage.org/w/api.php"
FREQUENCE = {"phare": 30, "intermediaire": 90, "autre": 180}
LONGUEUR = {"phare": 9000, "intermediaire": 4500, "autre": 2500}
SECTIONS = {  # clé -> titres possibles dans Wikivoyage (début du titre, sans accents)
    "comprendre": ("comprendre",), "aller": ("aller", "se rendre", "arriver"), "circuler": ("circuler", "se deplacer"),
    "voir": ("voir", "a voir"), "faire": ("faire", "a faire", "activites"), "acheter": ("acheter", "achats"),
    "manger": ("manger",), "sortir": ("boire un verre", "sortir", "vie nocturne"), "loger": ("se loger", "logement", "dormir"),
    "securite": ("securite", "rester en securite"), "sante": ("sante",), "communiquer": ("communiquer", "rester en contact"),
    "respecter": ("respecter", "coutumes"), "environs": ("aux environs", "alentours", "environs", "aller plus loin"),
}


def api(base, **q):
    q.update(format="json", formatversion=2)
    brut = c.http(base + "?" + urllib.parse.urlencode(q), delai=15)
    return json.loads(brut) if brut else None


def sans_accents(t):
    import unicodedata
    return unicodedata.normalize("NFD", t.lower()).encode("ascii", "ignore").decode()


def couper(t, n):
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    if len(t) <= n:
        return t
    x = t[:n]
    fin = max(x.rfind(". "), x.rfind(".\n"))
    return (x[:fin + 1] if fin > n * 0.6 else x) + " […]"


def decouper(texte, maxi):
    blocs = re.split(r"\n(==+)\s*(.*?)\s*==+\n", "\n" + texte)
    out = {}
    i = 1
    while i < len(blocs) - 2:
        if len(blocs[i]) == 2:
            titre, corps = blocs[i + 1], blocs[i + 2]
            j = i + 3
            while j < len(blocs) - 2 and len(blocs[j]) > 2:
                corps += "\n\n" + blocs[j + 1] + "\n" + blocs[j + 2]
                j += 3
            t = sans_accents(titre)
            for cle, mots in SECTIONS.items():
                if cle not in out and any(t.startswith(m) for m in mots):
                    propre = couper(corps.strip(), maxi)
                    if len(propre) > 80:
                        out[cle] = {"titre": titre, "texte": propre}
            i = j
        else:
            i += 3
    intro = couper(blocs[0].strip(), 1200)
    return intro, out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-villes", type=int, default=5000)
    p.add_argument("--duree-max", type=float, default=320)
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    V = c.villes()
    suivi = c.lire("guides/_suivi.json", {}) or {}
    qids = c.lire("encyclo/_qid.json", {}) or {}
    t0 = c.maintenant()
    if a.demo:
        lot = [v for v in V if v["slug"] in ("porto-pt", "tokyo-jp")]
    else:
        dues = []
        for v in V:
            q = qids.get(str(v["id"]))
            if not q:
                continue
            d = suivi.get(str(v["id"]), {}).get("date")
            retard = (t0 - datetime.fromisoformat(d)).days - FREQUENCE[v["niveau"]] if d else 10**6
            if retard >= 0:
                dues.append(({"phare": 0, "intermediaire": 1, "autre": 2}[v["niveau"]], -retard, -v["population"], v))
        dues.sort(key=lambda x: x[:3])
        lot = [x[3] for x in dues[:a.max_villes]]
    print(f"{len(lot)} ville(s) à traiter.")
    debut, ok, sans, ech = time.monotonic(), 0, 0, 0
    for k in range(0, len(lot), 50):
        if time.monotonic() - debut > a.duree_max * 60:
            print("Durée maximale atteinte : la suite passera la nuit prochaine.")
            break
        paquet = lot[k:k + 50]
        if a.demo:
            titres = {v["id"]: v["nom"] for v in paquet}
        else:
            rep = api(WIKIDATA, action="wbgetentities", ids="|".join(qids[str(v["id"])] for v in paquet), props="sitelinks", sitefilter="frwikivoyage")
            ents = (rep or {}).get("entities", {})
            titres = {}
            for v in paquet:
                sl = ents.get(qids[str(v["id"])], {}).get("sitelinks", {}).get("frwikivoyage")
                if sl:
                    titres[v["id"]] = sl["title"]
        for v in paquet:
            titre = titres.get(v["id"])
            if not titre:
                sans += 1
                suivi[str(v["id"])] = {"date": t0.isoformat(), "article": False}
                continue
            if a.demo:
                texte = ("Porto est une ville d’exemple (mode démo).\n\n== Comprendre ==\nTexte d’exemple pour comprendre la ville, assez long pour être gardé. " * 3
                         + "\n\n== Aller ==\nEn avion, en train ou en bus : texte d’exemple suffisamment long pour être conservé dans le guide.\n\n"
                         + "== Manger ==\nSpécialités et adresses d’exemple, avec assez de texte pour être conservées dans la fiche de la ville.\n")
            else:
                rep = api(WIKIVOYAGE, action="query", prop="extracts", explaintext=1, titles=titre, redirects=1)
                pages = (rep or {}).get("query", {}).get("pages", [])
                texte = pages[0].get("extract") if pages else None
                if texte is None:
                    ech += 1
                    continue
            intro, sections = decouper(texte, LONGUEUR[v["niveau"]])
            if sections or len(intro) > 200:
                c.ecrire_gz(f"guides/{v['id']}.json.gz", {"date": c.horodatage(), "titre": titre, "intro": intro,
                            "url": "https://fr.wikivoyage.org/wiki/" + urllib.parse.quote(titre.replace(" ", "_")), "sections": sections})
                ok += 1
            else:
                sans += 1
            suivi[str(v["id"])] = {"date": t0.isoformat(), "article": True, "sections": len(sections)}
            if not a.demo:
                time.sleep(0.3)
        c.ecrire("guides/_suivi.json", suivi, compact=True)
    c.journal("guides", "ok" if ech == 0 else "partiel", villes_avec_guide=ok, sans_article=sans, echecs=ech,
              villes_suivies=len(suivi), mode="démo" if a.demo else "réel")
    print(f"Guides : {ok} villes avec un guide, {sans} sans article Wikivoyage, {ech} échecs.")


if __name__ == "__main__":
    main()
