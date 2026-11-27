#!/usr/bin/env python3
"""
Robot Encyclopédie : l'histoire et l'identité de chaque ville.

Sources :
  - Wikidata (licence CC0) : date de fondation, anciens noms, surnoms, fondateur, événements datés,
    altitude, superficie, fleuve ou mer, maire actuel, villes jumelées, site officiel, photo,
    blason, drapeau, sites du patrimoine mondial de l'UNESCO, personnalités nées dans la ville ;
  - Wikipédia en français (licence CC BY-SA 4.0) : résumé et grandes sections de l'article
    (Histoire, Géographie, Patrimoine, Culture, Gastronomie, Économie, Sport, Transports) ;
  - Wikimedia Commons : auteur et licence de chaque photo, pour les créditer correctement.

Rythme : villes phares tous les 30 jours, intermédiaires tous les 90 jours, autres tous les 180 jours.
Les textes de Wikipédia sont affichés avec leur source et un lien, comme l'exige leur licence.

  python3 robots/robot_encyclopedie.py --max-villes 300
  python3 robots/robot_encyclopedie.py --ville lisbonne-pt
  python3 robots/robot_encyclopedie.py --demo
"""
import argparse, json, re, time, urllib.parse
from datetime import datetime
import commun as c

SPARQL = "https://query.wikidata.org/sparql"
WIKIDATA = "https://www.wikidata.org/w/api.php"
WIKIPEDIA = "https://fr.wikipedia.org/w/api.php"
COMMONS = "https://commons.wikimedia.org/w/api.php"
FREQUENCE = {"phare": 30, "intermediaire": 90, "autre": 240}
LONGUEUR = {"phare": 14000, "intermediaire": 5000, "autre": 2000}  # caractères max par section
SECTIONS = {  # rubrique du guide -> mots qui peuvent ouvrir la section dans l'article Wikipédia
    "histoire": ("histoire", "historique"),
    "geographie": ("géographie", "situation", "climat", "site"),
    "patrimoine": ("patrimoine", "monuments", "lieux et monuments", "architecture", "urbanisme"),
    "culture": ("culture", "vie culturelle", "arts", "musique", "littérature", "cinéma", "religion"),
    "gastronomie": ("gastronomie", "cuisine", "spécialités culinaires"),
    "economie": ("économie", "activités économiques", "tourisme"),
    "sport": ("sport", "sports"),
    "transports": ("transports", "transport", "voies de communication"),
}


def sparql(requete):
    brut = c.http(SPARQL + "?" + urllib.parse.urlencode({"query": requete, "format": "json"}), delai=20)
    return json.loads(brut)["results"]["bindings"] if brut else None


def api(base, **params):
    params.update(format="json", formatversion=2)
    brut = c.http(base + "?" + urllib.parse.urlencode(params), delai=15)
    return json.loads(brut) if brut else None


def qid_de(uri):
    return uri.rsplit("/", 1)[-1]


# ---------- 1. Correspondance GeoNames -> Wikidata (une fois pour toutes) ----------
def par_nom(v):
    """Recherche l'élément Wikidata d'une ville par son nom, en vérifiant qu'il est à moins de 20 km de ses coordonnées."""
    rep = api(WIKIDATA, action="wbsearchentities", search=v.get("qid_recherche") or v["nom_local"], language="en", type="item", limit=7)
    ids = [x["id"] for x in (rep or {}).get("search", [])]
    if not ids:
        return ""
    rep = api(WIKIDATA, action="wbgetentities", ids="|".join(ids), props="claims")
    for q in ids:
        cl = (rep or {}).get("entities", {}).get(q, {}).get("claims", {})
        for val, _, _ in valeurs(cl, "P625"):
            if isinstance(val, dict) and "latitude" in val:
                t = 0.0174533
                dx = (val["longitude"] - v["lon"]) * 111.32 * abs(__import__("math").cos(v["lat"] * t))
                dy = (val["latitude"] - v["lat"]) * 110.57
                if (dx * dx + dy * dy) ** 0.5 < 20:
                    return q
    return ""


DEBUT = time.monotonic()  # le temps de travail compte dès le lancement (limite de 6 h des machines de GitHub)
LIMITE_S = [300 * 60]


