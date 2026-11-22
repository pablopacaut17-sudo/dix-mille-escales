#!/usr/bin/env python3
"""
Robot Surveillance : chaque matin, il vérifie le travail des autres robots et le site, corrige ce qui peut l'être
et publie un rapport (une « issue » GitHub, qui arrive par e-mail ou notification au propriétaire du dépôt).

Vérifications :
  1. le passage de la nuit a bien eu lieu, n'est pas bloqué, et chaque groupe de robots a réussi ;
  2. chaque robot a travaillé récemment, sans échec massif (d'après son journal) ;
  3. les branches de données existent ;
  4. le site répond, le compteur ne s'est pas effondré, le site reste sous la limite de 1 Go.

Corrections automatiques (une seule relance par jour, pour ne jamais tourner en boucle) :
  - groupe de robots en échec ou en retard  -> relance de ce groupe seulement ;
  - passage bloqué depuis plus de 7 h        -> annulation puis relance complète ;
  - aucun passage depuis plus de 26 h         -> relance complète ;
  - site non publié ou injoignable            -> nouvelle publication.
Ce qu'il ne peut pas corriger seul (source qui change de format, site trop lourd, données effondrées) est signalé
en tête du rapport, pour une intervention humaine.

  python3 robots/robot_surveillance.py           # vérifie, corrige, publie le rapport
  python3 robots/robot_surveillance.py --essai   # vérifie seulement, sans rien relancer ni publier
"""
import argparse, json, os, sys, urllib.request
from datetime import datetime, timedelta, timezone
import commun as c

