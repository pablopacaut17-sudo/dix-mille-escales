#!/usr/bin/env python3
"""
Dix Mille Escales – générateur du site.

Lit les données (data/) produites par les robots et fabrique le site complet dans le dossier site/ :
  - la page d'accueil avec la carte des 10 000 villes ;
  - une page par ville (villes/<nom-pays>/), ou la page rédigée à la main si elle existe dans pages/ ;
  - l'index de recherche, les pages « Nos sources » et « État des robots », le plan du site.

  python3 build.py                  # génère tout
  python3 build.py --limite 50      # seulement les 50 premières villes (test rapide)
Variable facultative : SITE_URL (ex. https://dixmilleescales.fr) pour le plan du site.
"""
import argparse, html, json, math, os, shutil, sys
from datetime import date, datetime, timezone

RACINE = os.path.dirname(os.path.abspath(__file__))
DATA, SITE = os.path.join(RACINE, "data"), os.path.join(RACINE, "site")
E = html.escape
CONTINENTS = {"EU": "Europe", "AF": "Afrique", "AS": "Asie", "NA": "Amérique du Nord et centrale",
              "SA": "Amérique du Sud", "OC": "Océanie", "AN": "Antarctique"}
NIVEAUX = {"phare": "Ville phare", "intermediaire": "Ville intermédiaire", "autre": "Ville du guide"}
FREQ = {"phare": "chaque semaine", "intermediaire": "chaque mois", "autre": "tous les trois mois"}
RUBRIQUES = [("voir", "À voir", "Monuments, musées, belvédères, parcs et sites recensés autour du centre-ville."),
             ("manger", "Manger et boire", "Restaurants, cafés, bars et glaciers."),
             ("dormir", "Dormir", "Hôtels, auberges de jeunesse et maisons d’hôtes."),
             ("acheter", "Acheter", "Marchés, librairies, épiceries fines, artisanat et souvenirs.")]
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
    p = os.path.join(DATA, nom)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else defaut


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
        if 18 <= m["tmax"] <= 29 and m["jours_pluie"] <= 8:
            out.append((i, "ideal"))
        elif 12 <= m["tmax"] <= 33 and m["jours_pluie"] <= 13:
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


def maj(t):
    return t[:1].upper() + t[1:]


def meteo_fr(code):
    return next((t for codes, t in METEO if code in codes), "Variable")


def page(root, titre, description, corps, recherche=True):
    """Gabarit commun à toutes les pages générées. root = chemin relatif vers la racine du site."""
    rech = ('<form class="search" role="search" onsubmit="return false"><label for="q" class="vh">Chercher une ville</label>'
            '<input id="q" type="search" autocomplete="off" placeholder="Chercher une ville parmi 10 000">'
            '<ul id="results"></ul></form>') if recherche else ""
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(titre)}</title><meta name="description" content="{E(description)}">
{FONTS}<link rel="stylesheet" href="{root}static/style.css"></head>
<body data-root="{root}">
<header class="top"><div class="top-in"><a class="brand" href="{root}">{LOGO}Dix Mille Escales</a>{rech}
<button type="button" class="theme-btn" id="theme-btn" aria-label="Changer le thème d’affichage">Thème : auto</button></div></header>
<main class="wrap">{corps}</main>
<footer class="foot"><div class="in"><p>Dix Mille Escales, le guide des 10 000 plus grandes villes du monde. Données mises à jour en continu par nos robots.</p>
<p><a href="{root}sources/">Nos sources</a> · <a href="{root}etat/">État des robots</a></p></div></footer>
<script src="{root}static/app.js"></script></body></html>"""


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
            '<span style="--c:var(--acheter)">Acheter</span></figcaption></figure>')


def liste_lieux(rub, items):
    items = sorted(items, key=lambda f: (-f["infos"], f["nom"]))
    def li(f):
        meta = " · ".join(x for x in (f["type"], f.get("cuisine"), (f["etoiles"] + " étoiles") if f.get("etoiles") else "",
                                      "payant" if f.get("payant") == "oui" else "gratuit" if f.get("payant") == "non" else "",
                                      "accessible en fauteuil" if f.get("fauteuil") == "oui" else "",
                                      "terrasse" if f.get("terrasse") == "oui" else "") if x)
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
    visibles = items[:MAX_PAR_RUBRIQUE]
    html_ = f'<div class="chips" data-filter-for="l-{rub}"></div><ul class="places" id="l-{rub}">' + "".join(li(f) for f in visibles) + "</ul>"
    if len(items) > len(visibles):
        html_ += f'<p class="note">Et {nombre(len(items) - len(visibles))} autres lieux recensés, classés après les fiches les plus complètes.</p>'
    return html_


def page_ville(v, ctx):
    pays = ctx["pays"].get(v["pays"], {})
    nom_pays = pays.get("nom", v["pays"])
    cont = CONTINENTS.get(pays.get("continent", ""), "")
    rubs = ctx["lieux"].get(v["id"])
    lieux = rubs["lieux"] if rubs else []
    meteo = lire(f"meteo/{v['id']}.json")
    enc = lire(f"encyclo/{v['id']}.json") or {}
    clim = (lire(f"climat/{v['id']}.json") or {})
    red = lire(f"redaction/{v['id']}.json") or {}
    alerte = ctx["securite"].get("pays", {}).get(v["pays"])
    cout = ctx["cout"].get("pays", {}).get(v["pays"])
    wp = enc.get("wikipedia") or {}
    wps = wp.get("sections", {})
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
        + sum(len(red.get(k, [])) for k in ("pourquoi", "conseils", "a_eviter", "un_jour", "trois_jours")) + (3 if red else 0)
    total_infos = infos_base + sum(f["infos"] for f in lieux) + (len(meteo["jours"]) * 4 if meteo else 0) + (len(feries["jours"]) * 2 if feries else 0)
    coords = (f'{abs(v["lat"]):.2f}° {"N" if v["lat"] >= 0 else "S"} / {abs(v["lon"]):.2f}° {"E" if v["lon"] >= 0 else "O"}').replace(".", ",")
    badge = f'<span class="badge">{NIVEAUX[v["niveau"]]}</span>' if v["niveau"] == "phare" else ""

    facts = [("Pays", nom_pays), ("Habitants", nombre(v["population"])), ("Rang dans le guide", f'{nombre(v["rang"])}ᵉ ville'),
             ("Heure locale", f'<span data-tz="{E(v["fuseau"])}">–</span>'), ("Décalage", f'<span data-offset="{E(v["fuseau"])}">–</span>'),
             ("Saison", f'<span data-season="{v["lat"]}">–</span>'),
             ("Soleil aujourd’hui", f'<span data-sun="{v["lat"]},{v["lon"]}" data-suntz="{E(v["fuseau"])}">–</span>'),
             ("Depuis Paris", trajet)]
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
    corps = [photo + f'''<section class="hero"><p class="crumbs"><a href="../../">Accueil</a> › {E(cont)} › {E(nom_pays)}</p>
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
        i