def temps_ecoule():
    return time.monotonic() - DEBUT > LIMITE_S[0]


def correspondances(villes):
    table = c.lire("encyclo/_qid.json", {})
    manquants = [str(v["id"]) for v in villes if str(v["id"]) not in table]
    par_id = {str(x["id"]): x for x in villes}
    for i in range(0, len(manquants), 200):
        lot = manquants[i:i + 200]
        rep = sparql("SELECT ?gn ?item WHERE { VALUES ?gn { %s } ?item wdt:P1566 ?gn . }" % " ".join(f'"{g}"' for g in lot))
        if rep is None:
            break
        for r in rep:
            table.setdefault(r["gn"]["value"], qid_de(r["item"]["value"]))
        for g in lot:
            if g not in table:  # pas d'identifiant GeoNames dans Wikidata : recherche par nom
                v = par_id.get(g)
                if temps_ecoule():
                    break  # la suite de la recherche se fera la nuit prochaine
                table[g] = par_nom(v) if v else ""
        c.ecrire("encyclo/_qid.json", table, compact=True)
        time.sleep(1)
    return table


# ---------- 2. Lecture des fiches Wikidata ----------
def valeurs(claims, prop):
    out = []
    for s in claims.get(prop, []):
        if s.get("rank") == "deprecated":
            continue
        dv = s.get("mainsnak", {}).get("datavalue", {})
        out.append((dv.get("value"), s.get("qualifiers", {}), s.get("rank")))
    return out


def date_wd(v):
    """'+1147-10-25T00:00:00Z', précision -> texte lisible."""
    if not isinstance(v, dict) or "time" not in v:
        return "", None
    t, p = v["time"], v.get("precision", 9)
    m = re.match(r"([+-])(\d+)-(\d\d)-(\d\d)", t)
    if not m:
        return "", None
    an = int(m.group(2)) * (-1 if m.group(1) == "-" else 1)
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    if p <= 7:
        siecle = (abs(an) - 1) // 100 + 1
        texte = f"{siecle}ᵉ siècle" + (" av. J.-C." if an < 0 else "")
    elif p == 8:
        texte = f"années {abs(an) // 10 * 10}" + (" av. J.-C." if an < 0 else "")
    elif p == 9 or m.group(3) == "00":
        texte = f"{abs(an)}" + (" av. J.-C." if an < 0 else "")
    elif p == 10 or m.group(4) == "00":
        texte = f"{mois[int(m.group(3)) - 1]} {abs(an)}"
    else:
        texte = f"{int(m.group(4))} {mois[int(m.group(3)) - 1]} {abs(an)}"
    return texte, an


def libelles(qids):
    noms = {}
    qids = [q for q in dict.fromkeys(qids) if q]
    for i in range(0, len(qids), 50):
        rep = api(WIKIDATA, action="wbgetentities", ids="|".join(qids[i:i + 50]), props="labels", languages="fr|en")
        for q, e in (rep or {}).get("entities", {}).items():
            l = e.get("labels", {})
            noms[q] = (l.get("fr") or l.get("en") or {}).get("value", "")
    return noms


def credit_images(fichiers):
    """Auteur et licence des images Commons."""
    infos = {}
    fichiers = [f for f in dict.fromkeys(fichiers) if f]
    for i in range(0, len(fichiers), 40):
        rep = api(COMMONS, action="query", titles="|".join("File:" + f for f in fichiers[i:i + 40]),
                  prop="imageinfo", iiprop="extmetadata", iiextmetadatafilter="Artist|LicenseShortName")
        for p in (rep or {}).get("query", {}).get("pages", []):
            meta = (p.get("imageinfo") or [{}])[0].get("extmetadata", {})
            auteur = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
            infos[p["title"][5:]] = {"auteur": auteur[:120], "licence": meta.get("LicenseShortName", {}).get("value", "")}
    return infos


def image(nom, largeur=1600):
    n = nom.replace(" ", "_")
    return {"fichier": nom, "url": f"https://commons.wikimedia.org/wiki/Special:FilePath/{urllib.parse.quote(n)}?width={largeur}",
            "page": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(n)}"}