DEPOT = os.environ.get("GITHUB_REPOSITORY", "")
JETON = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")
API = "https://api.github.com/repos/" + DEPOT
FICHIER_ROBOTS = "robots.yml"
GROUPES = {"villes": "villes", "base": "base", "encyclopedie": "encyclopedie", "lieux": "lieux", "guides": "guides", "climat": "climat", "histoires": "histoires", "redaction": "redaction", "publier": "publier"}
# robot -> (groupe, âge maximal en heures, nom lisible)
ATTENDUS = {
    "change": ("base", 30, "Change"), "feries": ("base", 30, "Jours fériés"), "securite": ("base", 30, "Sécurité"),
    "formalites": ("base", 30, "Formalités"), "cout": ("base", 30, "Coût de la vie"), "meteo": ("base", 30, "Météo"),
    "climat": ("climat", 30, "Climat"), "encyclopedie": ("encyclopedie", 30, "Encyclopédie"),
    "lieux_0": ("lieux", 30, "Lieux, robot 1"), "lieux_1": ("lieux", 30, "Lieux, robot 2"), "lieux_2": ("lieux", 30, "Lieux, robot 3"), "lieux_3": ("lieux", 30, "Lieux, robot 4"),
    "guides": ("guides", 30, "Guides Wikivoyage"), "aeroports": ("base", 24 * 35, "Aéroports"), "urgences": ("base", 24 * 35, "Numéros d’urgence"), "conseils": ("base", 30, "Conseils aux voyageurs (Canada)"), "pratique": ("base", 24 * 35, "Prises et conduite (Wikidata)"), "langues": ("base", 24 * 35, "Mots utiles (Wikivoyage)"), "histoires": ("histoires", 30, "Histoire des lieux (Wikipédia)"), "avis": ("base", 30, "Avis des lecteurs"),
}
BRANCHES = ["donnees-base", "donnees-encyclopedie", "donnees-lieux-0", "donnees-lieux-1", "donnees-lieux-2", "donnees-lieux-3", "donnees-guides", "donnees-climat"]
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def gh(chemin, methode="GET", donnees=None):
    req = urllib.request.Request(API + chemin if chemin.startswith("/") else chemin, method=methode,
                                 data=json.dumps(donnees).encode() if donnees is not None else None,
                                 headers={"Authorization": "Bearer " + JETON, "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "dix-mille-escales-surveillance"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
            return r.status, (json.loads(b) if b else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return 0, str(e)


def date_iso(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def jour_fr(d):
    return f"{d.day} {MOIS[d.month - 1]} {d.year}"


def nombre(n):
    return f"{n:,}".replace(",", "\u202f")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--essai", action="store_true", help="vérifier seulement : ne rien relancer, ne rien publier")
    a = p.parse_args()
    maintenant = c.maintenant()
    problemes, corriges, infos, a_relancer = [], [], [], set()
    journal = c.lire("journal/surveillance.json", {}) or {}
    historique = journal.get("historique", [])

    # 1. Passages des robots
    st, rep = gh(f"/actions/workflows/{FICHIER_ROBOTS}/runs?per_page=20")
    runs = [r for r in (rep or {}).get("workflow_runs", []) if r["event"] != "push"] if st == 200 else []
    if st != 200:
        problemes.append(f"Impossible de lire les passages des robots (erreur {st}).")
    bloques = [r for r in runs if r["status"] in ("in_progress", "queued") and maintenant - date_iso(r["run_started_at"] or r["created_at"]) > timedelta(hours=7)]
    for r in bloques:
        problemes.append(f"Passage du {date_iso(r['created_at']):%d/%m à %H:%M} UTC bloqué depuis plus de 7 h.")
        if not a.essai and gh(f"/actions/runs/{r['id']}/cancel", "POST")[0] == 202:
            corriges.append("Passage bloqué annulé.")
        a_relancer.update(["tout"])
    recents = [r for r in runs if maintenant - date_iso(r["created_at"]) < timedelta(hours=26)]
    # Les passages annulés volontairement (avant d'avoir travaillé) ne comptent pas
    termines = [r for r in recents if r["status"] == "completed" and r["conclusion"] != "cancelled"]
    if not recents:
        problemes.append("Aucun passage des robots depuis plus de 26 h.")
        a_relancer.add("tout")
    elif termines:
        dernier = termines[0]
        st, jobs = gh(f"/actions/runs/{dernier['id']}/jobs?per_page=50")
        for j in (jobs or {}).get("jobs", []) if st == 200 else []:
            groupe = j["name"].split(" ")[0]
            if j["conclusion"] in ("failure", "timed_out", "cancelled") and groupe in GROUPES:
                problemes.append(f"Le groupe « {j['name']} » a échoué ({j['conclusion']}) lors du passage du {date_iso(dernier['created_at']):%d/%m}.")
                a_relancer.add(GROUPES[groupe])
            for s in j.get("steps", []):
                if s["name"].startswith("Enregistrer") and s["conclusion"] == "failure":
                    problemes.append(f"« {j['name']} » n’a pas pu enregistrer ses données.")
                    a_relancer.add(GROUPES.get(groupe, "tout"))
        infos.append(f"Dernier passage terminé : {date_iso(dernier['created_at']):%d/%m à %H:%M} UTC, résultat : {dernier['conclusion']}.")
    else:
        infos.append("Un passage est en cours.")

    # 2. Journaux des robots
    en_cours = any(r["status"] != "completed" for r in recents)
    for robot, (groupe, age_max, nom) in ATTENDUS.items():
        j = c.lire(f"journal/{robot}.json")
        if not j:
            if not en_cours:
                problemes.append(f"{nom} : aucun passage enregistré.")
                a_relancer.add(groupe)
            continue
        age = (maintenant - date_iso(j["dernier_passage"])).total_seconds() / 3600
        detail = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in j.items() if k not in ("etat", "dernier_passage", "mode"))
        if age > age_max and not en_cours:
            problemes.append(f"{nom} : dernier passage il y a {age:.0f} h.")
            a_relancer.add(groupe)
        elif j.get("etat") in ("echec",):
            problemes.append(f"{nom} : en échec{' (' + detail + ')' if detail else ''}. Les données précédentes sont conservées ; "
                             f"si l’échec se répète plusieurs jours, la source a sans doute changé et le robot doit être adapté.")
        elif robot.startswith("lieux") and j.get("regions_traitees", j.get("villes_traitees", 1)) == 0:
            problemes.append(f"{nom} : aucune ville traitée cette nuit (serveur OpenStreetMap saturé ?).")
            a_relancer.add("lieux")
        else:
            infos.append(f"{nom} : {j.get('etat')} ({detail}).")
    red = c.lire("journal/redaction.json")
    if red and red.get("etat") == "désactivé":
        infos.append("Rédaction : inactive (pas de clé API Claude), c’est normal.")

    # 3. Branches de données
    st, br = gh("/branches?per_page=100")
    noms = {b["name"] for b in br} if st == 200 else set()
    for b in BRANCHES:
        if st == 200 and b not in noms and not en_cours:
            problemes.append(f"La branche de données « {b} » est absente.")

    # 4. Site
    st, pages = gh("/pages")
    url = (pages or {}).get("html_url") if st == 200 else None
    cpt = None
    if url:
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                ok = r.status == 200
            with urllib.request.urlopen(url.rstrip("/") + "/static/compteur.json", timeout=30) as r:
                cpt = json.load(r)
            infos.append(f"Site en ligne : {url}")
        except Exception as e:
            problemes.append(f"Le site ne répond pas ({e}).")
            a_relancer.add("publier")
    if cpt:
        inf = cpt.get("informations", 0)
        precedent = historique[-1]["informations"] if historique else None
        infos.append(f"Compteur : {nombre(inf)} informations" + (f" ({'+' if inf >= precedent else ''}{nombre(inf - precedent)} depuis le dernier rapport)." if precedent else "."))
        if precedent and inf < precedent * 0.9:
            problemes.append(f"Le compteur a baissé de plus de 10 % ({nombre(precedent)} → {nombre(inf)}) : des données ont peut-être été perdues. Intervention humaine conseillée.")
        taille = cpt.get("taille_site_mo")
        if taille:
            infos.append(f"Taille du site : {taille} Mo sur 1 024 Mo.")
            if taille > 950:
                problemes.append(f"Le site approche la limite de 1 Go de GitHub Pages ({taille} Mo). Intervention humaine nécessaire.")
        historique.append({"date": maintenant.strftime("%Y-%m-%d"), "informations": inf, "villes_enrichies": cpt.get("villes_enrichies"),
                           "lieux": cpt.get("lieux")})
        historique = historique[-90:]

    # 5. Signalements des lecteurs (à traiter par un humain)
    signalements = []
    st, ouverts = gh("/issues?state=open&per_page=100")
    for i in ouverts if st == 200 else []:
        if i.get("title", "").startswith("Signalement") and "pull_request" not in i:
            signalements.append(f"[{i['title']}]({i['html_url']})")
        elif i.get("title", "").startswith("Avis –") and "pull_request" not in i and not any(l["name"] == "approuvé" for l in i.get("labels", [])):
            signalements.append(f"À approuver (ajoutez l’étiquette « approuvé » pour publier, ou fermez pour refuser) : [{i['title']}]({i['html_url']})")
    if signalements:
        infos.append(f"{len(signalements)} signalement(s) d’erreur de lecteurs en attente (voir plus bas).")

    # 6. Corrections : une seule relance par jour
    aujourdhui = maintenant.strftime("%Y-%m-%d")
    deja = journal.get("derniere_relance") == aujourdhui
    if a_relancer and not deja and not a.essai and not en_cours:
        groupes = "" if "tout" in a_relancer else ",".join(sorted(a_relancer | ({"publier"} if a_relancer - {"publier"} else set())))
        st, _ = gh(f"/actions/workflows/{FICHIER_ROBOTS}/dispatches", "POST", {"ref": "main", "inputs": {"groupes": groupes}})
        if st == 204:
            corriges.append("Relance lancée pour : " + (groupes.replace(",", ", ") if groupes else "tous les robots") + ".")
            journal["derniere_relance"] = aujourdhui
        else:
            problemes.append(f"La relance automatique a échoué (erreur {st}).")
    elif a_relancer and deja:
        problemes.append("Une relance a déjà été tentée aujourd’hui : pas de nouvelle relance automatique, pour éviter de tourner en boucle.")
    elif a_relancer and en_cours:
        infos.append("Un passage est en cours : la relance attendra le prochain rapport.")

    # 7. Rapport
    restants = len(problemes)
    titre = (f"Rapport du matin – {jour_fr(maintenant)} : " +
             ("tout va bien" if not restants else f"{restants} problème{'s' if restants > 1 else ''}" + (f", {len(corriges)} correction{'s' if len(corriges) > 1 else ''} lancée{'s' if len(corriges) > 1 else ''}" if corriges else "")))
    corps = [f"## {'Tout va bien' if not restants else 'À regarder'}", ""]
    corps += [f"- {x}" for x in problemes] or ["Aucun problème détecté."]
    if corriges:
        corps += ["", "## Corrections automatiques", ""] + [f"- {x}" for x in corriges]
    corps += ["", "## Détails", ""] + [f"- {x}" for x in infos]
    if signalements:
        corps += ["", "## Signalements d’erreurs à vérifier", ""] + [f"- {x}" for x in signalements[:30]]
    if len(historique) > 1:
        corps += ["", "## Progression du compteur", "", "| Date | Informations |", "|---|---|"]
        corps += [f"| {h['date']} | {nombre(h['informations'])} |" for h in historique[-7:]]
    corps += ["", "_Rapport rédigé automatiquement par le robot Surveillance._"]
    texte = "\n".join(corps)
    print(titre + "\n\n" + texte)
    if not a.essai:
        # Ferme les rapports précédents restés ouverts, publie le nouveau
        st, ouverts = gh("/issues?state=open&per_page=50")
        for i in ouverts if st == 200 else []:
            if i.get("title", "").startswith("Rapport du matin") and "pull_request" not in i:
                gh(f"/issues/{i['number']}", "PATCH", {"state": "closed"})
        st, _ = gh("/issues", "POST", {"title": titre, "body": texte})
        if st != 201:
            print(f"Rapport non publié (erreur {st}).", file=sys.stderr)
        journal.update(dernier_rapport=c.horodatage(), problemes=restants, historique=historique)
        c.ecrire("journal/surveillance.json", journal)
    c.journal("surveillance_etat", "ok" if not restants else "alerte", problemes=restants, corrections=len(corriges))


if __name__ == "__main__":
    main()
