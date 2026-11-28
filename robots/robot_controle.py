#!/usr/bin/env python3
"""
Robot Contrôle : chaque matin, il relit les données des autres robots et repère, sans IA, ce qui ne peut pas être juste :
  - villes : coordonnées impossibles, population aberrante, doublons, pays inconnu, ville isolée au milieu d'un autre pays ;
  - climat : températures ou pluies impossibles, maximum sous le minimum, écarts jour/nuit trop grands (valeurs extrêmes
    prises pour des moyennes), normales calculées avec l'ancienne méthode ;
  - météo des 7 jours, taux de change (bornes et sauts d'un jour à l'autre), jours fériés (dates invalides, Noël
    ailleurs qu'au 25 décembre, année manquante) ;
  - encyclopédie : altitude, superficie, date de fondation impossibles, résumés vides ou coupés ;
  - lieux : lieux trop loin de leur ville, distance affichée fausse, nom vide, doublons, adresse web mal formée ;
  - histoires des lieux célèbres : biographies de personnes prises pour l'histoire d'un lieu, dates avant Jésus-Christ
    écrites comme des dates après, chiffres impossibles ;
  - liens cassés relevés par robot_liens, réponses ajoutées dans static/reponses.json ;
  - (avec --site) la boîte à questions du site en ligne, sur une liste de questions types (tests/questions.json).
Il écrit son rapport dans journal/controle.json (branche donnees-controle), lu par le chasseur d'erreurs.

  python3 robots/robot_controle.py                 # contrôle les données (dossier DME_DONNEES)
  python3 robots/robot_controle.py --demo          # jeu d'essai fabriqué : chaque contrôle doit trouver son erreur
  python3 robots/robot_controle.py --site https://pablopacaut17-sudo.github.io/dix-mille-escales/   # + questions types
"""
import argparse, gzip, json, math, os, re, sys, tempfile, time, unicodedata
from datetime import date, datetime
import commun as c

ALERTES_MAX = 60          # par contrôle, pour garder un rapport lisible
AN = date.today().year
# Bornes larges : une valeur hors de ces bornes est impossible, pas seulement rare
BORNES_CHANGE = {"USD": (0.7, 1.7), "GBP": (0.6, 1.1), "CHF": (0.6, 1.3), "JPY": (90, 260), "CAD": (1.0, 2.2),
                 "AUD": (1.1, 2.4), "CNY": (5, 11), "INR": (60, 140), "TRY": (10, 120), "BRL": (3, 9), "ZAR": (10, 30)}