# ---------- 3. Wikipédia ----------
def sections_wikipedia(titre, maxi):
    rep = api(WIKIPEDIA, action="query", prop="extracts|revisions", explaintext=1, rvprop="timestamp", titles=titre, redirects=1)
    pages = (rep or {}).get("query", {}).get("pages", [])
    if not pages or "extract" not in pages[0]:
        return None
    texte = pages[0]["extract"]
    blocs = re.split(r"\n(==+)\s*(.*?)\s*==+\n", "\n" + texte)
    intro = blocs[0].strip()
    out = {"resume": couper(intro, 1600), "sections": {}}
    i = 1
    while i < len(blocs) - 2:
        niveau, titre_s, corps = len(blocs[i]), blocs[i + 1], blocs[i + 2]
        if niveau == 2:
            # rassembler les sous-sections qui suivent
            j = i + 3
            while j < len(blocs) - 2 and len(blocs[j]) > 2:
                corps += "\n\n" + blocs[j + 1] + "\n" + blocs[j + 2]
                j += 3
            t = titre_s.lower()
            for rub, mots in SECTIONS.items():
                if rub not in out["sections"] and any(t.startswith(m) for m in mots):
                    propre = couper(corps.strip(), maxi)
                    if len(propre) > 120:
                        out["sections"][rub] = {"titre": titre_s, "texte": propre}
            i = j
        else:
            i += 3
    return out


def couper(texte, maxi):
    texte = re.sub(r"\n{3,}", "\n\n", texte).strip()
    if len(texte) <= maxi:
        return texte
    coupe = texte[:maxi]
    fin = max(coupe.rfind(". "), coupe.rfind(".\n"))
    return (coupe[:fin + 1] if fin > maxi * 0.6 else coupe) + " […]"


