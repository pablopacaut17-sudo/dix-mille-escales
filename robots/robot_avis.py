#!/usr/bin/env python3
"""
Robot Avis : publie les avis des lecteurs déposés sur GitHub (« issues » dont le titre commence par « Avis – »),
mais seulement ceux que le propriétaire du site a approuvés en leur ajoutant l'étiquette « approuvé ».
Les avis en attente sont listés dans le rapport du matin.

  python3 robots/robot_avis.py
"""
import json, os, re, urllib.request
import commun as c

DEPOT = os.environ.get("GITHUB_REPOSITORY", "")
JETON = os.environ.get("GITHUB_TOKEN", "")


def gh(chemin, methode="GET", donnees=None):
    req = urllib.request.Request("https://api.github.com/repos/" + DEPOT + chemin, method=methode,
                                 data=json.dumps(donnees).encode() if donnees is not None else None,
                                 headers={"Authorization": "Bearer " + JETON, "Accept": "application/vnd.github+json", "User-Agent": "dix-mille-escales"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, None


def champ(corps, nom):
    m = re.search(nom + r"\s*:\s*(.*?)(?:\n\s*\n[A-ZÉ][^\n]{0,40}:|\n\(|\Z)", corps, re.S)
    return m.group(1).strip() if m else ""


def main():
    if not (DEPOT and JETON):
        raise SystemExit("GITHUB_REPOSITORY et GITHUB_TOKEN nécessaires.")
    gh("/labels", "POST", {"name": "approuvé", "color": "2F7D6D", "description": "Avis de lecteur approuvé pour publication"})
    villes, attente, page = {}, 0, 1
    while page <= 10:
        st, issues = gh(f"/issues?state=all&per_page=100&page={page}")
        if st != 200 or not issues:
            break
        for i in issues:
            if "pull_request" in i or not i["title"].startswith("Avis –"):
                continue
            if not any(l["name"] == "approuvé" for l in i.get("labels", [])):
                attente += 1 if i["state"] == "open" else 0
                continue
            corps = i.get("body") or ""
            m = re.search(r"Note[^:]*:\s*([1-5])", corps)
            texte = champ(corps, r"Votre avis")
            ident, ville = champ(corps, "Identifiant").split("\n")[0], champ(corps, "Ville").split("\n")[0]
            if not (m and texte and ville):
                continue
            villes.setdefault(ville, {}).setdefault(ident or "ville", []).append(
                {"note": int(m.group(1)), "texte": texte[:1200], "date": champ(corps, r"Date de la visite[^:]*").split("\n")[0][:30],
                 "auteur": i["user"]["login"], "lien": i["html_url"]})
        page += 1
    c.ecrire("avis.json", {"date": c.horodatage(), "villes": villes})
    n = sum(len(l) for v in villes.values() for l in v.values())
    c.journal("avis", "ok", avis_publies=n, avis_en_attente=attente)
    print(f"Avis : {n} publiés, {attente} en attente d’approbation.")


if __name__ == "__main__":
    main()
