#!/usr/bin/env python3
"""
Dix Mille Escales – générateur du site.

Lit les données (data/) produites par les robots et fabrique le site complet dans le dossier site/ :
  - la page d'accueil avec la carte des villes ;
  - une page par ville (villes/<nom-pays>/), ou la page rédigée à la main si elle existe dans pages/ ;
  - l'index de recherche, les pages « Nos sources » et « État des robots », le plan du site.

  python3 build.py                  # génère tout
  python3 build.py --limite 50      # seulement les 50 premières villes (test rapide)
Variable facultative : SITE_URL (ex. https://dixmilleescales.fr) pour le plan du site.
"""
import argparse, gzip, html, json, math, os, re, shutil, sys
from datetime import date, datetime, timezone

RACINE = os.path.dirname(os.path.abspath(__file__))
DATA, SITE = os.path.join(RACINE, "data"), os.path.join(RACINE, "site")
DONNEES = os.environ.get("DME_DONNEES") or os.path.join(RACINE, "donnees")  # données des robots (branches donnees-…)
LIMITE_SITE = 950 * 1024 * 1024  # GitHub Pages accepte 1 Go : alerte au-delà de 950 Mo
EN_LIGNE = {"phare": 30, "intermediaire": 15, "autre": 8}  # adresses écrites dans la page par rubrique ; la suite se charge à la demande
SECTIONS_AUTRES = ("histoire", "patrimoine", "gastronomie")  # petites villes : sections Wikipédia gardées dans la page
E = html.escape
CONTINENTS = {"EU": "Europe", "AF": "Afrique", "AS": "Asie", "NA": "Amérique du Nord et centrale",
              "SA": "Amérique du Sud", "OC": "Océanie", "AN": "Antarctique"}
NIVEAUX = {"phare": "Ville phare", "intermediaire": "Ville intermédiaire", "autre": "Ville du guide"}
FREQ = {"phare": "chaque semaine", "intermediaire": "chaque mois", "autre": "tous les trois mois"}
RUBRIQUES = [("voir", "À voir", "Monuments, musées, belvédères, parcs et sites recensés autour du centre-ville."),
             ("manger", "Manger et boire", "Restaurants, cafés, bars et glaciers."),
             ("dormir", "Dormir", "Hôtels, auberges de jeunesse et maisons d’hôtes."),
             ("faire", "Activités", "Plages, baignade, sports nautiques, parcs d’attractions, golf, ski et autres loisirs."),
             ("acheter", "Acheter", "Marchés, librairies, épiceries fines, artisanat et souvenirs."),
             ("bouger", "Gares et stations", "Gares, stations, gares routières et terminaux de ferry.")]
GUIDE = [("comprendre", "Comprendre {ville}"), ("aller", "S’y rendre"), ("circuler", "Se déplacer"), ("voir", "Le guide : que voir"),
         ("faire", "Le guide : que faire"), ("manger", "Le guide : où manger"), ("sortir", "Sortir le soir"), ("loger", "Le guide : où dormir"),
         ("acheter", "Le guide : shopping"), ("securite", "Sécurité sur place"), ("sante", "Santé"), ("communiquer", "Communiquer"),
         ("respecter", "Coutumes et savoir-vivre"), ("environs", "Le guide : aux environs")]
MAX_PAR_RUBRIQUE = 250
METEO = [((0,), "Ensoleillé"), ((1, 2), "Peu nuageux"), ((3,), "Couvert"), ((45, 48), "Brouillard"),
         ((51, 53, 55, 56, 57), "Bruine"), ((61, 63, 65, 66, 67), "Pluie"), ((71, 73, 75, 77), "Neige"),
         ((80, 81, 82), "Averses"), ((85, 86), "Averses de neige"), ((95, 96, 99), "Orage")]
JOURS = {"Mo": "lun", "Tu": "mar", "We": "mer", "Th": "jeu", "Fr": "ven", "Sa": "sam", "Su": "dim",
         "PH": "jours fériés", "off": "fermé", "24/7": "24 h/24, 7 j/7"}
UE = set("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE IS LI NO CH".split())
NIVEAU_ALERTE = {1: ("Précautions normales", "#2F7D6D"), 2: ("Vigilance renforcée", "#C99A00"),
                 3: ("Voyage déconseillé sauf raison impérative", "#D9822B"), 4: ("Voyage formellement déconseillé", "#B5485D")}
PASSEPORTS = {"FR": "Passeport français", "BE": "Passeport belge", "CH": "Passeport suisse", "CA": "Passeport canadien"}
DIPLO = "https://www.diplomatie.gouv.fr/fr/conseils-aux-voyageurs/conseils-par-pays-destination/"
MOIS_LONG = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
LOGO = ('<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" '
        'stroke-width="2"/><path d="M2 12h20M12 2c3 3.2 3 16.8 0 20M12 2c-3 3.2-3 16.8 0 20" fill="none" '
        'stroke="currentColor" stroke-width="1.4"/><circle cx="15.5" cy="8" r="2.6" fill="#F2B705"/></svg>')
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,800'
         '&family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,600;1,7..72,400&display=swap" rel="stylesheet">')


def lire(nom, defaut=None):
    for base in (DONNEES, DATA):
        p = os.path.join(base, nom)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    return defaut


def lire_gz(nom):
    for base in (DONNEES, DATA):
        p = os.path.join(base, nom)
        if os.path.exists(p):
            with gzip.open(p, "rt", encoding="utf-8") as f:
                return json.load(f)
    return None


def ecrire_gz(chemin, objet):
    """Fichier JSON compressé (5 à 10 fois plus léger), décompressé par le navigateur."""
    p = os.path.join(SITE, chemin)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(gzip.compress(json.dumps(objet, ensure_ascii=False, separators=(",", ":")).encode(), 9, mtime=0))


def ecrire(chemin, texte):
    p = os.path.join(SITE, chemin)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(texte)


def nombre(n):
    return f"{n:,}".replace(",", "\u202f")


