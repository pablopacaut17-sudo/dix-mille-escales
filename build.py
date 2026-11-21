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
             ("faire", "Activités", "Plages, baignade, sports nautiques, parcs d’attractions, golf, ski et autres loisirs."),
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
<p><span data-compteur>…</span> informations dans le guide · <a href="{root}sources/">Nos sources</a> · <a href="{root}etat/">État des robots</a></p></div></footer>
<script src="{root}static/app.js"></script><script src="{root}static/questions.js"></script></body></html>"""


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
    tous = rubs["lieux"] if rubs else []
    lieux = [f for f in tous if f["rubrique"] != "alentours"]
    autour = sorted([f for f in tous if f["rubrique"] == "alentours"], key=lambda f: f.get("distance_km", 0))
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
    total_infos = infos_base + sum(f["infos"] + (2 if f.get("distance_km") else 0) for f in tous) + (len(meteo["jours"]) * 4 if meteo else 0) + (len(feries["jours"]) * 2 if feries else 0)
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
        corps.append(f'<section class="block"><h2>Météo des 7 prochains jours</h2><div class="weather">{jours}</div>'
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
                         f'<td>{round(m["tmin"]) if m["tmin"] is not None else "–"}°</td><td>{m["pluie_mm"]} mm</td><td>{m["jours_pluie"]}</td>'
                         f'<td>{str(m["soleil_h"]).replace(".", ",") + " h" if m["soleil_h"] is not None else "–"}</td></tr>' for i, m in enumerate(mois))
        corps.append(f'<section class="block" id="quand-partir"><h2>Quand partir</h2><p class="lead">{phrase} {E(red.get("quand_partir", ""))}</p>'
                     f'<div class="climat" aria-hidden="true">{barres}</div>'
                     '<p class="legend"><span style="--c:var(--sea)">Période idéale</span><span style="--c:var(--dot)">Possible</span>'
                     '<span style="--c:#c5ced0">Moins favorable</span><span style="--c:#5B8DC9">Pluie</span></p>'
                     f'<details class="more"><summary>Voir le tableau mois par mois</summary><div class="table-scroll"><table><thead><tr><th>Mois</th><th>Max.</th><th>Min.</th>'
                     f'<th>Pluie</th><th>Jours de pluie</th><th>Soleil par jour</th></tr></thead><tbody>{lignes}</tbody></table></div></details>'
                     f'<p class="note">Moyennes {clim["periode"].replace("-", " à ")} calculées à partir de l’archive météo ERA5 (Open-Meteo).</p></section>')

    # Lieux
    if lieux:
        corps.append(f'<section class="block"><h2>Les lieux de {E(v["nom"])}</h2><p class="lead">{nombre(len(lieux))} lieux recensés dans un rayon de '
                     f'{str(rubs.get("rayon_km", "")).replace(".", ",")} km autour du centre, et {nombre(len(autour))} sites notables aux alentours. Données vérifiées le {date_fr(rubs["date"])}.</p>'
                     + carte_lieux(v, lieux, rubs.get("rayon_km", 3)) + "</section>")
        for rub, titre, desc in RUBRIQUES:
            items = [f for f in lieux if f["rubrique"] == rub]
            if items:
                corps.append(f'<section class="block" id="{rub}"><h2>{titre}</h2><p class="lead">{desc} {nombre(len(items))} adresse{"s" if len(items) > 1 else ""}.</p>{liste_lieux(rub, items)}</section>')
    if autour or v["proches"]:
        corps.append(section_alentours(v, autour, rubs))
    if not lieux:
        corps.append(f'<section class="block"><h2>Lieux, adresses et visites</h2><p class="empty">Les robots n’ont pas encore exploré {E(v["nom"])}. '
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
            corps.append(f'<section class="block"><h2>Jours fériés à venir</h2><div class="table-scroll"><table><thead><tr><th>Date</th>'
                         f'<th>Nom local</th><th>Nom anglais</th></tr></thead><tbody>{lignes}</tbody></table></div>'
                         f'<p class="note">Jours fériés nationaux, source Nager.Date. Commerces et musées peuvent être fermés.</p></section>')

    # Villes proches
    proches = "".join(f'<a href="../{w["slug"]}/">{E(w["nom"])}<span>{nombre(round(d))} km</span></a>' for d, w in v["proches"])
    corps.append(f'<section class="block"><h2>Villes proches</h2><div class="near">{proches}</div></section>')
    ancres = [("en-bref", "En bref"), ("avis", "Notre avis"), ("histoire", "Histoire"), ("quand-partir", "Quand partir"), ("budget", "Budget"), ("formalites", "Formalités"),
              ("faire", "Activités"), ("alentours", "Aux alentours"), ("voir", "À voir"), ("manger", "Manger et boire"), ("dormir", "Dormir"),
              ("acheter", "Acheter"), ("patrimoine", "Patrimoine"), ("culture", "Culture"), ("gastronomie", "Gastronomie"),
              ("geographie", "Géographie"), ("personnalites", "Personnalités")]
    presentes = [(a, t) for a, t in ancres if any(f'id="{a}"' in b for b in corps)]
    if len(presentes) >= 3:
        corps.insert(sommaire_pos, '<nav class="sommaire" aria-label="Dans cette fiche">' + "".join(f'<a href="#{a}">{t}</a>' for a, t in presentes) + "</nav>")
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
    donnees = {"nom": v["nom"], "slug": v["slug"], "pays": nom_pays, "population": v["population"], "rang": v["rang"],
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
    red_ok = {k: red[k] for k in ("accroche", "conseils", "a_eviter", "quand_partir", "un_jour") if red.get(k)}
    if red_ok:
        donnees["avis"] = red_ok
    ecrire(f"villes/{v['slug']}/donnees.json", json.dumps(donnees, ensure_ascii=False, separators=(",", ":")))
    cpt = ctx["compteur"]
    cpt["informations"] += total_infos
    cpt["lieux"] += len(tous)
    cpt["textes"] += len(wps) + (1 if wp.get("resume") else 0)
    cpt["photos"] += 1 if enc.get("photo") else 0
    cpt["villes_enrichies"] += 1 if (tous or enc) else 0

    desc = f"Guide de voyage de {v['nom']} ({nom_pays}) : lieux à voir, où manger, où dormir, météo, jours fériés et infos pratiques."
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
        for f in autour[:300]:
            typ, ident = f["id"][4:].split("/")
            h += (f'<li data-type="{E(f["type"])}" style="--c:var(--alentours)"><h3>{E(f["nom"])}</h3>'
                  f'<div class="m">{E(f["type"])} · {str(f["distance_km"]).replace(".", ",")} km {E(f["direction"])}'
                  f'{" · patrimoine mondial" if f.get("patrimoine_mondial") else ""}</div>'
                  + (f'<div class="i">Horaires : {E(horaires_fr(f["horaires"]))}</div>' if f.get("horaires") else "")
                  + f'<div class="i"><a href="https://www.openstreetmap.org/{typ}/{ident}" rel="nofollow noopener" target="_blank">Carte</a></div></li>')
        h += "</ul>"
    return h + "</section>"


def duree(km):
    h = km * 1.3 / 70  # détours de la route, 70 km/h de moyenne
    if h < 1:
        return f"{max(10, round(h * 60 / 5) * 5)} min"
    return f"{int(h)} h {round((h % 1) * 60 / 5) * 5:02d}".replace(" 00", "")


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
    ctx["lieux"] = {}
    dl = os.path.join(DATA, "lieux")
    if os.path.isdir(dl):
        for fn in os.listdir(dl):
            if fn.endswith(".json") and not fn.startswith("_"):
                d = lire(f"lieux/{fn}")
                ctx["lieux"][d["ville"]] = d
    ctx["securite"] = lire("securite.json", {}) or {}
    ctx["cout"] = lire("cout.json", {}) or {}
    ctx["formalites"] = (lire("formalites.json", {}) or {}).get("passeports", {})
    ctx["compteur"] = {"informations": 0, "lieux": 0, "textes": 0, "photos": 0, "villes_enrichies": 0}
    ctx["feries"] = {}
    df = os.path.join(DATA, "feries")
    if os.path.isdir(df):
        for fn in os.listdir(df):
            ctx["feries"][fn[:-5]] = lire(f"feries/{fn}")
    # Capitales en français quand la ville est dans le guide
    ctx["capitales"] = {}
    for cc, pz in pays.items():
        m = next((v for v in villes if v["pays"] == cc and v["nom_local"] == pz.get("capitale")), None)
        ctx["capitales"][cc] = m["nom"] if m else pz.get("capitale", "")
    proches(villes)

    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    shutil.copytree(os.path.join(RACINE, "static"), os.path.join(SITE, "static"))

    # Index de recherche
    index = [[v["nom"], v["slug"], pays.get(v["pays"], {}).get("nom", v["pays"]), v["population"], "|".join(v["alts"])] for v in villes]
    ecrire("static/index.json", json.dumps(index, ensure_ascii=False, separators=(",", ":")))

    # Pages de villes
    lot = villes[:a.limite] if a.limite else villes
    perso = 0
    for v in lot:
        chemin_perso = os.path.join(RACINE, "pages", v["slug"] + ".html")
        if os.path.exists(chemin_perso):
            txt = open(chemin_perso, encoding="utf-8").read().replace('class="brand" href="#"', 'class="brand" href="../../"')
            ecrire(f"villes/{v['slug']}/index.html", txt)
            page_ville(v, ctx)  # pour exporter donnees.json (le HTML automatique est ignoré)
            ecrire(f"villes/{v['slug']}/index.html", txt)
            perso += 1
        else:
            ecrire(f"villes/{v['slug']}/index.html", page_ville(v, ctx))
    # Pages rédigées à la main pour des villes hors du lot de test
    for fn in os.listdir(os.path.join(RACINE, "pages")):
        slug = fn[:-5]
        if fn.endswith(".html") and not os.path.exists(os.path.join(SITE, "villes", slug, "index.html")):
            txt = open(os.path.join(RACINE, "pages", fn), encoding="utf-8").read().replace('class="brand" href="#"', 'class="brand" href="../../"')
            ecrire(f"villes/{slug}/index.html", txt)
            perso += 1

    # Compteur de données
    cpt = ctx["compteur"]
    cpt["villes"] = len(villes)
    cpt["informations"] += sum(1500 for fn in os.listdir(os.path.join(RACINE, "pages")) if fn.endswith(".html"))  # fiches rédigées à la main
    cpt["date"] = ctx["date_txt"]
    ecrire("static/compteur.json", json.dumps(cpt, ensure_ascii=False))

    # Accueil
    tzs, tzi, rows = [], {}, []
    for v in villes:
        if v["fuseau"] not in tzi:
            tzi[v["fuseau"]] = len(tzs); tzs.append(v["fuseau"])
        rows.append([v["nom"], v["pays"], v["lat"], v["lon"], v["population"], tzi[v["fuseau"]], "|".join(v["alts"]),
                     1 if v["niveau"] == "phare" else 0, v["slug"]])
    donnees = json.dumps({"c": rows, "tz": tzs, "cont": {cc: pz["continent"] for cc, pz in pays.items()}},
                         ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    accueil = open(os.path.join(RACINE, "templates", "accueil.html"), encoding="utf-8").read()
    ecrire("index.html", accueil.replace("__DATA__", donnees).replace("__DATE__", ctx["date_txt"])
           .replace("__INFOS__", str(cpt["informations"])).replace("__LIEUX__", nombre(cpt["lieux"]))
           .replace("__TEXTES__", nombre(cpt["textes"])).replace("__ENRICHIES__", nombre(cpt["villes_enrichies"])))

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
               ("Open-Meteo, archive ERA5", "https://open-meteo.com/", "Normales climatiques et qualité de l’air", "CC BY 4.0"),
               ("Passport Index Data", "https://github.com/imorte/passport-index-data", "Visas et durées de séjour", "MIT"),
               ("U.S. Department of State", "https://travel.state.gov/", "Niveau de sécurité par pays", "Domaine public"),
               ("Banque mondiale", "https://data.worldbank.org/", "Niveau des prix par pays (PA.NUS.PPPC.RF)", "CC BY 4.0"),
               ("Claude (Anthropic)", "https://www.anthropic.com/", "Rédaction des conseils à partir des données", "Textes originaux du site")]
    lignes = "".join(f'<tr><td><a href="{u}" rel="noopener">{E(n)}</a></td><td>{E(r)}</td><td>{E(l)}</td></tr>' for n, u, r, l in sources)
    ecrire("sources/index.html", page("../", "Nos sources – Dix Mille Escales", "Sources et licences des données du guide.",
           f'<section class="hero"><h1 class="city" style="font-size:clamp(2.4rem,7vw,4.5rem)">Nos sources</h1>'
           f'<p class="tagline">Toutes les données du guide viennent de sources ouvertes ou officielles. Leur licence impose de les citer.</p></section>'
           f'<div class="table-scroll"><table><thead><tr><th>Source</th><th>Ce qu’elle apporte</th><th>Licence</th></tr></thead><tbody>{lignes}</tbody></table></div>'))

    # Page État des robots
    suivi = lire("lieux/_suivi.json", {}) or {}
    noms = {"redaction": "Rédaction (IA)", "climat": "Climat (Open-Meteo ERA5)", "securite": "Sécurité (Département d’État)",
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

    nb = len(lot) + (perso if a.limite else 0)
    print(f"Site généré dans site/ : accueil + {nombre(len(lot))} pages de villes ({perso} rédigées à la main), "
          f"{len(ctx['lieux'])} villes avec des lieux, en {(datetime.now() - t0).seconds} s.")


if __name__ == "__main__":
    main()