def norm(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def km(a, b, c_, d):
    r = math.radians
    x = math.sin(r(c_ - a) / 2) ** 2 + math.cos(r(a)) * math.cos(r(c_)) * math.sin(r(d - b) / 2) ** 2
    return 12742 * math.asin(min(1, math.sqrt(x)))


class Rapport:
    def __init__(self):
        self.alertes, self.totaux, self.verifies = {}, {}, {}

    def alerte(self, controle, objet, detail):
        self.totaux[controle] = self.totaux.get(controle, 0) + 1
        l = self.alertes.setdefault(controle, [])
        if len(l) < ALERTES_MAX:
            l.append({"objet": objet, "detail": detail})

    def vu(self, controle, n=1):
        self.verifies[controle] = self.verifies.get(controle, 0) + n


def lire_json(chemin):
    try:
        with (gzip.open(chemin, "rt", encoding="utf-8") if chemin.endswith(".gz") else open(chemin, encoding="utf-8")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- villes
def controler_villes(R, V, P):
    slugs, ids, grille = {}, {}, {}
    for v in V:
        R.vu("villes")
        nom = f"{v.get('nom')} ({v.get('pays')})"
        lat, lon = v.get("lat"), v.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            R.alerte("villes", nom, f"coordonnées impossibles : {lat}, {lon}"); continue
        if abs(lat) < 0.01 and abs(lon) < 0.01:
            R.alerte("villes", nom, "coordonnées 0, 0 (point fictif dans le golfe de Guinée)")
        p = v.get("population")
        if not isinstance(p, (int, float)) or p <= 0 or p > 4e7:
            R.alerte("villes", nom, f"population impossible : {p}")
        if v.get("pays") not in P:
            R.alerte("villes", nom, f"pays inconnu : {v.get('pays')}")
        if not v.get("fuseau"):
            R.alerte("villes", nom, "fuseau horaire manquant")
        if not (v.get("nom") or "").strip():
            R.alerte("villes", str(v.get("id")), "nom vide")
        for cle, vu_ in (("slug", slugs), ("id", ids)):
            k = v.get(cle)
            if k in vu_:
                R.alerte("villes", nom, f"{cle} en double avec {vu_[k]}")
            vu_[k] = nom
        grille.setdefault((int(lat // 1), int(lon // 1)), []).append(v)
    # Doublons (même nom, même pays, à moins de 3 km) et villes isolées au milieu d'un autre pays
    for (gi, gj), l in grille.items():
        voisins = [w for di in (-1, 0, 1) for dj in (-1, 0, 1) for w in grille.get((gi + di, gj + dj), [])]
        for v in l:
            nv = norm(v["nom"])
            for w in voisins:
                if w["id"] < v["id"] and w["pays"] == v["pays"] and norm(w["nom"]) == nv and km(v["lat"], v["lon"], w["lat"], w["lon"]) < 3:
                    R.alerte("doublons", f"{v['nom']} ({v['pays']})", f"deux fiches à moins de 3 km : {v['slug']} et {w['slug']}")
            autres = [w for w in voisins if w["pays"] != v["pays"] and km(v["lat"], v["lon"], w["lat"], w["lon"]) < 40]
            if len(autres) >= 8 and v["population"] < 200000:
                larges = [w for di in range(-6, 7) for dj in range(-6, 7) for w in grille.get((gi + di, gj + dj), [])
                          if w["pays"] == v["pays"] and w["id"] != v["id"]]
                if not larges:
                    pays_voisin = max(set(w["pays"] for w in autres), key=lambda x: sum(1 for w in autres if w["pays"] == x))
                    R.alerte("mauvais_pays", f"{v['nom']} ({v['pays']})", f"aucune autre ville de ce pays à 600 km, mais {len(autres)} villes de {pays_voisin} à moins de 40 km : pays probablement faux")


# ---------------------------------------------------------------- climat et météo
def controler_climat(R, V, dossier):
    if not os.path.isdir(dossier):
        return
    ids = {str(v["id"]): v for v in V}
    anciens = 0
    for fn in os.listdir(dossier):
        if not fn.endswith(".json"):
            continue
        d = lire_json(os.path.join(dossier, fn))
        v = ids.get(fn[:-5])
        nom = f"{v['nom']} ({v['pays']})" if v else fn
        R.vu("climat")
        if not d or len(d.get("mois") or []) != 12:
            R.alerte("climat", nom, "fichier illisible ou incomplet (12 mois attendus)"); continue
        if d.get("source") == "NASA POWER" and d.get("methode") != "T2M±T2M_RANGE/2":
            anciens += 1  # masqué par build.py, recalculé par robot_climat
            continue
        m = d["mois"]
        ecarts = []
        for i, x in enumerate(m):
            tmax, tmin, pl = x.get("tmax"), x.get("tmin"), x.get("pluie_mm")
            if tmax is None or tmin is None:
                R.alerte("climat", nom, f"mois {i + 1} : température manquante"); break
            if tmax < tmin:
                R.alerte("climat", nom, f"mois {i + 1} : maximum {tmax} °C sous le minimum {tmin} °C"); break
            if tmax > 47 or tmin < -55:
                R.alerte("climat", nom, f"mois {i + 1} : moyenne impossible ({tmax} / {tmin} °C)"); break
            if pl is None or not 0 <= pl <= 2500:
                R.alerte("climat", nom, f"mois {i + 1} : pluie impossible ({pl} mm)"); break
            if x.get("soleil_h") is not None and not 0 <= x["soleil_h"] <= 24:
                R.alerte("climat", nom, f"mois {i + 1} : {x['soleil_h']} h de soleil par jour"); break
            ecarts.append(tmax - tmin)
        else:
            if sum(ecarts) / 12 > 20:
                R.alerte("climat", nom, f"écart jour/nuit moyen de {sum(ecarts) / 12:.0f} °C : valeurs extrêmes prises pour des moyennes ?")
        if not v:
            R.alerte("climat_orphelins", fn, "climat d'une ville qui n'est plus dans la liste")
    if anciens:
        R.alerte("climat_a_recalculer", f"{anciens} villes", "normales NASA POWER de l'ancienne méthode (masquées sur le site, recalcul en cours)")


def controler_meteo(R, dossier):
    if not os.path.isdir(dossier):
        return
    for fn in os.listdir(dossier):
        d = lire_json(os.path.join(dossier, fn))
        R.vu("meteo")
        for j in (d or {}).get("jours", []):
            mx, mn, pl = j.get("max"), j.get("min"), j.get("pluie_mm")
            if mx is None or mn is None or mx < mn or mx > 60 or mn < -75 or (pl is not None and not 0 <= pl <= 900):
                R.alerte("meteo", fn, f"{j.get('date')} : max {mx}, min {mn}, pluie {pl}"); break


# ---------------------------------------------------------------- change, jours fériés
def controler_change(R, d, precedent):
    if not d:
        R.alerte("change", "change.json", "fichier absent"); return
    taux = d.get("taux") or {}
    for k, t in taux.items():
        R.vu("change")
        if not isinstance(t, (int, float)) or t <= 0:
            R.alerte("change", k, f"taux impossible : {t}"); continue
        b = BORNES_CHANGE.get(k)
        if b and not b[0] <= t <= b[1]:
            R.alerte("change", k, f"1 € = {t} {k}, hors des bornes plausibles {b}")
        avant = (precedent or {}).get(k)
        if isinstance(avant, (int, float)) and avant > 0 and abs(t / avant - 1) > 0.15:
            R.alerte("change", k, f"saut de {100 * (t / avant - 1):+.0f} % depuis le dernier contrôle ({avant} → {t})")
    try:
        age = (c.maintenant() - datetime.fromisoformat(d["date"].replace("Z", "+00:00"))).days
        if age > 5:
            R.alerte("change", "change.json", f"taux vieux de {age} jours")
    except (KeyError, ValueError):
        pass


FIXES = [(re.compile(r"christmas day|^noël|^noel", re.I), "12-25"), (re.compile(r"new year'?s day|jour de l.an", re.I), "01-01")]


def controler_feries(R, dossier):
    if not os.path.isdir(dossier):
        return
    for fn in os.listdir(dossier):
        d = lire_json(os.path.join(dossier, fn)) or {}
        pays = fn.split(".")[0]
        jours = d.get("jours") or []
        R.vu("feries", len(jours))
        annees, vus = set(), set()
        for j in jours:
            try:
                dt = date.fromisoformat(j.get("date", ""))
            except ValueError:
                R.alerte("feries", pays, f"date invalide : {j.get('date')} ({j.get('nom')})"); continue
            annees.add(dt.year)
            if (j.get("date"), j.get("nom")) in vus:
                R.alerte("feries", pays, f"jour férié en double : {j.get('date')} {j.get('nom')}")
            vus.add((j.get("date"), j.get("nom")))
            for motif, md in FIXES:
                if motif.search(j.get("nom") or "") and dt.strftime("%m-%d") != md and "eve" not in (j.get("nom") or "").lower():
                    # Noël orthodoxe (7 janvier) et jours reportés (« observed ») : normaux
                    vrai = date(dt.year if md != "01-01" or dt.month == 1 else dt.year + 1, int(md[:2]), int(md[3:]))
                    reporte = vrai.weekday() >= 5 and abs((dt - vrai).days) <= 3
                    if md == "12-25" and dt.month == 1 or re.match(r"day after", j.get("nom") or "", re.I):
                        continue  # Noël arménien et orthodoxe (5-7 janvier), « lendemain du jour de l'an »  # tombé un week-end : jour chômé reporté
                    if not reporte and not re.search(r"orthodox|observed|substitute|\(", (j.get("nom") or "") + (j.get("nom_local") or ""), re.I) and dt.strftime("%m-%d") not in ("01-07", "12-26", "01-02"):
                        R.alerte("feries", pays, f"« {j.get('nom')} » le {j.get('date')} au lieu du {md[3:]}/{md[:2]}")
        if jours and AN not in annees and AN + 1 not in annees:
            R.alerte("feries", pays, f"aucun jour férié pour {AN} (années présentes : {sorted(annees)})")


# ---------------------------------------------------------------- encyclopédie
def texte_coupe(t):
    t = (t or "").strip()
    return len(t) > 40 and not re.search(r"[.!?»…)\]\"”]$", t)


def controler_encyclo(R, V, dossier):
    if not os.path.isdir(dossier):
        return
    ids = {str(v["id"]): v for v in V}
    for fn in os.listdir(dossier):
        d = lire_json(os.path.join(dossier, fn))
        if not d:
            continue
        v = ids.get(fn.split(".")[0])
        nom = f"{v['nom']} ({v['pays']})" if v else fn
        R.vu("encyclopedie")
        alt = d.get("altitude_m")
        if isinstance(alt, (int, float)) and not -430 <= alt <= 5100:
            R.alerte("encyclopedie", nom, f"altitude impossible pour une ville : {alt} m")
        sup = d.get("superficie_km2")
        if isinstance(sup, (int, float)) and not 0 < sup <= 3e5:
            R.alerte("encyclopedie", nom, f"superficie impossible : {sup} km²")
        fo = d.get("fondation")
        m = re.match(r"^-?\d{1,4}$", str(fo or ""))
        if m and int(fo) > AN:
            R.alerte("encyclopedie", nom, f"fondée dans le futur : {fo}")
        wp = d.get("wikipedia") or {}
        if wp and not (wp.get("resume") or "").strip():
            R.alerte("textes", nom, "résumé Wikipédia vide")
        elif texte_coupe(wp.get("resume")):
            R.alerte("textes", nom, f"résumé coupé : « …{wp['resume'].strip()[-60:]} »")
        for k, t in (wp.get("sections") or {}).items():
            if isinstance(t, str) and not t.strip():
                R.alerte("textes", nom, f"section « {k} » vide")


# ---------------------------------------------------------------- lieux
URL_OK = re.compile(r"^https?://[^\s/$.?#][^\s]*\.[^\s]+$", re.I)
DOMAINE = re.compile(r"^(?:www\.)?[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.[a-z]{2,}(?:[/?#]\S*)?$", re.I)  # complété par build.py


def controler_lieux(R, V, dossier, duree_max):
    if not os.path.isdir(dossier):
        return
    ids = {v["id"]: v for v in V}
    debut = time.monotonic()
    fichiers = []
    for d in sorted(os.listdir(dossier)):
        p = os.path.join(dossier, d)
        if os.path.isdir(p):
            fichiers += [os.path.join(p, f) for f in os.listdir(p) if f.endswith((".json.gz", ".json"))]
    # rotation : chaque jour une autre partie si la durée ne suffit pas pour tout relire
    dec = (date.today().toordinal() * 7919) % max(1, len(fichiers))
    fichiers = fichiers[dec:] + fichiers[:dec]
    for chemin in fichiers:
        if time.monotonic() - debut > duree_max * 60:
            R.alerte("lieux_non_relus", f"{len(fichiers) - R.verifies.get('fichiers_lieux', 0)} villes", "durée maximale atteinte, la suite demain")
            break
        d = lire_json(chemin)
        R.vu("fichiers_lieux")
        if not d:
            R.alerte("lieux", os.path.basename(chemin), "fichier illisible"); continue
        v = ids.get(d.get("ville"))
        if not v:
            continue
        nom = f"{v['nom']} ({v['pays']})"
        rayon, rayon_al = d.get("rayon_km") or 10, d.get("rayon_alentours_km") or 50
        vus = set()
        for f in d.get("lieux") or []:
            R.vu("lieux")
            if f.get("id") in vus:
                R.alerte("lieux", nom, f"lieu en double : {f.get('nom')} ({f.get('id')})")
            vus.add(f.get("id"))
            lat, lon = f.get("lat"), f.get("lon")
            if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                R.alerte("lieux", nom, f"« {f.get('nom')} » sans coordonnées"); continue
            dist = km(v["lat"], v["lon"], lat, lon)
            # golfes, sentiers, parcs : leur point est souvent loin du centre ; on ne signale que les écarts nets
            limite = rayon_al * 3 if f.get("rubrique") == "alentours" else rayon * 2 + 10
            if dist > limite:
                R.alerte("lieux_trop_loin", nom, f"« {f.get('nom')} » à {dist:.0f} km du centre (rayon {rayon if f.get('rubrique') != 'alentours' else rayon_al} km)")
            dk = f.get("distance_km")
            if isinstance(dk, (int, float)) and abs(dk - dist) > max(1.5, 0.25 * dist):
                R.alerte("lieux_distance", nom, f"« {f.get('nom')} » : distance affichée {dk} km, réelle {dist:.1f} km")
            if not (f.get("nom") or "").strip():
                R.alerte("lieux", nom, f"lieu sans nom ({f.get('id')})")
            site = (f.get("site") or "").strip()
            if site and not URL_OK.match(site) and not DOMAINE.match(site):
                R.alerte("liens_mal_formes", nom, f"« {f.get('nom')} » : adresse web « {site[:80]} »")


# ---------------------------------------------------------------- histoires des lieux célèbres
BIO_PERSONNE = re.compile(r"^[^.]{0,250}?(,|\)) (né|née|nés|nées) (le |à |en |vers |dans |au |\d)")
BIO_LIEU = re.compile(r"^(musée|maison|statue|monument|mémorial|place|rue|avenue|tombe|tombeau|mausolée|église|chapelle|parc|jardin|"
                      r"square|pont|gare|école|lycée|collège|université|stade|théâtre|bibliothèque|fontaine|buste|cimetière|villa|"
                      r"château|palais|hôtel|centre|institut|salle)\b|museum", re.I)
AV_JC = re.compile(r"(\d{1,4})\s*(?:av\.?\s*J\.?-?C\.?|avant J(?:ésus)?\.?-?C(?:hrist)?\.?|av\. notre ère|avant notre ère)", re.I)
# mêmes bornes que build.py (BORNES) : une valeur hors bornes y est déjà masquée, on la signale pour corriger la source
BORNES_LIEUX = {"hauteur": (0.5, 900), "longueur": (0.05, 25_000_000), "largeur": (0.05, 2_000_000), "superficie": (1, 1e12),
                "altitude": (-450, 8849), "visiteurs_an": (1, 120_000_000), "capacite": (1, 400_000), "frequentation": (1, 2_000_000_000)}


def controler_histoires(R, dossier):
    if not os.path.isdir(dossier):
        return
    for fn in os.listdir(dossier):
        if not fn.endswith(".json") or fn.startswith("_"):
            continue
        for q, h in (lire_json(os.path.join(dossier, fn)) or {}).items():
            if not isinstance(h, dict):
                continue
            R.vu("histoires")
            t, r, f = h.get("t") or q, h.get("r") or "", h.get("f") or {}
            if BIO_PERSONNE.search(r[:300]) and not BIO_LIEU.search(t):
                R.alerte("histoires_biographies", f"{t} ({q})", "biographie d'une personne prise pour l'histoire d'un lieu (écartée par build.py)")
                continue
            for k, b in BORNES_LIEUX.items():
                x = f.get(k)
                if isinstance(x, (int, float)) and not isinstance(x, bool) and not b[0] <= x <= b[1]:
                    R.alerte("histoires_chiffres", f"{t} ({q})", f"{k} impossible : {x}")
            av = {int(n) for n in AV_JC.findall(r)}
            for k in ("creation", "ouverture", "debut"):
                x = f.get(k)
                if isinstance(x, int) and x > 0 and x in av:
                    R.alerte("histoires_dates", f"{t} ({q})", f"{k} = {x} alors que le texte dit « {x} av. J.-C. » (signe moins rétabli par build.py)")
                elif isinstance(x, int) and x > AN:
                    R.alerte("histoires_dates", f"{t} ({q})", f"{k} dans le futur : {x}")
            if texte_coupe(r):
                R.alerte("textes", f"{t} ({q})", f"histoire coupée : « …{r.strip()[-60:]} »")


# ---------------------------------------------------------------- liens, réponses ajoutées
def controler_liens(R, d):
    """liens.json.gz de robot_liens : {adresse: [date du test, code, échecs nets consécutifs]} ; 2 échecs = mort, masqué."""
    if not isinstance(d, dict):
        return
    R.vu("liens", len(d))
    morts = [(u, e) for u, e in d.items() if isinstance(e, list) and len(e) > 2 and e[2] >= 2]
    if morts:
        R.alerte("liens_casses", f"{len(morts)} liens", f"liens morts masqués sur le site (ex. {morts[0][0][:90]}, code {morts[0][1][1]})")


def controler_reponses(R, chemin):
    l = lire_json(chemin)
    if l is None:
        R.alerte("reponses", "static/reponses.json", "fichier illisible"); return
    vus = set()
    for x in l if isinstance(l, list) else []:
        R.vu("reponses")
        q = norm(x.get("q"))
        if not q or not (x.get("r") or "").strip():
            R.alerte("reponses", x.get("q") or "?", "question ou réponse vide")
        if (q, x.get("slug")) in vus:
            R.alerte("reponses", x.get("q"), "réponse en double")
        vus.add((q, x.get("slug")))
        if texte_coupe(x.get("r")):
            R.alerte("reponses", x.get("q"), "réponse coupée")
        if re.search(r"\b(19|20)\d\d\b", x.get("r") or "") is None and re.search(r"\bprix|co[uû]t|€|tarif", x.get("r") or "", re.I) and not x.get("date"):
            R.alerte("reponses", x.get("q"), "prix sans date de vérification")


# ---------------------------------------------------------------- boîte à questions (site en ligne)
def controler_questions(R, site, fichier):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        R.alerte("questions", "Playwright", "non installé : questions types non posées"); return
    tests = lire_json(fichier) or []
    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page(viewport={"width": 390, "height": 844})
        try:
            page.goto(site, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            R.alerte("questions", site, f"site injoignable : {e}"[:200]); nav.close(); return
        for t in tests:
            R.vu("questions")
            try:
                page.fill(".q-input", t["q"]); page.press(".q-input", "Enter")
                txt = ""
                for _ in range(40):
                    page.wait_for_timeout(400)
                    txt = " ".join(page.inner_text(".q-rep").split())
                    if txt and "Je cherche" not in txt:
                        break
            except Exception as e:
                R.alerte("questions", t["q"], f"la boîte ne répond pas : {e}"[:200]); continue
            manque = [x for x in t.get("contient", []) if not any(o in txt for o in x.split("|"))]
            interdit = [x for x in t.get("interdit", []) if x in txt]
            if manque:
                R.alerte("questions", t["q"], f"réponse sans « {' / '.join(manque)} » : {txt[:160]}")
            elif interdit:
                R.alerte("questions", t["q"], f"réponse à côté (contient « {' / '.join(interdit)} ») : {txt[:160]}")
        nav.close()


# ---------------------------------------------------------------- démo
def jeu_demo(dossier):
    """Petit jeu de données avec une erreur de chaque sorte (et des valeurs justes à ne pas signaler)."""
    def w(rel, d):
        p = os.path.join(dossier, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
    V = [{"id": 1, "nom": "Lisbonne", "pays": "PT", "lat": 38.72, "lon": -9.14, "population": 500000, "fuseau": "Europe/Lisbon", "slug": "lisbonne-pt"},
         {"id": 2, "nom": "Lisbonne", "pays": "PT", "lat": 38.73, "lon": -9.15, "population": 1000, "fuseau": "Europe/Lisbon", "slug": "lisbonne-2-pt"},
         {"id": 3, "nom": "Nulle", "pays": "XX", "lat": 0, "lon": 0, "population": -5, "fuseau": "", "slug": "nulle"}]
    mois_ok = [{"tmax": 15 + i, "tmin": 8 + i, "pluie_mm": 50, "jours_pluie": 8, "soleil_h": 6} for i in range(12)]
    mois_ext = [{"tmax": 39, "tmin": 3, "pluie_mm": 50, "jours_pluie": None, "soleil_h": None} for i in range(12)]
    w("climat/1.json", {"source": "openmeteo", "mois": mois_ok})
    w("climat/2.json", {"source": "NASA POWER", "methode": "T2M±T2M_RANGE/2", "mois": mois_ext})
    w("climat/3.json", {"source": "NASA POWER", "mois": mois_ok})
    w("change.json", {"date": c.horodatage(), "taux": {"USD": 1.09, "GBP": 0.84, "JPY": 1748.1}})
    w("feries/PT.json", {"jours": [{"date": f"{AN}-12-25", "nom": "Christmas Day"}, {"date": f"{AN}-12-24", "nom": "Christmas Day"}, {"date": f"{AN}-02-30", "nom": "Carnaval"}]})
    w("encyclo/1.json", {"altitude_m": 9000, "superficie_km2": 100, "wikipedia": {"resume": "Lisbonne est la capitale du Portugal et la plus grande ville du pays, située sur l", "sections": {}}})
    w("lieux/0/1.json", {"ville": 1, "rayon_km": 5, "lieux": [
        {"id": "a", "nom": "Tour de Belém", "rubrique": "voir", "lat": 38.69, "lon": -9.22, "distance_km": 7.4, "site": "https://www.museusemonumentos.pt"},
        {"id": "b", "nom": "Tour Eiffel", "rubrique": "voir", "lat": 48.86, "lon": 2.29, "distance_km": 1.2, "site": "www belém"}]})
    w("histoires/h00.json", {"Q1001": {"t": "Mohandas Karamchand Gandhi", "r": "Mohandas Karamchand Gandhi, né à Porbandar le 2 octobre 1869, est un avocat indien.", "f": {"hauteur": 1.64}},
                             "Q1": {"t": "Pyramide de Khéops", "r": "La pyramide de Khéops, construite vers 2560 av. J.-C., est la plus grande des pyramides de Gizeh.", "f": {"hauteur": 138.5, "creation": 2560}},
                             "Q2": {"t": "Tour Eiffel", "r": "La tour Eiffel est une tour de fer puddlé de 330 m de hauteur.", "f": {"hauteur": 330, "creation": 1889}}})
    return V, {"PT": {}}


ATTENDU_DEMO = {"villes", "doublons", "climat", "climat_a_recalculer", "change", "feries", "encyclopedie", "textes", "lieux_trop_loin",
                "lieux_distance", "liens_mal_formes", "histoires_biographies", "histoires_dates"}


# ---------------------------------------------------------------- principal
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    p.add_argument("--site", help="adresse du site en ligne : pose aussi les questions types (Playwright)")
    p.add_argument("--duree-max", type=float, default=25, help="minutes consacrées à la relecture des lieux")
    a = p.parse_args()
    R = Rapport()
    if a.demo:
        tmp = tempfile.mkdtemp(prefix="controle-demo-")
        V, P = jeu_demo(tmp)
        base = tmp
    else:
        V, P = c.villes(), c.lire("pays.json", {}) or {}
        base = c.DATA
    precedent = (c.lire("journal/controle.json") or {}).get("taux_change") if not a.demo else None
    change = lire_json(os.path.join(base, "change.json"))
    etapes = [("villes", lambda: controler_villes(R, V, P)),
              ("climat", lambda: controler_climat(R, V, os.path.join(base, "climat"))),
              ("meteo", lambda: controler_meteo(R, os.path.join(base, "meteo"))),
              ("change", lambda: controler_change(R, change, precedent)),
              ("feries", lambda: controler_feries(R, os.path.join(base, "feries"))),
              ("encyclopedie", lambda: controler_encyclo(R, V, os.path.join(base, "encyclo"))),
              ("histoires", lambda: controler_histoires(R, os.path.join(base, "histoires"))),
              ("liens", lambda: controler_liens(R, lire_json(os.path.join(base, "liens.json.gz")))),
              ("reponses", lambda: controler_reponses(R, os.path.join(c.RACINE, "static", "reponses.json"))),
              ("lieux", lambda: controler_lieux(R, V, os.path.join(base, "lieux"), a.duree_max))]
    if a.site:
        etapes.append(("questions", lambda: controler_questions(R, a.site, os.path.join(c.RACINE, "tests", "questions.json"))))
    for nom, f in etapes:
        t0 = time.monotonic()
        try:
            f()
        except Exception as e:  # un contrôle cassé ne doit pas empêcher les autres
            R.alerte("controle_en_panne", nom, f"{type(e).__name__} : {e}"[:200])
        print(f"{nom} : {R.verifies.get(nom, 0)} éléments relus en {time.monotonic() - t0:.0f} s")
    total = sum(R.totaux.values())
    print(f"\n{total} alertes :")
    for k, n in sorted(R.totaux.items(), key=lambda x: -x[1]):
        print(f"  {k} : {n}  (ex. {R.alertes[k][0]['objet']} : {R.alertes[k][0]['detail']})")
    if a.demo:
        manquent = ATTENDU_DEMO - set(R.totaux)
        faux = [x for x in R.alertes.get("histoires_dates", []) + R.alertes.get("lieux_trop_loin", []) if "Eiffel" in x["objet"] and "Tour Eiffel (Q2)" == x["objet"]]
        if manquent or faux or "controle_en_panne" in R.totaux:
            print(f"\nDÉMO : contrôles qui n'ont pas trouvé leur erreur : {sorted(manquent)} ; fausses alertes : {faux}")
            return 1
        print("\nDÉMO : chaque contrôle a trouvé son erreur.")
        return 0
    c.journal("controle", "ok" if "controle_en_panne" not in R.totaux else "partiel", alertes_total=total, totaux=R.totaux,
              verifies=R.verifies, alertes=R.alertes, taux_change=(change or {}).get("taux", {}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