def dist(a, b):
    t = math.pi / 180
    x = (math.sin((b[0] - a[0]) * t / 2) ** 2 +
         math.cos(a[0] * t) * math.cos(b[0] * t) * math.sin((b[1] - a[1]) * t / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(x))


def date_fr(iso):
    try:
        d = date.fromisoformat(iso[:10])
        return f"{d.day} {MOIS[d.month - 1]} {d.year}"
    except Exception:
        return iso


def horaires_fr(h):
    for k, v in JOURS.items():
        h = h.replace(k, v)
    return h.replace(";", " ; ").replace(",", ", ")


def texte_html(t, ouvert=3):
    """Texte brut Wikipédia -> paragraphes ; les lignes courtes sans point deviennent des intertitres.
    Les premiers paragraphes sont visibles, la suite est repliée."""
    blocs = []
    for ligne in [x.strip() for x in t.split("\n") if x.strip()]:
        if len(ligne) < 70 and not ligne.endswith((".", ":", "»", ")", "]")):
            blocs.append(f"<h4>{E(ligne)}</h4>")
        else:
            blocs.append(f"<p>{E(ligne)}</p>")
    paras = [i for i, b in enumerate(blocs) if b.startswith("<p>")]
    if len(paras) <= ouvert + 1:
        return '<div class="prose">' + "".join(blocs) + "</div>"
    coupe = paras[ouvert]
    return ('<div class="prose">' + "".join(blocs[:coupe]) + '<details class="more"><summary>Lire la suite</summary>'
            + "".join(blocs[coupe:]) + "</details></div>")


def formalite_fr(val, passeport, dest):
    if dest == passeport or val == "-1":
        return "Ressortissants du pays"
    if passeport in UE and dest in UE and passeport != "CH" or (passeport == "CH" and dest in UE):
        return "Libre circulation : carte d’identité ou passeport"
    if val.isdigit():
        return f"Sans visa, séjour jusqu’à {val} jours"
    return {"visa free": "Sans visa", "visa on arrival": "Visa délivré à l’arrivée",
            "eta": "Autorisation électronique à demander avant le départ (type ESTA ou ETA)",
            "e-visa": "Visa électronique à demander en ligne avant le départ",
            "visa required": "Visa obligatoire, à demander auprès de l’ambassade",
            "no admission": "Entrée non autorisée actuellement"}.get(val, val or "Information non disponible")


def meilleurs_mois(mois):
    """Mois agréables pour visiter : chaleur modérée et peu de jours de pluie."""
    out = []
    for i, m in enumerate(mois):
        if m["tmax"] is None:
            continue
        jp = m.get("jours_pluie")
        sec_ = jp <= 8 if jp is not None else m["pluie_mm"] <= 70       # sans nombre de jours de pluie : cumul mensuel
        assez_sec = jp <= 13 if jp is not None else m["pluie_mm"] <= 130
        if 18 <= m["tmax"] <= 29 and sec_:
            out.append((i, "ideal"))
        elif 12 <= m["tmax"] <= 33 and assez_sec:
            out.append((i, "possible"))
    return dict(out)


def qualite_air(i):
    for seuil, t in ((20, "bonne"), (40, "correcte"), (60, "moyenne"), (80, "médiocre"), (100, "mauvaise")):
        if i <= seuil:
            return t
    return "très mauvaise"


def fmt_prix(x):
    if x < 10:
        return f"{x:.1f} €".replace(".", ",")
    return f"{round(x / 5) * 5 if x > 40 else round(x)} €"


CARTE_BOUTON = ('<div class="carte-zone" data-lat="{lat}" data-lon="{lon}" data-rayon="{rayon}"><button type="button" class="tout-voir carte-ouvrir">'
                'Ouvrir la carte interactive (zoom, tous les lieux, détails)</button></div>')
BOITE_QUESTIONS = ('<section class="block questions" id="questions" data-ville="{slug}"><h2>Une question sur {nom} ?</h2>'
                   '<form class="q-form" onsubmit="return false"><label for="question" class="vh">Votre question</label>'
                   '<input id="question" class="q-input" type="text" autocomplete="off" placeholder="Par exemple : faut-il un visa ? Quel temps en avril ?">'
                   '<button type="submit" class="q-btn">Demander</button></form><div class="q-sugg"></div><div class="q-rep" aria-live="polite"></div></section>')


def couper_txt(t, n):
    t = " ".join(t.split())
    if len(t) <= n:
        return t
    c = t[:n]
    fin = c.rfind(". ")
    return (c[:fin + 1] if fin > n * 0.5 else c) + " […]"


def maj(t):
    return t[:1].upper() + t[1:]


def meteo_fr(code):
    return next((t for codes, t in METEO if code in codes), "Variable")


def page(root, titre, description, corps, recherche=True):
    """Gabarit commun à toutes les pages générées. root = chemin relatif vers la racine du site."""
    rech = ('<form class="search" role="search" onsubmit="return false"><label for="q" class="vh">Chercher une ville</label>'
            '<input id="q" type="search" autocomplete="off" placeholder="Chercher une ville">'
            '<ul id="results"></ul></form>') if recherche else ""
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(titre)}</title><meta name="description" content="{E(description)}">
{FONTS}<link rel="stylesheet" href="{root}static/style.css"></head>
<body data-root="{root}">
<header class="top"><div class="top-in"><a class="brand" href="{root}">{LOGO}Dix Mille Escales</a><a class="nav-pays" href="{root}pays/">Pays</a><a class="nav-pays" href="{root}outils/">Outils</a>{rech}
<button type="button" class="theme-btn" id="theme-btn" aria-label="Changer le thème d’affichage">Thème : auto</button></div></header>
<main class="wrap">{corps}</main>
<footer class="foot"><div class="in"><p>Dix Mille Escales, le guide de toutes les villes du monde de plus de 5 000 habitants. Données mises à jour chaque nuit par nos robots.</p>
<p><span data-compteur>…</span> informations dans le guide · <a href="{root}sources/">Nos sources</a> · <a href="{root}etat/">État des robots</a> · <a href="{root}mentions-legales/">Mentions légales</a></p></div></footer>
<script src="{root}static/app.js"></script><script src="{root}static/fiche.js"></script><script src="{root}static/questions.js"></script><script src="{root}static/lieux.js"></script><script src="{root}static/onglets.js"></script><script src="{root}static/carte.js"></script><script src="{root}static/carnet.js"></script></body></html>"""


def carte_lieux(v, lieux, rayon):
    """Petite carte SVG des lieux autour du centre-ville (sans fond de carte externe)."""
    if not lieux:
        return ""
    W = H = 600
    k = math.cos(v["lat"] * math.pi / 180)
    def xy(f):
        dx = (f["lon"] - v["lon"]) * 111.32 * k
        dy = (f["lat"] - v["lat"]) * 110.57
        return W / 2 + dx / rayon * (W / 2 - 20), H / 2 - dy / rayon * (H / 2 - 20)
    pts = []
    for f in lieux[:3000]:
        x, y = xy(f)
        if 0 <= x <= W and 0 <= y <= H:
            pts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="var(--{f["rubrique"]})" fill-opacity=".85">'
                       f'<title>{E(f["nom"])} · {E(f["type"])}</title></circle>')
    km = 1 if rayon <= 5 else 2
    barre = km / rayon * (W / 2 - 20)
    return (f'<figure class="placemap" style="margin:0"><svg viewBox="0 0 {W} {H}" role="img" aria-label="Carte des lieux recensés autour du centre de {E(v["nom"])}">'
            f'<circle cx="{W/2}" cy="{H/2}" r="{W/2-20}" fill="none" stroke="var(--grid)" stroke-width="1.5"/>'
            f'<circle cx="{W/2}" cy="{H/2}" r="{(W/2-20)/2}" fill="none" stroke="var(--grid)" stroke-dasharray="4 6"/>'
            + "".join(pts) +
            f'<circle cx="{W/2}" cy="{H/2}" r="7" fill="var(--buoy)" stroke="var(--ink)" stroke-width="2"/>'
            f'<line x1="24" y1="{H-24}" x2="{24+barre:.1f}" y2="{H-24}" stroke="var(--ink)" stroke-width="3"/>'
            f'<text x="24" y="{H-32}" font-family="system-ui" font-size="14" fill="var(--muted)">{km} km</text></svg>'
            '<figcaption class="legend"><span style="--c:var(--buoy)">Centre-ville</span><span style="--c:var(--voir)">À voir</span>'
            '<span style="--c:var(--manger)">Manger et boire</span><span style="--c:var(--dormir)">Dormir</span>'
            '<span style="--c:var(--faire)">Activités</span><span style="--c:var(--acheter)">Acheter</span></figcaption></figure>')


def liste_lieux(rub, items, niveau="phare"):
    items = sorted(items, key=lambda f: (-f["infos"], f["nom"]))
    def li(f):
        meta = " · ".join(x for x in (f["type"], f.get("cuisine"), (f["etoiles"] + " étoiles") if f.get("etoiles") else "",
                                      "payant" if f.get("payant") == "oui" else "gratuit" if f.get("payant") == "non" else "",
                                      "accessible en fauteuil" if f.get("fauteuil") == "oui" else "",
                                      "terrasse" if f.get("terrasse") == "oui" else "",
                                      "service d’urgences" if f.get("urgences") == "oui" else "") if x)
        infos = []
        if f.get("adresse"):
            infos.append(E(f["adresse"]))
        if f.get("horaires"):
            infos.append("Horaires : " + E(horaires_fr(f["horaires"])))
        liens = []
        if f.get("site", "").startswith("http"):
            liens.append(f'<a href="{E(f["site"])}" rel="nofollow noopener" target="_blank">Site</a>')
        if f.get("telephone"):
            liens.append(f'<a href="tel:{E(f["telephone"].replace(" ", ""))}">{E(f["telephone"])}</a>')
        typ, ident = f["id"][4:].split("/")
        liens.append(f'<a href="https://www.openstreetmap.org/{typ}/{ident}" rel="nofollow noopener" target="_blank">Carte</a>')
        return (f'<li data-type="{E(f["type"])}" style="--c:var(--{rub})"><h3>{E(f["nom"])}</h3><div class="m">{E(meta)}</div>'
                + "".join(f'<div class="i">{x}</div>' for x in infos) + f'<div class="i">{" · ".join(liens)}</div></li>')
    visibles = items[:EN_LIGNE.get(niveau, 15)]
    html_ = f'<ul class="places" id="l-{rub}">' + "".join(li(f) for f in visibles) + "</ul>"
    if len(items) > len(visibles):
        html_ += (f'<button type="button" class="tout-voir" data-rub="{rub}" data-n="{len(items)}">Voir les {nombre(len(items))} adresses, '
                  f'avec recherche et filtres</button>')
    return html_


def lieux_ville(chemins):
    """Lit et fusionne les fichiers de lieux d'une ville (plusieurs robots ou régions peuvent l'avoir servie)."""
    if not chemins:
        return None
    res = None
    for p in chemins:
        ouvrir = gzip.open if p.endswith(".gz") else open
        try:
            with ouvrir(p, "rt", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if res is None:
            res = d
            continue
        fusion = {x["id"]: x for x in res["lieux"]}
        fusion.update({x["id"]: x for x in d["lieux"]})
        res = dict(res, lieux=list(fusion.values()), date=max(res.get("date", ""), d.get("date", "")),
                   rayon_km=d.get("rayon_km") or res.get("rayon_km"), rayon_alentours_km=d.get("rayon_alentours_km") or res.get("rayon_alentours_km"))
    return res


def page_ville(v, ctx):
    pays = ctx["pays"].get(v["pays"], {})
    nom_pays = pays.get("nom", v["pays"])
    cont = CONTINENTS.get(pays.get("continent", ""), "")
    rubs = lieux_ville(ctx["lieux"].get(v["id"]))
    tous = rubs["lieux"] if rubs else []
    lieux = [f for f in tous if f["rubrique"] != "alentours"]
    autour = sorted([f for f in tous if f["rubrique"] == "alentours"], key=lambda f: f.get("distance_km", 0))
    meteo = lire(f"meteo/{v['id']}.json")
    enc = lire(f"encyclo/{v['id']}.json") or {}
    guide = lire_gz(f"guides/{v['id']}.json.gz") or {}
    gs = guide.get("sections", {})
    aeros = ctx["aeroports"].get(str(v["id"]), [])
    clim = (lire(f"climat/{v['id']}.json") or {})
    red = lire(f"redaction/{v['id']}.json") or {}
    alerte = ctx["securite"].get("pays", {}).get(v["pays"])
    cout = ctx["cout"].get("pays", {}).get(v["pays"])
    wp = enc.get("wikipedia") or {}
    wps = wp.get("sections", {})
    if v["niveau"] == "autre":
        wps = {k: x for k, x in wps.items() if k in SECTIONS_AUTRES}
    feries = ctx["feries"].get(v["pays"])
    d_paris = dist((48.8566, 2.3522), (v["lat"], v["lon"]))
    trajet = (f"≈ {nombre(round(d_paris))} km, train ou voiture" if d_paris < 350
              else f"≈ {nombre(int(round(d_paris, -1)))} km à vol d’oiseau, ≈ {max(1, round(d_paris / 800 + .5))} h de vol")
    devise = pays.get("monnaie", "")
    change = ""
    if devise and devise != "EUR" and devise in ctx["change"].get("taux", {}):
        t = ctx["change"]["taux"][devise]
        change = f"1 € = {t:,.2f} {devise}".replace(",", "\u202f").replace(".", ",")
    capitale = ctx["capitales"].get(v["pays"], pays.get("capitale", ""))
    infos_base = 12 + sum(1 for k in ("fondation", "altitude_m", "superficie_km2", "maire", "site_officiel") if enc.get(k)) \
        + len(enc.get("evenements", [])) * 2 + len(enc.get("jumelages", [])) + len(enc.get("unesco", [])) \
        + len(enc.get("personnalites", [])) * 3 + len(enc.get("surnoms", [])) + len(enc.get("anciens_noms", [])) \
        + sum(max(1, len(x["texte"]) // 300) for x in wps.values()) + (1 if wp.get("resume") else 0) + (1 if enc.get("photo") else 0) \
        + (60 if clim.get("mois") else 0) + (8 if cout else 0) + (4 if ctx["formalites"] else 0) + (1 if alerte else 0) \
        + sum(len(red.get(k, [])) for k in ("pourquoi", "conseils", "a_eviter", "un_jour", "trois_jours")) + (3 if red else 0) \
        + sum(max(1, len(x["texte"]) // 300) for x in gs.values()) + len(aeros) * 4
    total_infos = infos_base + sum(f["infos"] + (2 if f.get("distance_km") else 0) for f in tous) + (len(meteo["jours"]) * 4 if meteo else 0) + (len(feries["jours"]) * 2 if feries else 0)
    coords = (f'{abs(v["lat"]):.2f}° {"N" if v["lat"] >= 0 else "S"} / {abs(v["lon"]):.2f}° {"E" if v["lon"] >= 0 else "O"}').replace(".", ",")
    badge = f'<span class="badge">{NIVEAUX[v["niveau"]]}</span>' if v["niveau"] == "phare" else ""

    facts = [("Pays", nom_pays), ("Habitants", nombre(v["population"])), ("Rang dans le guide", f'{nombre(v["rang"])}ᵉ ville'),
             ("Heure locale", f'<span data-tz="{E(v["fuseau"])}">–</span>'), ("Décalage", f'<span data-offset="{E(v["fuseau"])}">–</span>'),
             ("Saison", f'<span data-season="{v["lat"]}">–</span>'),
             ("Soleil aujourd’hui", f'<span data-sun="{v["lat"]},{v["lon"]}" data-suntz="{E(v["fuseau"])}">–</span>'),
             ("Depuis Paris", trajet)]
    pr = ctx["pratique"].get(v["pays"], {})
    if pr.get("prises"):
        facts.append(("Prises électriques", "type " + ", ".join(pr["prises"]) + (f' · {pr["tension"]} V' if pr.get("tension") else "")
                      + (f', {pr["frequence"]} Hz' if pr.get("frequence") else "") + (" (pas d’adaptateur pour les prises françaises)" if set(pr["prises"]) <= {"C", "E", "F"} else " (adaptateur nécessaire)")))
    if pr.get("conduite"):
        facts.append(("Conduite", "à " + pr["conduite"]))
    if aeros:
        facts.append(("Aéroport le plus proche", f'{aeros[0][1]} ({aeros[0][0]}), {nombre(aeros[0][2])} km'))
    if enc.get("fondation"):
        facts.append(("Fondation", enc["fondation"]))
    if enc.get("altitude_m") is not None:
        facts.append(("Altitude", f'{nombre(enc["altitude_m"])} m'))
    if enc.get("superficie_km2"):
        facts.append(("Superficie", f'{str(enc["superficie_km2"]).replace(".", ",")} km²'))
    if enc.get("eaux"):
        facts.append(("Au bord de", ", ".join(enc["eaux"])))
    if enc.get("maire"):
        facts.append(("Maire", enc["maire"]))
    if enc.get("surnoms"):
        facts.append(("Surnom", enc["surnoms"][0]))
    if pays.get("monnaie_nom"):
        facts.append(("Monnaie", E(maj(pays["monnaie_nom"])) + (f"<br><small>{change}</small>" if change else "")))
    if pays.get("langues"):
        facts.append(("Langues", E(maj(", ".join(pays["langues"])))))
    if pays.get("indicatif"):
        facts.append(("Indicatif", E(pays["indicatif"])))
    if capitale and capitale != v["nom"]:
        facts.append(("Capitale du pays", E(capitale)))
    elif capitale:
        facts.append(("Statut", "Capitale du pays"))
    dl = "".join(f"<div><dt>{k}</dt><dd>{val if k in ('Heure locale', 'Décalage', 'Saison', 'Monnaie', 'Soleil aujourd’hui') else (val if '<' in str(val) else E(str(val)))}</dd></div>" for k, val in facts)

    photo = ""
    if enc.get("photo"):
        ph = enc["photo"]
        credit = " · ".join(x for x in (ph.get("auteur"), ph.get("licence")) if x)
        photo = (f'<figure class="hero-photo"><img src="{E(ph["url"])}" alt="Vue de {E(v["nom"])}" loading="eager" decoding="async">'
                 f'<figcaption>Photo : <a href="{E(ph["page"])}" rel="noopener" target="_blank">{E(credit or "Wikimedia Commons")}</a></figcaption></figure>')
    blason = (f'<img class="blason" src="{E(enc["blason"]["url"])}" alt="Blason de {E(v["nom"])}" loading="lazy">' if enc.get("blason") else "")
    corps = [photo + f'''<section class="hero"><p class="crumbs"><a href="../../">Accueil</a> › <a href="../../pays/#{pays.get("continent", "")}">{E(cont)}</a> › <a href="../../pays/{v["pays"].lower()}/">{E(nom_pays)}</a></p>
<h1 class="city">{blason}{E(v["nom"])}{badge}</h1><p class="coords">{coords}{(" · " + E(v["nom_local"])) if v["nom_local"] != v["nom"] else ""}</p>
<p class="tagline">{E(v["nom"])}, {nombre(v["population"])} habitants, {E(nom_pays)}. {nombre(total_infos)} informations dans cette fiche, collectées et vérifiées automatiquement.</p></section>
<section class="facts" aria-label="Fiche d’identité"><dl>{dl}</dl></section>''']
    if alerte and alerte["niveau"] >= 2:
        lib, coul = NIVEAU_ALERTE[alerte["niveau"]]
        corps.append(f'<p class="alerte" style="--a:{coul}"><b>Sécurité : niveau {alerte["niveau"]} sur 4, {lib.lower()}.</b> '
                     f'Avant de partir, consultez les <a href="{DIPLO}" rel="noopener" target="_blank">Conseils aux voyageurs</a> du ministère des Affaires étrangères. '
                     f'<a href="#formalites">Détails</a></p>')

    sommaire_pos = len(corps)
    # En bref
    if wp.get("resume"):
        corps.append(f'<section class="block" id="en-bref"><h2>En bref</h2>{texte_html(wp["resume"], 4)}</section>')
    # Notre avis (rédigé par IA à partir des données)
    if red.get("accroche"):
        li = lambda l: "".join(f"<li>{E(x)}</li>" for x in l)
        h = f'<section class="block" id="avis"><h2>Notre avis</h2><p class="accroche">{E(red["accroche"])}</p>'
        if red.get("pourquoi"):
            h += f'<h3>Pourquoi y aller</h3><ul class="avis">{li(red["pourquoi"])}</ul>'
        if red.get("pour_qui"):
            h += f'<p class="lead"><b>Pour qui ?</b> {E(red["pour_qui"])}</p>'
        if red.get("conseils"):
            h += f'<h3>Conseils d’initiés</h3><ul class="avis">{li(red["conseils"])}</ul>'
        if red.get("a_eviter"):
            h += f'<h3>Les erreurs à éviter</h3><ul class="avis eviter">{li(red["a_eviter"])}</ul>'
        if red.get("un_jour") or red.get("trois_jours"):
            h += '<div class="progs">'
            if red.get("un_jour"):
                h += f'<div><h3>Une journée</h3><ol>{li(red["un_jour"])}</ol></div>'
            if red.get("trois_jours"):
                h += f'<div><h3>Trois jours</h3><ol>{li(red["trois_jours"])}</ol></div>'
            h += "</div>"
        h += f'<p class="note">Rédigé par une intelligence artificielle à partir des données vérifiées de cette fiche, le {date_fr(red["date"])}.</p>'
        corps.append(h + "</section>")

    # Histoire : frise + texte
    frise = []
    if enc.get("fondation"):
        frise.append(("Fondation", enc["fondation"], True))
    frise += [(x["nom"], x["date"], False) for x in enc.get("evenements", [])]
    if frise or "histoire" in wps or enc.get("anciens_noms"):
        h = '<section class="block" id="histoire"><h2>Histoire</h2>'
        if enc.get("anciens_noms"):
            h += f'<p class="lead">Anciens noms : {E(", ".join(enc["anciens_noms"]))}.</p>'
        if frise:
            h += '<ol class="timeline">' + "".join(f'<li class="{"big" if big else ""}"><b>{E(d) or "Date inconnue"}</b>{E(n)}</li>' for n, d, big in frise) + "</ol>"
        if "histoire" in wps:
            h += texte_html(wps["histoire"]["texte"], 4)
        corps.append(h + "</section>")

    # Météo
    if meteo:
        jours = "".join(f'<div><p class="d" style="margin:0">{date_fr(j["date"])[:-5]}</p><p class="w">{meteo_fr(j["code"])}</p>'
                        f'<p class="t" style="margin:0">{round(j["max"])}°</p><p class="d" style="margin:0">{round(j["min"])}°</p>'
                        f'<p class="r" style="margin:0">{(str(j["pluie_mm"]).replace(".", ",") + " mm") if j["pluie_mm"] else "&nbsp;"}</p></div>'
                        for j in meteo["jours"])
        corps.append(f'<section class="block" id="meteo"><h2>Météo des 7 prochains jours</h2><div class="weather">{jours}</div>'
                     + (f'<p class="lead" style="margin-top:1rem">Qualité de l’air : <b>{qualite_air(meteo["air"]["indice"])}</b> '
                        f'(indice européen {meteo["air"]["indice"]}, particules fines PM2,5 : {meteo["air"]["pm25"]} µg/m³).</p>' if meteo.get("air") else "")
                     + f'<p class="note">Prévisions Open-Meteo, mises à jour le {date_fr(meteo["date"])}.</p></section>')
    if clim.get("mois"):
        mois = clim["mois"]
        best = meilleurs_mois(mois)
        tmax = max((m["tmax"] or 0) for m in mois) or 1
        tmin = min((m["tmin"] or 0) for m in mois)
        bas = min(0, tmin)
        barres = "".join(
            f'<div class="m {best.get(i, "")}"><span class="v">{round(m["tmax"])}°</span><span class="b" style="height:{max(4, round(((m["tmax"] or 0) - bas) / (tmax - bas) * 100))}%"></span>'
            f'<span class="p" style="height:{min(100, round(m["pluie_mm"] / 3))}%"></span><span class="l">{MOIS[i].rstrip(".")}</span></div>'
            for i, m in enumerate(mois))
        ideaux = [MOIS_LONG[i] for i, k in best.items() if k == "ideal"]
        phrase = (f"Les mois les plus agréables pour visiter {E(v['nom'])} : {', '.join(ideaux)}." if ideaux
                  else "Aucun mois n’est vraiment tempéré et sec : choisissez selon la chaleur et la pluie que vous tolérez.")
        lignes = "".join(f'<tr><td>{MOIS_LONG[i].capitalize()}</td><td>{round(m["tmax"]) if m["tmax"] is not None else "–"}°</td>'
                         f'<td>{round(m["tmin"]) if m["tmin"] is not None else "–"}°</td><td>{m["pluie_mm"]} mm</td><td>{m["jours_pluie"] if m.get("jours_pluie") is not None else "–"}</td>'
                         f'<td>{str(m["soleil_h"]).replace(".", ",") + " h" if m["soleil_h"] is not None else "–"}</td></tr>' for i, m in enumerate(mois))
        corps.append(f'<section class="block" id="quand-partir"><h2>Quand partir</h2><p class="lead">{phrase} {E(red.get("quand_partir", ""))}</p>'
                     f'<div class="climat" aria-hidden="true">{barres}</div>'
                     '<p class="legend"><span style="--c:var(--sea)">Période idéale</span><span style="--c:var(--dot)">Possible</span>'
                     '<span style="--c:#c5ced0">Moins favorable</span><span style="--c:#5B8DC9">Pluie</span></p>'
                     f'<details class="more"><summary>Voir le tableau mois par mois</summary><div class="table-scroll"><table><thead><tr><th>Mois</th><th>Max.</th><th>Min.</th>'
                     f'<th>Pluie</th><th>Jours de pluie</th><th>Soleil par jour</th></tr></thead><tbody>{lignes}</tbody></table></div></details>'
                     f'<p class="note">Moyennes {clim["periode"].replace("-", " à ")}, '
                     + ("normales climatiques de la NASA (POWER)" if clim.get("source") == "NASA POWER" else "archive météo ERA5 (Open-Meteo)")
                     + (f", reprises de {E(clim["partage_avec"])}, ville voisine." if clim.get("partage_avec") else ".") + '</p></section>')

    # Lieux
    if lieux:
        corps.append(f'<section class="block" id="carte-lieux"><h2>Les lieux de {E(v["nom"])} sur la carte</h2><p class="lead">{nombre(len(lieux))} lieux recensés dans un rayon de '
                     f'{str(rubs.get("rayon_km", "")).replace(".", ",")} km autour du centre, et {nombre(len(autour))} sites notables aux alentours. Données vérifiées le {date_fr(rubs["date"])}.</p>'
                     + CARTE_BOUTON.format(lat=v["lat"], lon=v["lon"], rayon=rubs.get("rayon_km", 3))
                     + carte_lieux(v, lieux, rubs.get("rayon_km", 3)) + "</section>")
        for rub, titre, desc in RUBRIQUES:
            if rub == "sante":
                continue
            items = [f for f in lieux if f["rubrique"] == rub]
            if items:
                corps.append(f'<section class="block" id="{rub}"><h2>{titre}</h2><p class="lead">{desc} {nombre(len(items))} adresse{"s" if len(items) > 1 else ""}.</p>{liste_lieux(rub, items, v["niveau"])}</section>')
    if autour or v["proches"]:
        corps.append(section_alentours(v, autour, rubs))
    if not lieux:
        corps.append(f'<section class="block" id="lieux"><h2>Lieux, adresses et visites</h2><p class="empty">Les robots n’ont pas encore exploré {E(v["nom"])}. '
                     f'Les villes de ce niveau sont visitées {FREQ[v["niveau"]]} : monuments, musées, restaurants, hôtels et boutiques '
                     f'apparaîtront ici après leur premier passage.</p></section>')

    # Budget
    if cout:
        k = cout["indice"]
        prix = [("Café", 2.5), ("Repas simple", 15), ("Dîner au restaurant", 35), ("Ticket de transport", 2.2),
                ("Bière ou verre de vin", 5), ("Nuit en hôtel de milieu de gamme", 110)]
        lignes = "".join(f'<tr><td>{n}</td><td class="num">≈ {fmt_prix(p * k)}</td></tr>' for n, p in prix)
        jours = "".join(f'<tr><td>{n}</td><td class="num">≈ {fmt_prix(p * k)}</td></tr>'
                        for n, p in (("Petit budget", 70), ("Budget moyen", 150), ("Confort", 300)))
        corps.append(f'<section class="block" id="budget"><h2>Budget</h2><p class="lead">Pays : {E(nom_pays)}. Les prix y sont en moyenne à <b>{round(k * 100)} %</b> '
                     f'de ceux de la France. Estimations par personne :</p>'
                     f'<div class="cols"><div class="table-scroll"><table><tbody>{lignes}</tbody></table></div>'
                     f'<div class="table-scroll"><table><thead><tr><th>Par jour, hébergement compris</th><th></th></tr></thead><tbody>{jours}</tbody></table></div></div>'
                     f'<p class="note">Estimation tirée du niveau général des prix du pays (Banque mondiale, {cout["annee"]}). Les grandes villes touristiques sont souvent plus chères que la moyenne nationale.</p></section>')
    # Formalités et sécurité
    if ctx["formalites"] or alerte:
        h = '<section class="block" id="formalites"><h2>Formalités et sécurité</h2>'
        if ctx["formalites"]:
            lignes = "".join(f'<tr><td>{n}</td><td>{E(formalite_fr(ctx["formalites"].get(pp, {}).get(v["pays"], ""), pp, v["pays"]))}</td></tr>'
                             for pp, n in PASSEPORTS.items())
            h += f'<h3>Entrée dans le pays pour un séjour touristique</h3><div class="table-scroll"><table><tbody>{lignes}</tbody></table></div>'
        if alerte:
            lib, coul = NIVEAU_ALERTE[alerte["niveau"]]
            h += (f'<h3 style="margin-top:1.4rem">Niveau de sécurité</h3><p class="alerte" style="--a:{coul}"><b>Niveau {alerte["niveau"]} sur 4 : {lib}.</b> '
                  f'Indicateur des autorités américaines, mis à jour en continu.</p>')
        h += (f'<p class="note">Les règles d’entrée et la situation sécuritaire changent. Avant tout départ, vérifiez sur les '
              f'<a href="{DIPLO}" rel="noopener" target="_blank">Conseils aux voyageurs</a> du ministère français des Affaires étrangères '
              f'et sur le site de l’ambassade du pays.</p>')
        corps.append(h + "</section>")

    # S'y rendre : aéroports + guide
    if aeros or "aller" in gs:
        h = f'<section class="block" id="guide-aller"><h2>S’y rendre</h2>'
        if aeros:
            h += ('<h3>En avion</h3><div class="table-scroll"><table><thead><tr><th>Aéroport</th><th>Code</th><th>Distance</th><th>Trajet estimé</th></tr></thead><tbody>'
                  + "".join(f'<tr><td>{E(x[1])}{" · international" if x[3] else ""}</td><td class="num">{E(x[0])}</td><td class="num">{nombre(x[2])} km</td>'
                            f'<td>≈ {duree(x[2])} de route</td></tr>' for x in aeros) + "</tbody></table></div>")
        if "aller" in gs:
            h += texte_html(gs["aller"]["texte"], 3)
        corps.append(h + "</section>")
    for cle, titre_g in GUIDE:
        if cle in gs and cle != "aller":
            corps.append(f'<section class="block" id="guide-{cle}"><h2>{E(titre_g.format(ville=v["nom"]))}</h2>{texte_html(gs[cle]["texte"], 3)}</section>')

    cv = ctx["conseils"].get(v["pays"])
    cite = extraits_ville(cv, [v["nom"], v["nom_local"]] + v["alts"][:2]) if cv else []
    if cv:
        zones = [t for g, t in cv["sections"].get("avertissements", []) if g == "t"][1:]
        corps.append(f'<section class="block" id="conseils"><h2>Conseils officiels aux voyageurs</h2>'
                     f'<p class="alerte" style="--a:{COULEURS_NIVEAU.get(cv.get("niveau", 0), "#56707A")}"><b>{E(nom_pays)} : {E(cv.get("niveau_texte", ""))}.</b></p>'
                     + (f'<p class="lead">Zones à éviter ou à risque dans le pays :</p><ul class="unesco">' + "".join(f"<li>{E(z)}</li>" for z in zones[:8]) + "</ul>" if zones else "")
                     + ((f'<p class="lead">Ce que disent les conseils officiels de {E(v["nom"])} :</p><ul>' + "".join(f"<li>{E(x)}</li>" for x in cite) + "</ul>") if cite else "")
                     + ((f'<p class="lead">Arnaques signalées dans le pays :</p><ul>' + "".join(f"<li>{E(t)}</li>" for g, t in extraits_arnaques(cv, 3) if g != "t") + "</ul>") if extraits_arnaques(cv, 3) else "")
                     + f'<p><a class="tout-voir" style="display:inline-block;text-decoration:none" href="../../pays/{v["pays"].lower()}/conseils/">Sécurité, santé et vaccins, lois et coutumes, transports, catastrophes naturelles : tous les conseils</a></p>'
                     f'<p class="note">Source : gouvernement du Canada (données ouvertes). Pour les voyageurs français, la '
                     f'<a href="https://www.diplomatie.gouv.fr/fr/conseils-aux-voyageurs/conseils-par-pays-destination/{slug_fd(nom_pays)}/" rel="noopener" target="_blank">fiche du ministère des Affaires étrangères</a> fait foi.</p></section>')
    tr = ctx["transports"].get(v["id"])
    if tr and tr.get("lignes"):
        NOMS_MODES = [("metro", "métro"), ("tram", "tram"), ("bus", "bus"), ("train", "train"), ("ferry", "ferry")]
        parts = [f'<b>{nombre(tr["lignes"][m])}</b> ligne{"s" if tr["lignes"][m] > 1 else ""} de {n}' for m, n in NOMS_MODES if tr["lignes"].get(m)]
        corps.append(f'<section class="block" id="transports-communs"><h2>Transports en commun</h2><p class="lead">{", ".join(parts)} recensées dans et autour de {E(v["nom"])}.</p>'
                     + (f'<p>Réseaux et exploitants : {E(", ".join(tr["reseaux"]))}.</p>' if tr.get("reseaux") else "")
                     + f'<p class="note">D’après OpenStreetMap. Horaires et tarifs : voir le site de l’exploitant. Pour comparer avion, train, bus et voiture vers une autre ville : '
                     f'<a href="../../trajets/#de={v["slug"]}">comparateur de trajets</a>.</p></section>')
    sec_sante = section_sante(v, ctx, lieux, nom_pays)
    if sec_sante:
        corps.append(sec_sante)

    # Patrimoine
    if enc.get("unesco") or "patrimoine" in wps:
        h = '<section class="block" id="patrimoine"><h2>Patrimoine</h2>'
        if enc.get("unesco"):
            h += '<p class="lead">Inscrit au patrimoine mondial de l’UNESCO :</p><ul class="unesco">' + "".join(f"<li>{E(x)}</li>" for x in enc["unesco"]) + "</ul>"
        if "patrimoine" in wps:
            h += texte_html(wps["patrimoine"]["texte"])
        corps.append(h + "</section>")
    for rub, titre in (("culture", "Culture"), ("gastronomie", "Gastronomie"), ("geographie", "Géographie et climat"),
                       ("economie", "Économie"), ("sport", "Sport"), ("transports", "Transports")):
        if rub in wps:
            corps.append(f'<section class="block" id="{rub}"><h2>{titre}</h2>{texte_html(wps[rub]["texte"])}</section>')
    if enc.get("personnalites"):
        pers = "".join(f'<li><b>{E(x["nom"])}</b><span>{E(x["description"])}{(" · né en " + x["naissance"]) if x["naissance"] else ""}</span></li>'
                       for x in enc["personnalites"])
        corps.append(f'<section class="block" id="personnalites"><h2>Ils sont nés à {E(v["nom"])}</h2><ul class="persons">{pers}</ul>'
                     '<p class="note">Classées par notoriété internationale (nombre d’articles Wikipédia).</p></section>')
    if enc.get("jumelages"):
        corps.append(f'<section class="block" id="jumelages"><h2>Villes jumelées</h2><p class="lead">{E(", ".join(enc["jumelages"]))}.</p></section>')

    # Jours fériés à venir
    if feries:
        auj = date.today().isoformat()
        a_venir = [j for j in feries["jours"] if j["date"] >= auj][:12]
        if a_venir:
            lignes = "".join(f'<tr><td>{date_fr(j["date"])}</td><td>{E(j["nom_local"])}</td><td>{E(j["nom"])}</td></tr>' for j in a_venir)
            corps.append(f'<section class="block" id="feries"><h2>Jours fériés à venir</h2><div class="table-scroll"><table><thead><tr><th>Date</th>'
                         f'<th>Nom local</th><th>Nom anglais</th></tr></thead><tbody>{lignes}</tbody></table></div>'
                         f'<p class="note">Jours fériés nationaux, source Nager.Date. Commerces et musées peuvent être fermés.</p></section>')

    # Villes proches
    proches = "".join(f'<a href="../{w["slug"]}/">{E(w["nom"])}<span>{nombre(round(d))} km</span></a>' for d, w in v["proches"])
    corps.append(f'<section class="block" id="proches"><h2>Villes proches</h2><div class="near">{proches}</div></section>')
    ancres = [("en-bref", "En bref"), ("avis", "Notre avis"), ("histoire", "Histoire"), ("quand-partir", "Quand partir"), ("budget", "Budget"), ("formalites", "Formalités"),
              ("faire", "Activités"), ("alentours", "Aux alentours"), ("voir", "À voir"), ("manger", "Manger et boire"), ("dormir", "Dormir"),
              ("acheter", "Acheter"), ("patrimoine", "Patrimoine"), ("culture", "Culture"), ("gastronomie", "Gastronomie"),
              ("geographie", "Géographie"), ("personnalites", "Personnalités")]
    presentes = [(a, t) for a, t in ancres if any(f'id="{a}"' in b for b in corps)]
    if len(presentes) >= 3:
        corps.insert(sommaire_pos, '<nav class="sommaire" aria-label="Dans cette fiche">' + "".join(f'<a href="#{a}">{t}</a>' for a, t in presentes) + "</nav>")
    if guide:
        corps.append(f'<p class="note">Les rubriques « Le guide », « S’y rendre », « Se déplacer » et voisines reprennent l’article <a href="{E(guide["url"])}" rel="noopener" target="_blank">'
                     f'{E(guide["titre"])}</a> de Wikivoyage, le guide de voyage libre, sous licence <a href="https://creativecommons.org/licenses/by-sa/3.0/deed.fr" rel="noopener" target="_blank">CC BY-SA</a>.</p>')
    if wp:
        corps.append(f'<p class="note">Les textes « En bref », « Histoire » et suivants reprennent l’article <a href="{E(wp["url"])}" rel="noopener" target="_blank">'
                     f'{E(wp["titre"])}</a> de Wikipédia en français, sous licence <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.fr" rel="noopener" target="_blank">CC BY-SA 4.0</a> '
                     f'(auteurs : voir l’historique de l’article). Faits historiques et jumelages : Wikidata.</p>')
    corps.append(f'<p class="note" style="margin-top:2.5rem">Fiche générée le {ctx["date_txt"]}. Une erreur ? Les signalements seront bientôt possibles depuis chaque fiche.</p>')

    # Boîte à questions sur la ville
    corps.insert(sommaire_pos + (1 if len(presentes) >= 3 else 0), BOITE_QUESTIONS.format(nom=E(v["nom"]), slug=v["slug"]))

    # Export des données de la fiche, utilisées par la boîte à questions de tout le site
    def top(rub, n):
        return [{"nom": f["nom"], "type": f["type"], **({"cuisine": f["cuisine"]} if f.get("cuisine") else {}),
                 **({"adresse": f["adresse"]} if f.get("adresse") else {})}
                for f in sorted([f for f in lieux if f["rubrique"] == rub], key=lambda f: (-f["infos"], f["nom"]))[:n]]
    donnees = {"nom": v["nom"], "slug": v["slug"], "cc": v["pays"], "pays": nom_pays, "population": v["population"], "rang": v["rang"],
               "niveau": v["niveau"], "fuseau": v["fuseau"], "lat": v["lat"], "lon": v["lon"], "distance_paris": round(d_paris),
               "monnaie": pays.get("monnaie_nom", ""), "devise": devise, "taux": ctx["change"].get("taux", {}).get(devise),
               "langues": pays.get("langues", []), "indicatif": pays.get("indicatif", ""), "capitale": capitale,
               "infos": total_infos, "maj": ctx["date_txt"]}
    for k in ("fondation", "altitude_m", "superficie_km2", "maire", "surnoms", "eaux", "anciens_noms", "unesco", "site_officiel", "description"):
        if enc.get(k):
            donnees[k] = enc[k]
    if enc.get("jumelages"):
        donnees["jumelages"] = enc["jumelages"][:12]
    if enc.get("personnalites"):
        donnees["personnalites"] = [{"nom": x["nom"], "description": x["description"]} for x in enc["personnalites"][:8]]
    if wp.get("resume"):
        donnees["resume"] = couper_txt(wp["resume"], 700)
    if "histoire" in wps:
        donnees["histoire"] = couper_txt(wps["histoire"]["texte"], 900)
    if "gastronomie" in wps:
        donnees["gastronomie"] = couper_txt(wps["gastronomie"]["texte"], 600)
    if enc.get("evenements"):
        donnees["evenements"] = [{"date": e["date"], "nom": e["nom"]} for e in enc["evenements"][:12]]
    if meteo:
        donnees["meteo"] = [{"date": j["date"], "max": j["max"], "min": j["min"], "pluie": j["pluie_mm"], "ciel": meteo_fr(j["code"])} for j in meteo["jours"]]
        if meteo.get("air"):
            donnees["air"] = dict(meteo["air"], qualite=qualite_air(meteo["air"]["indice"]))
    if clim.get("mois"):
        donnees["climat"] = clim["mois"]
        donnees["meilleurs_mois"] = [MOIS_LONG[i] for i, k in meilleurs_mois(clim["mois"]).items() if k == "ideal"]
    if cout:
        donnees["cout"] = {"indice": cout["indice"], "annee": cout["annee"],
                           "prix": {"café": round(2.5 * cout["indice"], 1), "repas simple": round(15 * cout["indice"]),
                                    "dîner au restaurant": round(35 * cout["indice"]), "ticket de transport": round(2.2 * cout["indice"], 1),
                                    "nuit d’hôtel moyen": round(110 * cout["indice"]), "budget par jour (moyen)": round(150 * cout["indice"])}}
    if ctx["formalites"]:
        donnees["formalites"] = {n: formalite_fr(ctx["formalites"].get(pp, {}).get(v["pays"], ""), pp, v["pays"]) for pp, n in PASSEPORTS.items()}
    if alerte:
        donnees["securite"] = {"niveau": alerte["niveau"], "libelle": NIVEAU_ALERTE[alerte["niveau"]][0]}
    if feries:
        auj = date.today().isoformat()
        donnees["feries"] = [{"date": date_fr(j["date"]), "nom": j["nom_local"] or j["nom"]} for j in feries["jours"] if j["date"] >= auj][:6]
    for rub, n in (("voir", 10), ("manger", 10), ("dormir", 8), ("faire", 8), ("acheter", 6)):
        t = top(rub, n)
        if t:
            donnees[rub] = t
            donnees["nb_" + rub] = sum(1 for f in lieux if f["rubrique"] == rub)
    if autour:
        donnees["alentours"] = [{"nom": f["nom"], "type": f["type"], "km": f["distance_km"], "direction": f["direction"],
                                 "patrimoine_mondial": f.get("patrimoine_mondial", False)} for f in autour[:10]]
    donnees["proches"] = [{"nom": w["nom"], "slug": w["slug"], "km": round(d)} for d, w in v["proches"]]
    if ctx["urgences"].get(v["pays"]):
        donnees["urgences"] = ctx["urgences"][v["pays"]]
    if tr and tr.get("lignes"):
        donnees["transports"] = tr
    if pr:
        donnees["pratique"] = pr
    if cv:
        donnees["conseils_ville"] = cite
        donnees["arnaques"] = [t for g, t in extraits_arnaques(cv, 4) if g != "t"][:3]
        donnees["conseils"] = {"niveau": cv.get("niveau", 0), "texte": cv.get("niveau_texte", ""),
                               "zones": [t for g, t in cv["sections"].get("avertissements", []) if g == "t"][1:9], "fd": slug_fd(nom_pays)}
    if v.get("representations"):
        donnees["representations"] = [{k: x[k] for k in ("pays", "type", "nom", "adresse", "telephone", "site", "km")} for x in v["representations"]]
    sante_ = [f for f in lieux if f["rubrique"] == "sante"]
    if sante_:
        sante_.sort(key=lambda f: (f.get("urgences") != "oui", f["type"] not in ("Hôpital", "Clinique"), -f["infos"]))
        donnees["sante"] = [{"nom": f["nom"], "type": f["type"], "adresse": f.get("adresse", ""), "telephone": f.get("telephone", ""),
                             "urgences": f.get("urgences", "")} for f in sante_[:8]]
        donnees["nb_sante"] = len(sante_)
    if aeros:
        donnees["aeroports"] = [{"code": x[0], "nom": x[1], "km": x[2], "international": bool(x[3])} for x in aeros]
    if gs.get("aller"):
        donnees["aller"] = couper_txt(gs["aller"]["texte"], 700)
    red_ok = {k: red[k] for k in ("accroche", "conseils", "a_eviter", "quand_partir", "un_jour") if red.get(k)}
    if red_ok:
        donnees["avis"] = red_ok
    ecrire_gz(f"villes/{v['slug']}/donnees.json.gz", donnees)
    if tous:
        cles = ("nom", "type", "rubrique", "adresse", "horaires", "cuisine", "etoiles", "payant", "site", "telephone",
                "fauteuil", "terrasse", "distance_km", "direction", "patrimoine_mondial", "id", "lat", "lon")
        export = [{k: f[k] for k in cles if f.get(k)} for f in sorted(tous, key=lambda f: (f["rubrique"], -f["infos"], f["nom"]))]
        if v["niveau"] == "autre":
            gardes = {}
            export = [f for f in export if gardes.setdefault(f["rubrique"], []).append(1) or len(gardes[f["rubrique"]]) <= 40]
        ecrire_gz(f"villes/{v['slug']}/lieux.json.gz", {"date": rubs["date"], "rayon_km": rubs.get("rayon_km"),
                                                         "rayon_alentours_km": rubs.get("rayon_alentours_km"), "lieux": export})
    # Ligne compacte pour les outils (itinéraire, « où partir », comparateur)
    types_ = [f["type"] for f in tous]
    culture = sum(1 for t in types_ if t in ("Musée", "Monument", "Château", "Site archéologique", "Galerie", "Monastère", "Fort", "Ruines")) + 5 * len(enc.get("unesco", []))
    nature = sum(1 for t in types_ if t in ("Parc national", "Réserve naturelle", "Espace naturel protégé", "Cascade", "Sommet", "Grotte", "Volcan", "Glacier", "Sentier de randonnée"))
    plage = any(t in ("Plage", "Plage aménagée", "Baignade") for t in types_)
    ski = "Station de ski" in types_
    nbr = {r: sum(1 for f in lieux if f["rubrique"] == r) for r in ("voir", "manger", "dormir", "faire")}
    cm = clim.get("mois")
    ctx["monde"].append([v["slug"], v["nom"], v["pays"], round(v["lat"], 2), round(v["lon"], 2), v["population"],
                         {"phare": 0, "intermediaire": 1, "autre": 2}[v["niveau"]],
                         [round(m["tmax"]) for m in cm] if cm else 0, [round(m["tmin"]) for m in cm] if cm else 0,
                         [m["pluie_mm"] for m in cm] if cm else 0,
                         nbr["voir"], nbr["manger"], nbr["dormir"], nbr["faire"], culture, nature, 1 if plage else 0, 1 if ski else 0,
                         [aeros[0][0], aeros[0][2]] if aeros else 0])
    cpt = ctx["compteur"]
    cpt["informations"] += total_infos
    cpt["lieux"] += len(tous)
    cpt["textes"] += len(wps) + (1 if wp.get("resume") else 0)
    cpt["photos"] += 1 if enc.get("photo") else 0
    cpt["villes_enrichies"] += 1 if (tous or enc) else 0

    desc = f"Guide de voyage de {v['nom']} ({nom_pays}) : lieux à voir, où manger, où dormir, météo, jours fériés et infos pratiques."
    if v["niveau"] == "autre" and not ctx.get("pages_completes"):
        # Page légère : le reste de la fiche est construit dans le navigateur à partir des fichiers compressés
        donnees["complet"] = {"textes": {k: x["texte"] for k, x in wps.items()}, "resume": wp.get("resume", ""),
                              "guide": {k: x["texte"] for k, x in gs.items()},
                              "guide_source": {"titre": guide.get("titre"), "url": guide.get("url")} if guide else None,
                              "wikipedia": {"titre": wp.get("titre"), "url": wp.get("url")} if wp else None,
                              "evenements": enc.get("evenements", []), "photo": enc.get("photo"), "blason": enc.get("blason"),
                              "alentours": [{"nom": f["nom"], "type": f["type"], "km": f.get("distance_km"), "direction": f.get("direction"),
                                             "patrimoine_mondial": f.get("patrimoine_mondial", False), "id": f["id"]} for f in autour[:100]],
                              "facts": [(k, val) for k, val in facts]}
        ecrire_gz(f"villes/{v['slug']}/donnees.json.gz", donnees)
        leger = (f'<section class="hero"><p class="crumbs"><a href="../../">Accueil</a> › <a href="../../pays/#{pays.get("continent", "")}">{E(cont)}</a> › <a href="../../pays/{v["pays"].lower()}/">{E(nom_pays)}</a></p>'
                 f'<h1 class="city">{E(v["nom"])}</h1><p class="coords">{coords}</p>'
                 f'<p class="tagline">{E(v["nom"])}, {nombre(v["population"])} habitants, {E(nom_pays)}. {nombre(total_infos)} informations dans cette fiche.</p></section>'
                 f'<div id="fiche-dyn" data-slug="{v["slug"]}" data-niveau="{v["niveau"]}"><p class="note">Chargement de la fiche…</p></div>'
                 + BOITE_QUESTIONS.format(nom=E(v["nom"]), slug=v["slug"]))
        return page("../../", f"{v['nom']} ({nom_pays}) – Dix Mille Escales", desc, leger)
    return page("../../", f"{v['nom']} ({nom_pays}) – Dix Mille Escales", desc, "\n".join(corps))


def section_alentours(v, autour, rubs):
    """Aux alentours : idées d'excursions à la journée, puis tous les sites notables classés par distance."""
    h = '<section class="block" id="alentours"><h2>Aux alentours</h2>'
    # Idées d'excursions : patrimoine mondial, grands sites et villes voisines, à moins de 2 h
    poids = {"Parc national": 3, "Château": 3, "Site archéologique": 3, "Monastère": 2, "Cascade": 2, "Grotte": 2,
             "Plage": 1, "Espace naturel protégé": 2, "Volcan": 3, "Glacier": 3, "Parc d’attractions": 2, "Sommet": 1}
    idees = sorted(autour, key=lambda f: (-(5 if f.get("patrimoine_mondial") else 0) - poids.get(f["type"], 0) - (1 if f.get("wikidata") else 0),
                                          f.get("distance_km", 99)))[:6]
    villes = [(d, w) for d, w in v["proches"] if 15 <= d <= 150][:4]
    if idees or villes:
        h += '<h3>Idées d’excursions à la journée</h3><ul class="excursions">'
        for f in idees:
            badge = '<span class="unesco-tag">Patrimoine mondial</span>' if f.get("patrimoine_mondial") else ""
            h += (f'<li><b>{E(f["nom"])}{badge}</b><span class="d">{E(f["type"])} · {str(f["distance_km"]).replace(".", ",")} km {E(f["direction"])}'
                  f' · ≈ {duree(f["distance_km"])} de route</span></li>')
        for d, w in villes:
            h += (f'<li><b><a href="../{w["slug"]}/">{E(w["nom"])}</a></b><span class="d">Ville voisine · {nombre(round(d))} km · ≈ {duree(d)} de route</span></li>')
        h += "</ul><p class=\"note\">Temps de route estimés à vol d’oiseau, à titre indicatif.</p>"
    if autour:
        types = {}
        for f in autour:
            types[f["type"]] = types.get(f["type"], 0) + 1
        h += (f'<h3 style="margin-top:1.6rem">Tous les sites notables à moins de {rubs.get("rayon_alentours_km", 50)} km</h3>'
              f'<div class="chips" data-filter-for="l-alentours"></div><ul class="places" id="l-alentours">')
        limite_ = {"phare": 60, "intermediaire": 25, "autre": 12}.get(v["niveau"], 25)
        for f in autour[:limite_]:
            typ, ident = f["id"][4:].split("/")
            h += (f'<li data-type="{E(f["type"])}" style="--c:var(--alentours)"><h3>{E(f["nom"])}</h3>'
                  f'<div class="m">{E(f["type"])} · {str(f["distance_km"]).replace(".", ",")} km {E(f["direction"])}'
                  f'{" · patrimoine mondial" if f.get("patrimoine_mondial") else ""}</div>'
                  + (f'<div class="i">Horaires : {E(horaires_fr(f["horaires"]))}</div>' if f.get("horaires") else "")
                  + f'<div class="i"><a href="https://www.openstreetmap.org/{typ}/{ident}" rel="nofollow noopener" target="_blank">Carte</a></div></li>')
        h += "</ul>"
        if len(autour) > limite_:
            h += f'<button type="button" class="tout-voir" data-rub="alentours" data-n="{len(autour)}">Voir les {nombre(len(autour))} sites des alentours</button>'
    return h + "</section>"