# ---------- 4. Une ville ----------
def traiter(v, qid):
    rep = api(WIKIDATA, action="wbgetentities", ids=qid, props="claims|sitelinks|labels|aliases|descriptions", languages="fr")
    e = (rep or {}).get("entities", {}).get(qid)
    if not e:
        return None
    cl = e.get("claims", {})
    def premier(prop):
        l = valeurs(cl, prop)
        pref = [x for x in l if x[2] == "preferred"]
        return (pref or l or [(None, {}, None)])[0][0]

    fiche = {"qid": qid, "date": c.horodatage(), "description": e.get("descriptions", {}).get("fr", {}).get("value", "")}
    a_nommer = []
    fondation = premier("P571")
    if fondation:
        fiche["fondation"] = date_wd(fondation)[0]
    alt = premier("P2044")
    if isinstance(alt, dict):
        fiche["altitude_m"] = round(float(alt["amount"]))
    sup = premier("P2046")
    if isinstance(sup, dict):
        a = float(sup["amount"])
        if sup.get("unit", "").endswith("Q25343"):  # mètre carré
            a /= 1e6
        elif sup.get("unit", "").endswith("Q35852"):  # hectare
            a /= 100
        fiche["superficie_km2"] = round(a, 1)
    site = premier("P856")
    if isinstance(site, str):
        fiche["site_officiel"] = site
    fiche["surnoms"] = [x[0]["text"] for x in valeurs(cl, "P1449") if isinstance(x[0], dict) and x[0].get("language") == "fr"][:5]
    fiche["anciens_noms"] = list(dict.fromkeys(
        x[0]["text"] for x in valeurs(cl, "P1448") + valeurs(cl, "P1449")
        if isinstance(x[0], dict) and x[1].get("P582")))[:6]
    refs = {}
    for cle, prop, n in (("fondateurs", "P112", 4), ("nommee_d_apres", "P138", 3), ("eaux", "P206", 4), ("jumelages", "P190", 40)):
        ids = [x[0]["id"] for x in valeurs(cl, prop) if isinstance(x[0], dict) and "id" in x[0]][:n]
        refs[cle] = ids
        a_nommer += ids
    maires = [x for x in valeurs(cl, "P6") if isinstance(x[0], dict) and not x[1].get("P582")]
    if maires:
        refs["maire"] = [maires[-1][0]["id"]]
        a_nommer += refs["maire"]
    evenements = []
    for val, qual, _ in valeurs(cl, "P793"):
        if isinstance(val, dict) and "id" in val:
            q = (qual.get("P585") or qual.get("P580") or [{}])[0].get("datavalue", {}).get("value")
            texte, an = date_wd(q) if q else ("", None)
            evenements.append({"qid": val["id"], "date": texte, "an": an})
            a_nommer.append(val["id"])
    for cle in ("P18", "P94", "P41"):
        f = premier(cle)
        if isinstance(f, str):
            fiche[{"P18": "photo", "P94": "blason", "P41": "drapeau"}[cle]] = image(f, 1600 if cle == "P18" else 240)

    noms = libelles(a_nommer)
    for cle, ids in refs.items():
        fiche[cle] = [noms.get(q, "") for q in ids if noms.get(q)]
    if "maire" in fiche:
        fiche["maire"] = fiche["maire"][0] if fiche["maire"] else ""
    fiche["evenements"] = sorted([dict(x, nom=noms.get(x["qid"], "")) for x in evenements if noms.get(x["qid"])],
                                 key=lambda x: (x["an"] is None, x["an"] or 0))[:40]

    # Patrimoine mondial et personnalités (requêtes SPARQL légères, limitées)
    r = sparql('SELECT DISTINCT ?s ?sLabel WHERE { ?s wdt:P1435 wd:Q9259 ; wdt:P131 wd:%s . '
               'SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". } } LIMIT 20' % qid)
    fiche["unesco"] = sorted({x["sLabel"]["value"] for x in (r or []) if not re.match(r"Q\d+$", x["sLabel"]["value"])})
    if v["niveau"] in ("phare", "intermediaire"):
        r = sparql('SELECT ?p ?pLabel ?d ?naissance ?liens WHERE { ?p wdt:P19 wd:%s ; wikibase:sitelinks ?liens . '
                   'OPTIONAL { ?p wdt:P569 ?naissance } OPTIONAL { ?p schema:description ?d FILTER(LANG(?d) = "fr") } '
                   'SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". } } ORDER BY DESC(?liens) LIMIT 12' % qid)
        fiche["personnalites"] = [{"nom": x["pLabel"]["value"], "description": x.get("d", {}).get("value", ""),
                                   "naissance": x.get("naissance", {}).get("value", "")[:4].lstrip("+")}
                                  for x in (r or []) if not re.match(r"Q\d+$", x["pLabel"]["value"])][:12]

    # Crédits des images
    fichiers = [fiche[k]["fichier"] for k in ("photo", "blason", "drapeau") if k in fiche]
    credits = credit_images(fichiers)
    for k in ("photo", "blason", "drapeau"):
        if k in fiche:
            fiche[k].update(credits.get(fiche[k]["fichier"].replace("_", " "), credits.get(fiche[k]["fichier"], {})))

    # Wikipédia
    titre = e.get("sitelinks", {}).get("frwiki", {}).get("title")
    if titre:
        wp = sections_wikipedia(titre, LONGUEUR[v["niveau"]])
        if wp:
            fiche["wikipedia"] = dict(wp, titre=titre, url="https://fr.wikipedia.org/wiki/" + urllib.parse.quote(titre.replace(" ", "_")))
    return fiche