def duree(km):
    h = km * 1.3 / 70  # détours de la route, 70 km/h de moyenne
    if h < 1:
        return f"{max(10, round(h * 60 / 5) * 5)} min"
    return f"{int(h)} h {round((h % 1) * 60 / 5) * 5:02d}".replace(" 00", "")


def avec_robots(txt):
    """Ajoute à une fiche rédigée à la main le bloc des données collectées par les robots (rendu dans le navigateur)."""
    bloc = ('<section id="donnees-robots" data-root="../../" aria-label="Données mises à jour chaque nuit"></section>'
            '<script src="../../static/robots-fiche.js" defer></script><script src="../../static/onglets.js" defer></script>')
    return txt.replace("</main>", bloc + "</main>", 1) if "</main>" in txt else txt.replace("</body>", bloc + "</body>", 1)


PAYS_JS = """<script>
(function(){var q=document.getElementById('pays-q');if(!q)return;var box=document.getElementById('pays-liste'),note=document.getElementById('pays-note'),nomp=box.getAttribute('data-pays'),L=null;
function n(t){return (t||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');}
function E(t){return String(t).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function rendre(){var t=n(q.value.trim()),l=L.filter(function(r){return !t||n(r[0]+' '+r[4]).indexOf(t)>-1;});
box.innerHTML=l.slice(0,300).map(function(r){return '<a href="../../villes/'+r[1]+'/">'+E(r[0])+'<span>'+new Intl.NumberFormat('fr-FR').format(r[3])+' hab.</span></a>';}).join('');
note.textContent=l.length>300?'300 premières villes sur '+l.length+' : affinez la recherche.':(l.length?'':'Aucune ville ne correspond.');}
fetch('../../static/index.json').then(function(r){return r.json();}).then(function(d){L=d.filter(function(r){return r[2]===nomp;});rendre();});
q.addEventListener('input',function(){if(L)rendre();});})();
</script>"""


def outils(ctx):
    """Pages des outils : planificateur d'itinéraire, « où partir », comparateur, préparation, carnet, convertisseur."""
    pp = "".join(f'<option>{n}</option>' for n in PASSEPORTS.values())
    def outil(chemin, titre, desc, corps, scripts):
        sc = "".join(f'<script src="../static/{x}.js"></script>' for x in ["outils-commun"] + scripts)
        html_ = page("../", f"{titre} – Dix Mille Escales", desc,
                     f'<section class="hero"><p class="crumbs"><a href="../">Accueil</a> › <a href="../outils/">Outils</a></p>'
                     f'<h1 class="city" style="font-size:clamp(2.2rem,6.5vw,4.2rem)">{titre}</h1><p class="tagline">{desc}</p></section>{corps}')
        ecrire(f"{chemin}/index.html", html_.replace("</body>", sc + "</body>"))
    outil("itineraire", "Planificateur d’itinéraire", "Choisissez vos villes, vos dates et vos envies : l’ordre des étapes, les trajets, le programme jour par jour, le budget et la préparation sont calculés pour vous.",
          f'''<form id="itin" class="o-form">
<div class="o-champ o-large"><label for="itin-q">Ajouter une ville</label><input id="itin-q" type="search" autocomplete="off" placeholder="Tapez le nom d’une ville…"></div>
<ul id="itin-villes" class="o-choix"></ul>
<label class="o-coche"><input type="checkbox" id="itin-depart" checked> La première ville est mon point de départ</label>
<div class="o-grille">
<div class="o-champ"><label for="itin-jours">Nombre de jours</label><input id="itin-jours" type="number" min="1" max="120" value="10"></div>
<div class="o-champ"><label for="itin-mois">Mois du voyage</label><select id="itin-mois"></select></div>
<div class="o-champ"><label for="itin-pers">Voyageurs</label><input id="itin-pers" type="number" min="1" max="20" value="2"></div>
<div class="o-champ"><label for="itin-budget">Budget</label><select id="itin-budget"><option value="petit">Petit budget</option><option value="moyen" selected>Moyen</option><option value="confort">Confort</option></select></div>
<div class="o-champ"><label for="itin-passeport">Passeport</label><select id="itin-passeport">{pp}</select></div>
</div>
<fieldset class="o-envies"><legend>Vos envies</legend><div id="itin-envies"></div></fieldset>
<button type="submit" class="o-go">Créer mon itinéraire</button></form><div id="itin-res" class="o-res" aria-live="polite"></div>''', ["itineraire"])
    outil("ou-partir", "Où partir ?", "Un mois, une température, vos envies : les villes idéales du monde entier, parmi toutes celles du guide.",
          '''<form id="op" class="o-form"><div class="o-grille">
<div class="o-champ"><label for="op-mois">Mois</label><select id="op-mois"></select></div>
<div class="o-champ"><label for="op-tmin">Température l’après-midi, au moins</label><input id="op-tmin" type="number" value="20"></div>
<div class="o-champ"><label for="op-tmax">Au plus</label><input id="op-tmax" type="number" value="30"></div>
<div class="o-champ"><label for="op-pluie">Pluie du mois, au plus (mm)</label><input id="op-pluie" type="number" value="80"></div>
<div class="o-champ"><label for="op-envie">Envie</label><select id="op-envie"><option value="tout">Peu importe</option><option value="plage">Plage</option><option value="culture">Culture et monuments</option><option value="nature">Nature</option><option value="ski">Ski</option></select></div>
<div class="o-champ"><label for="op-cont">Continent</label><select id="op-cont"><option value="">Partout</option><option value="EU">Europe</option><option value="AF">Afrique</option><option value="AS">Asie</option><option value="NA">Amérique du Nord et centrale</option><option value="SA">Amérique du Sud</option><option value="OC">Océanie</option></select></div>
<div class="o-champ"><label for="op-budget">Budget</label><select id="op-budget"><option value="">Peu importe</option><option value="moyen">Moins cher que la France</option><option value="petit">Bien moins cher</option></select></div>
<div class="o-champ"><label for="op-taille">Villes</label><select id="op-taille"><option value="">Toutes</option><option value="grandes">Grandes villes</option><option value="petites">Petites villes</option></select></div>
<div class="o-champ"><label for="op-dist">Distance de Paris, au plus</label><select id="op-dist"><option value="0">Peu importe</option><option value="1500">1 500 km</option><option value="3000">3 000 km</option><option value="6000">6 000 km</option></select></div>
</div><label class="o-coche"><input type="checkbox" id="op-visa"> Sans visa pour un passeport français</label> <label class="o-coche"><input type="checkbox" id="op-sur" checked> Pays sûrs seulement (niveau 1 ou 2)</label>
<button type="submit" class="o-go">Trouver</button></form><div id="op-res" class="o-res" aria-live="polite"></div>''', ["ou-partir"])
    outil("comparer", "Comparer des villes", "Deux à quatre villes côte à côte : climat, budget, visa, sécurité, nombre de lieux, accès.",
          '''<form id="cmp" class="o-form" onsubmit="return false"><div class="o-grille"><div class="o-champ o-large"><label for="cmp-q">Ajouter une ville</label><input id="cmp-q" type="search" autocomplete="off" placeholder="Tapez le nom d’une ville…"></div>
<div class="o-champ"><label for="cmp-mois">Mois du voyage</label><select id="cmp-mois"></select></div></div><ul id="cmp-villes" class="o-choix"></ul></form><div id="cmp-res" class="o-res"></div>''', ["comparer"])
    outil("preparer", "Préparer son départ", "Papiers, argent, valise, santé : la liste à cocher pour vos destinations et votre mois de voyage.",
          f'''<form id="prep" class="o-form" onsubmit="return false"><div class="o-grille"><div class="o-champ o-large"><label for="prep-q">Ajouter une destination</label><input id="prep-q" type="search" autocomplete="off" placeholder="Tapez le nom d’une ville…"></div>
<div class="o-champ"><label for="prep-mois">Mois</label><select id="prep-mois"></select></div><div class="o-champ"><label for="prep-pp">Passeport</label><select id="prep-pp">{pp}</select></div></div>
<ul id="prep-villes" class="o-choix"></ul></form><div id="prep-res" class="o-res"></div>
<script>document.addEventListener("DOMContentLoaded",function(){{var D=window.DME,E=D.E,ch=[],f=document.getElementById("prep"),m=f.querySelector("#prep-mois");
m.innerHTML=D.MOIS.map(function(x,i){{return "<option value="+i+">"+x+"</option>";}}).join("");m.value=String(new Date().getMonth());
function r(){{var ul=f.querySelector("#prep-villes");ul.innerHTML=ch.map(function(s,i){{var v=D.ville(s);return "<li>"+E(v?v.nom:s)+" <button type=button data-i="+i+">✕</button></li>";}}).join("")||"<li class=o-vide>Ajoutez une ou plusieurs destinations.</li>";
ul.querySelectorAll("button").forEach(function(b){{b.onclick=function(){{ch.splice(+b.getAttribute("data-i"),1);r();}};}});
if(!ch.length){{document.getElementById("prep-res").innerHTML="";return;}}var L=D.preparation(ch.map(D.ville),+m.value,f.querySelector("#prep-pp").value);
document.getElementById("prep-res").innerHTML="<div class=o-prep>"+Object.keys(L).map(function(k){{return "<div><h3>"+E(k)+"</h3><ul class=o-cases>"+L[k].map(function(x){{return "<li><label><input type=checkbox> "+x+"</label></li>";}}).join("")+"</ul></div>";}}).join("")+"</div><div class=o-actions><button type=button onclick=window.print()>Imprimer la liste</button></div>";}}
D.chargerMonde().then(function(){{D.choixVille(f.querySelector("#prep-q"),function(s){{if(ch.indexOf(s)<0)ch.push(s);r();}});r();}});m.onchange=r;f.querySelector("#prep-pp").onchange=r;}});</script>''', [])
    ecrire("assurance/index.html", page("../", "Assurance, santé et rapatriement – Dix Mille Escales", "Ce qu’il faut vérifier avant de partir, et que faire en cas de problème de santé à l’étranger.",
           '''<section class="hero"><p class="crumbs"><a href="../">Accueil</a> › <a href="../outils/">Outils</a></p>
<h1 class="city" style="font-size:clamp(2.2rem,6.5vw,4.2rem)">Assurance, santé et rapatriement</h1>
<p class="tagline">Ce qu’il faut vérifier avant de partir, et les bons réflexes en cas de problème de santé à l’étranger. Guide général : il ne remplace pas votre contrat ni l’avis d’un professionnel.</p></section>
<div class="prose">
<h2>1. Ce que vous avez peut-être déjà</h2>
<p><b>La carte européenne d’assurance maladie</b> (CEAM), gratuite et délivrée par votre caisse d’assurance maladie, permet d’être soigné dans les pays de l’Union européenne, de l’Espace économique européen, en Suisse et au Royaume-Uni, aux conditions du pays. Elle ne couvre pas le rapatriement. Demandez-la au moins deux semaines avant le départ.</p>
<p><b>Votre carte bancaire</b> inclut souvent une assistance et une assurance voyage, surtout les cartes haut de gamme, à condition d’avoir payé le voyage avec elle. Lisez la notice : montants, durée maximale du séjour, pays exclus.</p>
<p><b>Votre mutuelle ou complémentaire santé</b> prend parfois en charge des soins à l’étranger : renseignez-vous avant de partir.</p>
<h2>2. Ce qu’un bon contrat doit couvrir</h2>
<ul>
<li><b>Les frais médicaux et d’hospitalisation à l’étranger</b>, avec un plafond élevé hors d’Europe : une hospitalisation aux États-Unis, au Canada ou au Japon peut coûter plusieurs dizaines de milliers d’euros.</li>
<li><b>Le rapatriement médical</b> vers votre pays, sans plafond ou avec un plafond très élevé.</li>
<li><b>L’avance des frais</b> : sinon, il faut payer sur place et se faire rembourser au retour.</li>
<li>Une <b>assistance joignable jour et nuit</b>, dans votre langue.</li>
<li>Les <b>activités prévues</b> : sports à risque, plongée, randonnée en altitude ou ski sont souvent exclus sans option.</li>
<li>La <b>durée</b> et les <b>pays</b> du voyage, la <b>franchise</b>, et les éventuelles <b>exclusions</b> (maladies déjà connues, grossesse).</li>
</ul>
<p>Pour certains pays, une assurance est obligatoire pour obtenir le visa ou entrer sur le territoire : vérifiez dans les formalités de la fiche du pays et sur les Conseils aux voyageurs.</p>
<h2>3. Avant de partir</h2>
<ul>
<li>Notez le numéro d’assistance et le numéro de contrat, gardez-les sur vous et en version numérique.</li>
<li>Consultez votre médecin ou un centre de vaccinations internationales 4 à 6 semaines avant le départ (vaccins, traitement préventif du paludisme selon la destination). Voir le <a href="https://www.pasteur.fr/fr/centre-medical/preparer-son-voyage" rel="noopener" target="_blank">centre médical de l’Institut Pasteur</a>.</li>
<li>Emportez vos médicaments habituels en quantité suffisante, dans leur boîte, avec l’ordonnance (traduite si possible).</li>
<li>Inscrivez-vous sur le service <b>Ariane</b> du ministère des Affaires étrangères, pour être prévenu et joint en cas de crise.</li>
</ul>
<h2>4. En cas de problème sur place</h2>
<ul>
<li><b>Urgence vitale</b> : appelez les secours du pays (numéros indiqués dans la rubrique « Santé et urgences » de chaque fiche de ville ; le 112 fonctionne dans de nombreux pays).</li>
<li><b>Appelez votre assistance avant d’engager des frais</b>, sauf urgence vitale : elle peut orienter vers un établissement, avancer les frais et organiser un rapatriement.</li>
<li>Gardez <b>toutes les factures et comptes rendus médicaux</b> pour le remboursement.</li>
<li>En cas de difficulté grave (hospitalisation, perte de papiers), contactez l’<b>ambassade ou le consulat</b> : ses coordonnées figurent dans chaque fiche de ville. Le consulat ne paie pas les frais médicaux, mais peut aider à contacter la famille, l’assureur ou un médecin.</li>
</ul>
<p class="note">Dix Mille Escales ne vend pas d’assurance et ne reçoit aucune rémunération d’assureurs : ce guide est neutre. Comparez plusieurs offres et lisez toujours les conditions générales.</p>
</div>'''))
    outil("trajets", "Comparateur de trajets", "Avion, train, bus ou voiture entre deux villes : durée, prix et émissions de CO₂ estimés, avec des liens pour chercher les vrais billets.",
          '''<form id="tj" class="o-form" onsubmit="return false"><div class="o-grille">
<div class="o-champ"><label for="tj-a">Départ</label><input id="tj-a" type="search" autocomplete="off" placeholder="Ville de départ…"><p id="tj-a-v" class="o-nb"></p></div>
<div class="o-champ"><label for="tj-b">Arrivée</label><input id="tj-b" type="search" autocomplete="off" placeholder="Ville d’arrivée…"><p id="tj-b-v" class="o-nb"></p></div>
<div class="o-champ"><label for="tj-n">Voyageurs</label><input id="tj-n" type="number" min="1" max="9" value="1"></div></div></form><div id="tj-res" class="o-res" aria-live="polite"></div>''', ["trajets"])
    outil("carnet", "Mon carnet", "Vos villes et vos itinéraires gardés sur cet appareil.", '<div id="carnet-page" class="o-res"></div>', [])
    cartes = [("itineraire", "Planificateur d’itinéraire", "Plusieurs villes, un ou plusieurs pays : ordre des étapes, trajets, programme jour par jour, budget."),
              ("ou-partir", "Où partir ?", "Les villes idéales du monde pour un mois, une température et vos envies."),
              ("comparer", "Comparer des villes", "Deux à quatre villes côte à côte."),
              ("preparer", "Préparer son départ", "La liste à cocher : papiers, argent, valise, santé."),
              ("trajets", "Comparateur de trajets", "Avion, train, bus ou voiture : durée, prix et CO₂ estimés, liens vers les vols."),
              ("carnet", "Mon carnet", "Vos villes et itinéraires gardés."),
              ("assurance", "Assurance, santé et rapatriement", "Ce qu’il faut vérifier avant de partir, et que faire en cas de problème.")]
    corps = ('<div class="o-cartes">' + "".join(f'<a class="o-carte" href="../{c}/"><b>{t}</b><span>{d}</span></a>' for c, t, d in cartes) + "</div>"
             + '''<section class="block" id="convertisseur"><h2>Convertisseur de monnaie</h2><form id="conv" class="o-form" onsubmit="return false"><div class="o-grille">
<div class="o-champ"><label for="conv-montant">Montant</label><input id="conv-montant" type="text" inputmode="decimal" value="100"></div>
<div class="o-champ"><label for="conv-de">De</label><select id="conv-de"></select></div><div class="o-champ"><label for="conv-vers">Vers</label><select id="conv-vers"></select></div>
</div><button type="button" id="conv-inverser" class="o-petit">Inverser</button><p class="o-conv" id="conv-res" aria-live="polite"></p><p class="note" id="conv-date"></p></form></section>''')
    html_ = page("../", "Outils de voyage – Dix Mille Escales", "Planificateur d’itinéraire, où partir, comparateur, préparation, carnet et convertisseur.",
                 '<section class="hero"><h1 class="city" style="font-size:clamp(2.4rem,7vw,4.5rem)">Outils de voyage</h1><p class="tagline">Pour préparer un voyage avec les données de toutes les villes du guide.</p></section>' + corps)
    ecrire("outils/index.html", html_.replace("</body>", '<script src="../static/outils-commun.js"></script><script src="../static/convertisseur.js"></script></body>'))