def demo(v):
    t = "Texte d’exemple produit en mode démo. Sur le vrai site, cette section reprend l’article Wikipédia de la ville. "
    return {"qid": "Q0", "date": c.horodatage(), "description": "ville d’exemple (mode démo)", "fondation": "VIIIᵉ siècle av. J.-C.",
            "altitude_m": 45, "superficie_km2": 100.1, "surnoms": ["La ville aux exemples"], "anciens_noms": ["Exemplum"],
            "fondateurs": [], "eaux": ["Fleuve d’exemple"], "jumelages": ["Ville jumelle A", "Ville jumelle B", "Ville jumelle C"],
            "maire": "Maire d’exemple", "site_officiel": "https://exemple.org",
            "evenements": [{"nom": "Fondation d’exemple", "date": "1147", "an": 1147}, {"nom": "Grand événement d’exemple", "date": "1 novembre 1755", "an": 1755},
                           {"nom": "Exposition d’exemple", "date": "1998", "an": 1998}],
            "unesco": ["Site du patrimoine d’exemple"],
            "personnalites": [{"nom": "Personnalité d’exemple", "description": "écrivain d’exemple", "naissance": "1888"}],
            "wikipedia": {"titre": v["nom"], "url": "https://fr.wikipedia.org/wiki/" + v["nom_local"], "resume": t * 2,
                          "sections": {"histoire": {"titre": "Histoire", "texte": (t * 4 + "\n\n") * 3},
                                       "culture": {"titre": "Culture", "texte": t * 3},
                                       "gastronomie": {"titre": "Gastronomie", "texte": t * 2}}}}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-villes", type=int, default=8000)
    p.add_argument("--duree-max", type=float, default=290, help="minutes depuis le lancement : au-delà, arrêt propre")
    p.add_argument("--ville")
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    V = c.villes()
    suivi = c.lire("encyclo/_suivi.json", {})
    t = c.maintenant()
    if not a.demo:  # correspondances corrigées par le robot Noms (élément Wikidata qui a le plus d'articles) : fiche à refaire
        noms = (c.lire_gz_brut("noms.json.gz") or {}).get("villes", {})
        table = c.lire("encyclo/_qid.json", {}) or {}
        corrigees = 0
        for g, x in noms.items():
            if x and x[0] and table.get(g) and table[g] != x[0]:
                table[g] = x[0]
                suivi.pop(g, None)
                corrigees += 1
        if corrigees:
            c.ecrire("encyclo/_qid.json", table, compact=True)
            c.ecrire("encyclo/_suivi.json", suivi, compact=True)
            print(f"{corrigees} villes rattachées à un meilleur élément Wikidata : leur fiche sera refaite.")
    if a.ville:
        lot = [v for v in V if v["slug"] == a.ville]
    elif a.demo:
        lot = [v for v in V if v["slug"] in ("lisbonne-pt", "porto-pt", "tokyo-jp")]
    else:
        dues = []
        for v in V:
            d = suivi.get(str(v["id"]))
            retard = (t - datetime.fromisoformat(d)).days - FREQUENCE[v["niveau"]] if d else 10**6
            if retard >= 0:
                dues.append(({"phare": 0, "intermediaire": 1, "autre": 2}[v["niveau"]], -retard, -v["population"], v))
        dues.sort(key=lambda x: x[:3])
        lot = [x[3] for x in dues[:a.max_villes]]
    print(f"{len(lot)} ville(s) à traiter.")
    LIMITE_S[0] = a.duree_max * 60
    table = {} if a.demo else correspondances(lot)
    ok = sans = ech = 0
    for n, v in enumerate(lot, 1):
        if temps_ecoule():
            print("Durée maximale atteinte : la suite passera la nuit prochaine.")
            break
        qid = table.get(str(v["id"]))
        if not a.demo and not qid:
            sans += 1
            suivi[str(v["id"])] = t.isoformat()
            continue
        try:
            fiche = demo(v) if a.demo else traiter(v, qid)
        except Exception as err:  # une fiche Wikidata atypique ne doit pas arrêter le robot
            print(f"    {v['nom']} : {err}")
            fiche = None
        if fiche is None:
            ech += 1
            continue
        c.ecrire(f"encyclo/{v['id']}.json", fiche, compact=True)
        suivi[str(v["id"])] = t.isoformat()
        c.ecrire("encyclo/_suivi.json", suivi, compact=True)
        ok += 1
        print(f"[{n}/{len(lot)}] {v['nom']} : {len(fiche.get('evenements', []))} événements, "
              f"{len(fiche.get('wikipedia', {}).get('sections', {}))} sections Wikipédia")
        if not a.demo:
            time.sleep(0.3)
    c.journal("encyclopedie", "ok" if ech == 0 else "partiel", villes_a_jour=ok, sans_wikidata=sans, echecs=ech,
              villes_couvertes=len(suivi), mode="démo" if a.demo else "réel")
    print(f"Encyclopédie : {ok} villes à jour, {sans} sans fiche Wikidata, {ech} échecs.")


if __name__ == "__main__":
    main()