def representations(villes, ctx):
    """Pour chaque ville : l'ambassade ou le consulat le plus proche de France, Belgique, Suisse et Canada, dans le même pays."""
    cases = {}
    for v in villes:
        cases.setdefault((int(v["lat"] // 2), int(v["lon"] // 2)), []).append(v)
    par_hote = {}
    for x in ctx["diplo"]:
        hote = x.get("cible", "")
        if not hote:  # pays hôte = pays de la ville du guide la plus proche
            ci, cj = int(x["lat"] // 2), int(x["lon"] // 2)
            cand = [w for i in (ci - 1, ci, ci + 1) for j in (cj - 1, cj, cj + 1) for w in cases.get((i, j), [])]
            if not cand:
                continue
            hote = min(cand, key=lambda w: dist((w["lat"], w["lon"]), (x["lat"], x["lon"])))["pays"]
        par_hote.setdefault((x["pays"], hote), []).append(x)
    for v in villes:
        rep_ = []
        for pp in ("FR", "BE", "CH", "CA"):
            l = par_hote.get((pp, v["pays"]))
            if l and pp != v["pays"]:
                x = min(l, key=lambda y: dist((v["lat"], v["lon"]), (y["lat"], y["lon"])))
                rep_.append(dict(x, km=round(dist((v["lat"], v["lon"]), (x["lat"], x["lon"])))))
        v["representations"] = rep_


def contacts(x):
    """Téléphone et site d'une représentation diplomatique."""
    out = []
    if x.get("telephone"):
        out.append(f'<a href="tel:{E(x["telephone"].replace(" ", ""))}">{E(x["telephone"])}</a>')
    if x.get("site", "").startswith("http"):
        out.append(f'<a href="{E(x["site"])}" rel="noopener" target="_blank">Site</a>')
    return "<br>".join(out)


NOMS_REPR = {"FR": "France", "BE": "Belgique", "CH": "Suisse", "CA": "Canada"}
TYPES_REPR = {"embassy": "Ambassade", "consulate": "Consulat", "consulate_general": "Consulat général", "honorary_consul": "Consul honoraire",
              "delegation": "Délégation", "high_commission": "Haut-commissariat"}


def section_sante(v, ctx, lieux, nom_pays):
    items = [f for f in lieux if f["rubrique"] == "sante"]
    urg = ctx["urgences"].get(v["pays"], [])
    rep_ = v.get("representations", [])
    if not (items or urg or rep_):
        return ""
    h = '<section class="block" id="sante"><h2>Santé et urgences</h2>'
    if urg:
        h += ('<div class="urgences"><p class="lead"><b>Numéros d’urgence (' + E(nom_pays) + ')</b></p><ul>'
              + "".join(f'<li><a href="tel:{E(x["numero"].replace(" ", ""))}"><b>{E(x["numero"])}</b></a>'
                        f'{(" : " + E(", ".join(x["services"]))) if x["services"] else ""}</li>' for x in urg)
              + '</ul><p class="note">Le 112 fonctionne dans toute l’Union européenne et dans de nombreux pays depuis un téléphone mobile. Vérifiez les numéros sur place.</p></div>')
    if items:
        nb_h = sum(1 for f in items if f["type"] in ("Hôpital", "Clinique"))
        nb_p = sum(1 for f in items if f["type"] == "Pharmacie")
        items.sort(key=lambda f: (f.get("urgences") != "oui", f["type"] not in ("Hôpital", "Clinique"), -f["infos"]))
        h += (f'<h3>Soins autour de {E(v["nom"])}</h3><p class="lead">{nombre(nb_h)} hôpital{"aux" if nb_h > 1 else ""} ou clinique{"s" if nb_h > 1 else ""}, '
              f'{nombre(nb_p)} pharmacie{"s" if nb_p > 1 else ""}, {nombre(len(items) - nb_h - nb_p)} médecins et dentistes recensés. Les hôpitaux avec service d’urgences sont en tête.</p>'
              + liste_lieux("sante", items, v["niveau"]))
    if rep_:
        h += ('<h3>Ambassades et consulats</h3><div class="table-scroll"><table><tbody>'
              + "".join(f'<tr><td>{NOMS_REPR[x["pays"]]}</td><td><b>{E(x["nom"] or TYPES_REPR.get(x["type"], "Représentation"))}</b><br>'
                        f'<small>{E(TYPES_REPR.get(x["type"], ""))}{(" · " + E(x["adresse"])) if x["adresse"] else ""}</small></td>'
                        f'<td class="num">{nombre(x["km"])} km</td><td>{contacts(x)}</td></tr>' for x in rep_)
              + '</tbody></table></div><p class="note">D’après OpenStreetMap : vérifiez les coordonnées sur le site officiel de la représentation avant de vous déplacer.</p>')
    h += (f'<p class="note">Santé en voyage : consultez la rubrique « Santé » des <a href="{DIPLO}" rel="noopener" target="_blank">Conseils aux voyageurs</a> '
          'et les recommandations du <a href="https://www.pasteur.fr/fr/centre-medical/preparer-son-voyage" rel="noopener" target="_blank">centre médical de l’Institut Pasteur</a>. '
          'Assurance et rapatriement : voir notre <a href="../../assurance/">guide</a>.</p>')
    return h + "</section>"


TITRES_CONSEILS = [("avertissements", "Niveau de risque et zones à éviter"), ("securite", "Sécurité : criminalité, transports, arnaques…"),
                   ("sante", "Santé et vaccins"), ("lois_culture", "Lois et coutumes"), ("catastrophes_climat", "Catastrophes naturelles et climat"),
                   ("entree_sortie", "Entrée et sortie (règles pour les voyageurs canadiens)"), ("aide", "Services d’urgence et aide sur place")]
COULEURS_NIVEAU = {0: "#2F7D6D", 1: "#C99A00", 2: "#D9822B", 3: "#B5485D"}


def slug_fd(nom):
    """Adresse probable de la fiche du ministère français (diplomatie.gouv.fr) pour un pays."""
    import unicodedata
    t = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def blocs_html(bl, visibles=8):
    """Blocs (titre, paragraphe, élément de liste) -> HTML ; au-delà de « visibles » paragraphes, « Lire la suite »."""
    out, liste, n, coupe = [], False, 0, None
    for i, (g, t) in enumerate(bl):
        if g != "l" and liste:
            out.append("</ul>"); liste = False
        if g == "t":
            out.append(f"<h4>{E(t)}</h4>")
        elif g == "l":
            if not liste:
                out.append("<ul>"); liste = True
            out.append(f"<li>{E(t)}</li>")
        else:
            out.append(f"<p>{E(t)}</p>")
            n += 1
        if coupe is None and n >= visibles and g != "l" and i < len(bl) - 3:
            coupe = len(out)
    if liste:
        out.append("</ul>")
    if coupe:
        return '<div class="prose">' + "".join(out[:coupe]) + '<details class="more"><summary>Lire la suite</summary>' + "".join(out[coupe:]) + "</details></div>"
    return '<div class="prose">' + "".join(out) + "</div>"


def extraits_arnaques(cv, n=10):
    """Passages des conseils de sécurité qui parlent d'arnaques et de fraudes."""
    bl, out, dedans = cv["sections"].get("securite", []), [], False
    for g, t in bl:
        if g == "t":
            dedans = bool(re.search(r"fraude|arnaque|escroquer|escroc", t, re.I))
            continue
        if dedans or (g != "t" and re.search(r"\barnaque|escroquer", t, re.I)):
            out.append([g, t])
        if len(out) >= n:
            break
    return out


def extraits_ville(cv, noms, n=5):
    """Passages des conseils qui citent la ville (quartiers, plages, gares à éviter…)."""
    out = []
    motifs = [re.compile(r"\b" + re.escape(x) + r"\b", re.I) for x in noms if x and len(x) > 3]
    for k in ("avertissements", "securite", "catastrophes_climat", "lois_culture"):
        for g, t in cv["sections"].get(k, []):
            if g != "t" and any(m.search(t) for m in motifs) and t not in out:
                out.append(t)
                if len(out) >= n:
                    return out
    return out


def page_conseils(cc, nomp, cv):
    niv = cv.get("niveau", 0)
    zones = [t for g, t in cv["sections"].get("avertissements", []) if g == "t"]
    nav = "".join(f'<a href="#{k}">{E(t.split(" :")[0].split(" (")[0])}</a>' for k, t in TITRES_CONSEILS if k in cv["sections"])
    corps = (f'<section class="hero"><p class="crumbs"><a href="../../../">Accueil</a> › <a href="../">{E(nomp)}</a></p>'
             f'<h1 class="city" style="font-size:clamp(2.2rem,6.5vw,4.2rem)">Conseils aux voyageurs : {E(nomp)}</h1>'
             f'<p class="tagline">Sécurité, zones à éviter, santé et vaccins, lois et coutumes, catastrophes naturelles, transports.</p></section>'
             f'<p class="alerte" style="--a:{COULEURS_NIVEAU.get(niv, "#56707A")}"><b>{E(cv.get("niveau_texte", ""))}</b>'
             f'{(" · Zones concernées : " + E(", ".join(zones[1:6])) + ("…" if len(zones) > 6 else "")) if len(zones) > 1 else ""}</p>'
             f'<p class="note">Source : <a href="{E(cv["url"])}" rel="noopener" target="_blank">Conseils aux voyageurs et avertissements du gouvernement du Canada</a> '
             f'(mis à jour le {E(cv.get("mise_a_jour", ""))}), en français, sous Licence du gouvernement ouvert – Canada. '
             f'<b>Pour les voyageurs français, la fiche du ministère de l’Europe et des Affaires étrangères fait foi :</b> '
             f'<a href="https://www.diplomatie.gouv.fr/fr/conseils-aux-voyageurs/conseils-par-pays-destination/{slug_fd(nomp)}/" rel="noopener" target="_blank">'
             f'Conseils aux voyageurs – {E(nomp)} (diplomatie.gouv.fr)</a>. Inscrivez-vous aussi sur Ariane.</p>'
             f'<div class="chips" style="margin:1rem 0 .5rem"><input type="search" class="recherche-lieux" id="cv-q" placeholder="Chercher dans ces conseils (vaccin, taxi, alcool, séisme…)" aria-label="Chercher dans les conseils"></div>'
             f'<nav class="og-sous" aria-label="Rubriques">{nav}</nav>')
    arn = extraits_arnaques(cv)
    if arn:
        corps += f'<section class="block cv-sec" id="arnaques"><h2>Arnaques et fraudes signalées</h2>{blocs_html(arn, 10)}</section>'
    for k, t in TITRES_CONSEILS:
        if k in cv["sections"]:
            corps += f'<section class="block cv-sec" id="{k}"><h2>{E(t)}</h2>{blocs_html(cv["sections"][k], 12 if k == "avertissements" else 8)}</section>'
    js = ("<script>(function(){var q=document.getElementById('cv-q');if(!q)return;function n(t){return (t||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');}"
          "q.addEventListener('input',function(){var t=n(q.value.trim());document.querySelectorAll('.cv-sec').forEach(function(s){var vu=0;"
          "s.querySelectorAll('p,li,h4').forEach(function(e){var ok=!t||n(e.textContent).indexOf(t)>-1;e.style.display=ok?'':'none';if(ok&&t)vu++;});"
          "s.querySelectorAll('details').forEach(function(d){if(t)d.open=true;});s.style.display=(!t||vu)?'':'none';});});})();</script>")
    return page("../../../", f"Conseils aux voyageurs {nomp} – Dix Mille Escales", f"Sécurité, santé, vaccins, lois et coutumes, zones à éviter : {nomp}.", corps).replace("</body>", js + "</body>")


def proches(villes, n=6):
    """Pour chaque ville, ses n plus proches voisines du guide (recherche par cases de 5°)."""
    cases = {}
    for v in villes:
        cases.setdefault((int(v["lat"] // 5), int(v["lon"] // 5)), []).append(v)
    for v in villes:
        ci, cj = int(v["lat"] // 5), int(v["lon"] // 5)
        r, cand = 1, []
        while len(cand) < 3 * n and r <= 8:
            cand = [w for i in range(ci - r, ci + r + 1) for j in range(cj - r, cj + r + 1) for w in cases.get((i, j), [])]
            r += 1
        dd = sorted(((dist((v["lat"], v["lon"]), (w["lat"], w["lon"])), w) for w in cand if w is not v), key=lambda x: x[0])
        loin = [x for x in dd if x[0] >= 8]  # éviter les quartiers d’une même métropole
        dd = loin if len(loin) >= n else dd
        v["proches"] = dd[:n]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limite", type=int, help="ne générer que les N premières villes")
    a = p.parse_args()
    t0 = datetime.now()
    villes = lire("villes.json", [])
    if not villes:
        sys.exit("data/villes.json introuvable.")
    for i, v in enumerate(villes, 1):
        v["rang"] = i
    pays = lire("pays.json", {})
    ctx = {"pays": pays, "change": lire("change.json", {}) or {}, "journal": lire("journal.json", {}) or {},
           "date_txt": date_fr(date.today().isoformat())}
    # Lieux et jours fériés déjà collectés
    # Lieux : on ne note ici que l'emplacement des fichiers ; ils sont lus ville par ville (des millions de lieux)
    ctx["lieux"] = {}
    for base in (DATA, DONNEES):
        dl = os.path.join(base, "lieux")
        for racine, _, fichiers in (os.walk(dl) if os.path.isdir(dl) else []):
            for fn in fichiers:
                if fn.startswith("_") or not (fn.endswith(".json") or fn.endswith(".json.gz")):
                    continue
                try:
                    vid = int(fn.split(".")[0])
                except ValueError:
                    continue
                ctx["lieux"].setdefault(vid, []).append(os.path.join(racine, fn))
    ctx["securite"] = lire("securite.json", {}) or {}
    ctx["cout"] = lire("cout.json", {}) or {}
    ctx["formalites"] = (lire("formalites.json", {}) or {}).get("passeports", {})
    ctx["aeroports"] = {}
    for base in (DONNEES, DATA):
        p_ = os.path.join(base, "aeroports.json.gz")
        if os.path.exists(p_):
            with gzip.open(p_, "rt", encoding="utf-8") as f:
                ctx["aeroports"] = json.load(f)
            break
    ctx["urgences"] = (lire("urgences.json", {}) or {}).get("pays", {})
    ctx["pratique"] = (lire("pratique.json", {}) or {}).get("pays", {})
    ctx["transports"] = {}
    dtr = os.path.join(DONNEES, "transports")
    if os.path.isdir(dtr):
        for fn in os.listdir(dtr):
            if fn.endswith(".json"):
                for k, x in (lire(f"transports/{fn}") or {}).items():
                    ctx["transports"][int(k)] = x
    ctx["conseils"] = {}
    dcv = os.path.join(DONNEES, "conseils")
    if os.path.isdir(dcv):
        for fn in os.listdir(dcv):
            if fn.endswith(".json"):
                ctx["conseils"][fn[:-5]] = lire(f"conseils/{fn}")
    diplo = {}
    dd = os.path.join(DONNEES, "diplomatie")
    if os.path.isdir(dd):
        for fn in os.listdir(dd):
            if fn.endswith(".json"):
                for x in lire(f"diplomatie/{fn}") or []:
                    diplo[x["id"]] = x
    ctx["diplo"] = list(diplo.values())
    ctx["monde"] = []
    ctx["compteur"] = {"informations": 0, "lieux": 0, "textes": 0, "photos": 0, "villes_enrichies": 0}
    ctx["feries"] = {}
    for base in (DATA, DONNEES):
        df = os.path.join(base, "feries")
        if os.path.isdir(df):
            for fn in os.listdir(df):
                ctx["feries"][fn[:-5]] = lire(f"feries/{fn}")
    journal = dict(ctx["journal"])
    dj = os.path.join(DONNEES, "journal")
    if os.path.isdir(dj):
        for fn in os.listdir(dj):
            if fn.endswith(".json"):
                journal[fn[:-5]] = lire(f"journal/{fn}")
    ctx["journal"] = journal
    # Capitales en français quand la ville est dans le guide
    ctx["capitales"] = {}
    for cc, pz in pays.items():
        m = next((v for v in villes if v["pays"] == cc and v["nom_local"] == pz.get("capitale")), None)
        ctx["capitales"][cc] = m["nom"] if m else pz.get("capitale", "")
    proches(villes)
    representations(villes, ctx)

    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    shutil.copytree(os.path.join(RACINE, "static"), os.path.join(SITE, "static"))

    # Index de recherche
    index = [[v["nom"], v["slug"], pays.get(v["pays"], {}).get("nom", v["pays"]), v["population"],
              "|".join(v["alts"]) if (v["population"] >= 30000 or v["niveau"] != "autre") else "|".join(v["alts"][:1]),
              1 if v["niveau"] == "phare" else 0] for v in villes]
    ecrire("static/index.json", json.dumps(index, ensure_ascii=False, separators=(",", ":")))

    # Pages de villes
    lot = villes[:a.limite] if a.limite else villes
    perso = 0
    for v in lot:
        chemin_perso = os.path.join(RACINE, "pages", v["slug"] + ".html")
        if os.path.exists(chemin_perso):
            txt = open(chemin_perso, encoding="utf-8").read().replace('class="brand" href="#"', 'class="brand" href="../../"')
            page_ville(v, ctx)  # pour exporter donnees.json et lieux.json (le HTML automatique est ignoré)
            ecrire(f"villes/{v['slug']}/index.html", avec_robots(txt))
            perso += 1
        else:
            ecrire(f"villes/{v['slug']}/index.html", page_ville(v, ctx))
    # Pages rédigées à la main pour des villes hors du lot de test
    for fn in os.listdir(os.path.join(RACINE, "pages")):
        slug = fn[:-5]
        if fn.endswith(".html") and not os.path.exists(os.path.join(SITE, "villes", slug, "index.html")):
            txt = open(os.path.join(RACINE, "pages", fn), encoding="utf-8").read().replace('class="brand" href="#"', 'class="brand" href="../../"')
            v = next((w for w in villes if w["slug"] == slug), None)
            if v:
                page_ville(v, ctx)
            ecrire(f"villes/{slug}/index.html", avec_robots(txt))
            perso += 1

    # Fichier mondial pour les outils, et pages des outils
    monde_pays = {}
    for cc, pz in pays.items():
        alerte_ = ctx["securite"].get("pays", {}).get(cc)
        cout_ = ctx["cout"].get("pays", {}).get(cc)
        dev = pz.get("monnaie", "")
        monde_pays[cc] = {"nom": pz.get("nom", cc), "cont": pz.get("continent", ""), "devise": dev, "monnaie": pz.get("monnaie_nom", ""),
                          "taux": ctx["change"].get("taux", {}).get(dev) if dev != "EUR" else 1, "langues": pz.get("langues", []),
                          "secu": alerte_["niveau"] if alerte_ else 0, "cout": cout_["indice"] if cout_ else None,
                          "visa": {pp: formalite_fr(ctx["formalites"].get(pp, {}).get(cc, ""), pp, cc) for pp in PASSEPORTS} if ctx["formalites"] else {},
                          "conseils": (ctx["conseils"].get(cc) or {}).get("niveau_texte", ""),
                          "prises": ctx["pratique"].get(cc, {}).get("prises", []), "conduite": ctx["pratique"].get(cc, {}).get("conduite"),
                          "palu": any(re.search(r"paludisme", t, re.I) for g, t in (ctx["conseils"].get(cc) or {}).get("sections", {}).get("sante", [])),
                          "dengue": any(re.search(r"dengue|chikungunya|zika", t, re.I) for g, t in (ctx["conseils"].get(cc) or {}).get("sections", {}).get("sante", [])),
                          "urgences": [x["numero"] + (" (" + ", ".join(x["services"]) + ")" if x["services"] else "") for x in ctx["urgences"].get(cc, [])]}
    ecrire_gz("static/monde.json.gz", {"date": ctx["date_txt"], "villes": ctx["monde"], "pays": monde_pays,
                                       "change": ctx["change"].get("taux", {}), "change_date": ctx["change"].get("jour_bce", "")})
    outils(ctx)

    # Compteur de données
    cpt = ctx["compteur"]
    cpt["villes"] = len(villes)
    cpt["informations"] += sum(1500 for fn in os.listdir(os.path.join(RACINE, "pages")) if fn.endswith(".html"))  # fiches rédigées à la main
    cpt["date"] = ctx["date_txt"]
    ecrire("static/compteur.json", json.dumps(cpt, ensure_ascii=False))

    # Accueil
    tzs, tzi, rows = [], {}, []
    for v in [w for w in villes if w["rang"] <= 15000 or w["niveau"] == "phare"]:
        if v["fuseau"] not in tzi:
            tzi[v["fuseau"]] = len(tzs); tzs.append(v["fuseau"])
        rows.append([v["nom"], v["pays"], v["lat"], v["lon"], v["population"], tzi[v["fuseau"]], "|".join(v["alts"]),
                     1 if v["niveau"] == "phare" else 0, v["slug"]])
    cont_n = {}
    for v in villes:
        k = pays.get(v["pays"], {}).get("continent", "")
        cont_n[k] = cont_n.get(k, 0) + 1
    tot = {"villes": len(villes), "pays": len({v["pays"] for v in villes}), "habitants": sum(v["population"] for v in villes), "continents": cont_n}
    donnees = json.dumps({"c": rows, "tz": tzs, "cont": {cc: pz["continent"] for cc, pz in pays.items()}, "tot": tot},
                         ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    accueil = open(os.path.join(RACINE, "templates", "accueil.html"), encoding="utf-8").read()
    ecrire("index.html", accueil.replace("__DATA__", donnees).replace("__DATE__", ctx["date_txt"])
           .replace("__INFOS__", str(cpt["informations"])).replace("__LIEUX__", nombre(cpt["lieux"]))
           .replace("__TEXTES__", nombre(cpt["textes"])).replace("__ENRICHIES__", nombre(cpt["villes_enrichies"])))

    # Pages Pays : toutes les villes d'un pays, et l'index des pays par continent
    par_pays = {}
    for v in villes:
        par_pays.setdefault(v["pays"], []).append(v)
    blocs_cont = {}
    for cc, lv in par_pays.items():
        pz = pays.get(cc, {})
        nomp = pz.get("nom", cc)
        blocs_cont.setdefault(pz.get("continent", ""), []).append((nomp, cc, len(lv)))
        phares = [v for v in lv if v["niveau"] == "phare"]
        grandes = [v for v in lv if v["niveau"] != "phare"][:60]
        visa = formalite_fr(ctx["formalites"].get("FR", {}).get(cc, ""), "FR", cc) if ctx["formalites"] else ""
        alerte = ctx["securite"].get("pays", {}).get(cc)
        cout = ctx["cout"].get("pays", {}).get(cc)
        faits = [("Continent", CONTINENTS.get(pz.get("continent", ""), "")), ("Capitale", ctx["capitales"].get(cc, pz.get("capitale", ""))),
                 ("Langues", maj(", ".join(pz.get("langues", [])))), ("Monnaie", maj(pz.get("monnaie_nom", ""))), ("Indicatif", pz.get("indicatif", "")),
                 ("Villes dans le guide", nombre(len(lv))), ("Visa (passeport français)", visa)]
        if alerte:
            faits.append(("Sécurité", f'{alerte["niveau"]} sur 4, {NIVEAU_ALERTE[alerte["niveau"]][0].lower()}'))
        if cout:
            faits.append(("Niveau des prix", f'{round(cout["indice"] * 100)} % de la France'))
        dl = "".join(f"<div><dt>{E(k)}</dt><dd>{E(x)}</dd></div>" for k, x in faits if x)
        lien = lambda w: f'<a href="../../villes/{w["slug"]}/">{E(w["nom"])}<span>{nombre(w["population"])} hab.</span></a>'
        corps = (f'<section class="hero"><p class="crumbs"><a href="../../">Accueil</a> › <a href="../#{pz.get("continent", "")}">{E(CONTINENTS.get(pz.get("continent", ""), ""))}</a></p>'
                 f'<h1 class="city">{E(nomp)}</h1><p class="tagline">{nombre(len(lv))} villes de plus de 5 000 habitants dans le guide.</p></section>'
                 f'<section class="facts"><dl>{dl}</dl></section>'
                 + (f'<section class="block"><h2>Villes phares</h2><div class="near">{"".join(lien(w) for w in phares)}</div></section>' if phares else "")
                 + f'<section class="block"><h2>Les plus grandes villes</h2><div class="near">{"".join(lien(w) for w in grandes)}</div></section>'
                 + (f'<section class="block"><h2>Toutes les villes ({nombre(len(lv))})</h2><div class="chips"><input type="search" class="recherche-lieux" id="pays-q" '
                    f'placeholder="Chercher parmi les {nombre(len(lv))} villes de ce pays…" aria-label="Chercher une ville du pays"></div>'
                    f'<div class="near" id="pays-liste" data-pays="{E(nomp)}"></div><p class="note" id="pays-note"></p></section>' if len(lv) > len(phares) + len(grandes) else ""))
        cv = ctx["conseils"].get(cc)
        if cv:
            ecrire(f"pays/{cc.lower()}/conseils/index.html", page_conseils(cc, nomp, cv))
            corps = corps.replace('<section class="facts">', f'<p class="alerte" style="--a:{COULEURS_NIVEAU.get(cv.get("niveau", 0), "#56707A")}"><b>{E(cv.get("niveau_texte", ""))}.</b> '
                                  f'<a href="conseils/">Lire les conseils aux voyageurs : sécurité, santé et vaccins, lois, transports…</a></p><section class="facts">', 1)
        ecrire(f"pays/{cc.lower()}/index.html", page("../../", f"{nomp} : toutes les villes – Dix Mille Escales",
               f"Guide de voyage {nomp} : {len(lv)} villes, visa, sécurité, monnaie, langues.", corps).replace("</body>", PAYS_JS + "</body>"))
    cont_html = ""
    for code in ("EU", "AS", "AF", "NA", "SA", "OC", "AN"):
        l = sorted(blocs_cont.get(code, []))
        if l:
            cont_html += (f'<section class="block" id="{code}"><h2>{CONTINENTS[code]}</h2><div class="near">'
                          + "".join(f'<a href="{cc.lower()}/">{E(n)}<span>{nombre(k)} villes</span></a>' for n, cc, k in l) + "</div></section>")
    ecrire("pays/index.html", page("../", "Tous les pays – Dix Mille Escales", "Les pays du guide et leurs villes, par continent.",
           f'<section class="hero"><h1 class="city" style="font-size:clamp(2.4rem,7vw,4.5rem)">Tous les pays</h1>'
           f'<p class="tagline">{len(par_pays)} pays et territoires, {nombre(len(villes))} villes. Choisissez un pays pour voir toutes ses villes.</p></section>' + cont_html))

    # Page Sources
    sources = [("GeoNames", "https://www.geonames.org/", "Liste des villes, population, coordonnées, fuseaux horaires", "CC BY 4.0"),
               ("OpenStreetMap", "https://www.openstreetmap.org/copyright", "Lieux, adresses, horaires", "© contributeurs OpenStreetMap, ODbL"),
               ("Open-Meteo", "https://open-meteo.com/", "Prévisions météo", "CC BY 4.0"),
               ("Nager.Date", "https://date.nager.at/", "Jours fériés", "Données publiques"),
               ("Banque centrale européenne", "https://www.ecb.europa.eu/", "Taux de change de référence", "Données publiques"),
               ("CLDR (Unicode)", "https://cldr.unicode.org/", "Noms des pays, langues et monnaies en français", "Licence Unicode"),
               ("Wikidata", "https://www.wikidata.org/", "Fondation, événements, maires, jumelages, patrimoine, personnalités", "CC0"),
               ("Wikipédia en français", "https://fr.wikipedia.org/", "Résumés et sections Histoire, Culture, Gastronomie…", "CC BY-SA 4.0, textes repris avec lien vers l’article"),
               ("Wikimedia Commons", "https://commons.wikimedia.org/", "Photos, blasons et drapeaux", "Licence propre à chaque image, créditée sous la photo"),
               ("Open-Meteo, archive ERA5", "https://open-meteo.com/", "Qualité de l’air (et premières normales climatiques)", "CC BY 4.0"),
               ("NASA POWER", "https://power.larc.nasa.gov/", "Normales climatiques mois par mois (1991-2020)", "Données ouvertes de la NASA"),
               ("Passport Index Data", "https://github.com/imorte/passport-index-data", "Visas et durées de séjour", "MIT"),
               ("U.S. Department of State", "https://travel.state.gov/", "Niveau de sécurité par pays", "Domaine public"),
               ("Banque mondiale", "https://data.worldbank.org/", "Niveau des prix par pays (PA.NUS.PPPC.RF)", "CC BY 4.0"),
               ("Claude (Anthropic)", "https://www.anthropic.com/", "Rédaction des conseils à partir des données", "Textes originaux du site"),
               ("Wikivoyage en français", "https://fr.wikivoyage.org/", "Conseils de voyage : s’y rendre, se déplacer, voir, manger, se loger…", "CC BY-SA 3.0, textes repris avec lien vers l’article"),
               ("OurAirports", "https://ourairports.com/data/", "Aéroports les plus proches", "Domaine public"),
               ("OpenFreeMap", "https://openfreemap.org/", "Fond de la carte interactive", "Gratuit, données © OpenStreetMap"),
               ("Gouvernement du Canada, Conseils aux voyageurs", "https://voyage.gc.ca/", "Niveaux de risque, zones à éviter, sécurité, santé, lois, catastrophes naturelles", "Licence du gouvernement ouvert – Canada"),
               ("Geofabrik", "https://download.geofabrik.de/", "Fichiers OpenStreetMap par région", "Données © OpenStreetMap (ODbL)")]
    lignes = "".join(f'<tr><td><a href="{u}" rel="noopener">{E(n)}</a></td><td>{E(r)}</td><td>{E(l)}</td></tr>' for n, u, r, l in sources)
    ecrire("sources/index.html", page("../", "Nos sources – Dix Mille Escales", "Sources et licences des données du guide.",
           f'<section class="hero"><h1 class="city" style="font-size:clamp(2.4rem,7vw,4.5rem)">Nos sources</h1>'
           f'<p class="tagline">Toutes les données du guide viennent de sources ouvertes ou officielles. Leur licence impose de les citer.</p></section>'
           f'<div class="table-scroll"><table><thead><tr><th>Source</th><th>Ce qu’elle apporte</th><th>Licence</th></tr></thead><tbody>{lignes}</tbody></table></div>'))

    # Page État des robots
    suivi = {}
    for base in (DATA, DONNEES):
        dl = os.path.join(base, "lieux")
        if os.path.isdir(dl):
            for fn in os.listdir(dl):
                if fn.startswith("_suivi") and fn.endswith(".json"):
                    with open(os.path.join(dl, fn), encoding="utf-8") as f:
                        suivi.update(json.load(f))
    noms = {"guides": "Guides (Wikivoyage)", "aeroports": "Aéroports (OurAirports)", "surveillance_etat": "Surveillance (rapport du matin)", "villes": "Liste des villes (GeoNames)", "lieux_0": "Lieux, robot 1 (OpenStreetMap)", "lieux_1": "Lieux, robot 2 (OpenStreetMap)",
            "lieux_2": "Lieux, robot 3 (OpenStreetMap)", "lieux_3": "Lieux, robot 4 (OpenStreetMap)", "conseils": "Conseils aux voyageurs (Canada)", "pratique": "Prises, tension, conduite (Wikidata)", "urgences": "Numéros d’urgence (Wikidata)", "meteo": "Météo (Open-Meteo)", "redaction": "Rédaction (IA)", "climat": "Climat (Open-Meteo ERA5)", "securite": "Sécurité (Département d’État)",
            "formalites": "Formalités (Passport Index)", "cout": "Coût de la vie (Banque mondiale)", "encyclopedie": "Encyclopédie (Wikidata, Wikipédia)", "lieux": "Lieux (OpenStreetMap)", "meteo": "Météo (Open-Meteo)", "feries": "Jours fériés (Nager.Date)", "change": "Change (BCE)"}
    lignes = ""
    for k, n in noms.items():
        j = ctx["journal"].get(k)
        if j:
            det = ", ".join(f"{kk.replace('_', ' ')} : {vv}" for kk, vv in j.items() if kk not in ("etat", "dernier_passage"))
            lignes += f'<tr><td>{n}</td><td>{E(j["etat"])}</td><td>{date_fr(j["dernier_passage"])} à {j["dernier_passage"][11:16]} UTC</td><td>{E(det)}</td></tr>'
        else:
            lignes += f'<tr><td>{n}</td><td>pas encore lancé</td><td>–</td><td></td></tr>'
    couv = {niv: sum(1 for v in villes if v["niveau"] == niv and str(v["id"]) in suivi) for niv in NIVEAUX}
    tot = {niv: sum(1 for v in villes if v["niveau"] == niv) for niv in NIVEAUX}
    infos = sum(s.get("infos", 0) for s in suivi.values())
    couverture = "".join(f'<tr><td>{NIVEAUX[n]}</td><td>{nombre(couv[n])} / {nombre(tot[n])}</td><td>{FREQ[n]}</td></tr>' for n in NIVEAUX)
    ecrire("etat/index.html", page("../", "État des robots – Dix Mille Escales", "Fraîcheur des données du guide.",
           f'<section class="hero"><h1 class="city" style="font-size:clamp(2.4rem,7vw,4.5rem)">État des robots</h1>'
           f'<p class="tagline">{nombre(infos)} informations de lieux collectées à ce jour. Page régénérée le {ctx["date_txt"]}.</p></section>'
           f'<section class="block"><h2>Derniers passages</h2><div class="table-scroll"><table><thead><tr><th>Robot</th><th>État</th><th>Dernier passage</th><th>Détails</th></tr></thead><tbody>{lignes}</tbody></table></div></section>'
           f'<section class="block"><h2>Couverture des villes</h2><div class="table-scroll"><table><thead><tr><th>Niveau</th><th>Villes explorées</th><th>Rythme de passage</th></tr></thead><tbody>{couverture}</tbody></table></div></section>'))

    # Mentions légales
    ecrire("mentions-legales/index.html", page("../", "Mentions légales – Dix Mille Escales", "Mentions légales du site Dix Mille Escales.",
           '<section class="hero"><h1 class="city" style="font-size:clamp(2.4rem,7vw,4.5rem)">Mentions légales</h1></section><div class="prose">'
           '<h2>Éditeur du site</h2><p>Dix Mille Escales est un site personnel et non commercial. Éditeur : <b>[NOM ET PRÉNOM À COMPLÉTER]</b>, '
           'joignable via <a href="https://github.com/' + os.environ.get("GITHUB_REPOSITORY", "pablopacaut17-sudo/dix-mille-escales") + '/issues">les « issues » du dépôt GitHub</a>.</p>'
           '<h2>Hébergement</h2><p>GitHub Pages, service de GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis.</p>'
           '<h2>Données personnelles et cookies</h2><p>Le site ne crée pas de compte, ne dépose aucun cookie publicitaire ni de mesure d’audience. '
           'Seul le choix du thème (clair ou sombre) est mémorisé dans votre navigateur, sans quitter votre appareil. L’hébergeur peut conserver '
           'des journaux techniques de connexion (adresse IP) pour la sécurité du service.</p>'
           '<h2>Contenus et licences</h2><p>Les données proviennent de sources ouvertes listées sur la page <a href="../sources/">Nos sources</a>, '
           'avec leurs licences : © contributeurs OpenStreetMap (ODbL), Wikipédia et Wikivoyage (CC BY-SA), Wikidata (CC0), GeoNames et Open-Meteo (CC BY 4.0)… '
           'Les textes repris de Wikipédia et de Wikivoyage restent sous licence CC BY-SA.</p>'
           '<h2>Exactitude des informations</h2><p>Les informations sont collectées automatiquement et vérifiées régulièrement, mais peuvent contenir des erreurs '
           'ou être devenues inexactes. Vérifiez toujours les informations importantes (visa, sécurité, santé, horaires) auprès des sources officielles avant de partir. '
           'Chaque fiche propose un lien « Signaler une erreur ».</p></div>'))

    # Page 404, plan du site, robots.txt
    ecrire("404.html", page("/", "Page introuvable – Dix Mille Escales", "Page introuvable.",
           '<section class="hero"><h1 class="city" style="font-size:clamp(2.4rem,7vw,4.5rem)">Cette page n’existe pas</h1>'
           '<p class="tagline">Cherchez une ville avec le champ en haut de page, ou revenez à la <a href="/">carte du monde</a>.</p></section>'))
    base = os.environ.get("SITE_URL", "").rstrip("/")
    if base:
        urls = [f"{base}/"] + [f"{base}/villes/{v['slug']}/" for v in lot]
        ecrire("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               + "".join(f"<url><loc>{E(u)}</loc></url>" for u in urls) + "</urlset>")
        ecrire("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    else:
        ecrire("robots.txt", "User-agent: *\nAllow: /\n")

    taille = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(SITE) for f in fs)
    print(f"Taille du site : {taille / 1024 / 1024:.0f} Mo sur 1 024 Mo autorisés par GitHub Pages.")
    if taille > LIMITE_SITE:
        print("ATTENTION : le site approche la limite de 1 Go de GitHub Pages. Réduire EN_LIGNE ou SECTIONS_AUTRES dans build.py.")
    ctx["taille_site"] = taille
    cpt["taille_site_mo"] = round(taille / 1024 / 1024)
    ecrire("static/compteur.json", json.dumps(cpt, ensure_ascii=False))
    nb = len(lot) + (perso if a.limite else 0)
    print(f"Site généré dans site/ : accueil + {nombre(len(lot))} pages de villes ({perso} rédigées à la main), "
          f"{len(ctx['lieux'])} villes avec des lieux, en {(datetime.now() - t0).seconds} s.")


if __name__ == "__main__":
    main()
