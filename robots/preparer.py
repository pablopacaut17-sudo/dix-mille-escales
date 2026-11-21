#!/usr/bin/env python3
"""
Prépare le dossier des données des robots (variable DME_DONNEES, par défaut ./donnees).

Les données collectées ne sont plus rangées dans l'historique du dépôt principal (il grossirait de plusieurs Go) :
chaque groupe de robots enregistre les siennes dans une branche « donnees-… » qui ne garde que la dernière version.
Ce script réunit toutes ces branches dans un seul dossier, pour que les robots et le générateur du site les lisent.
Au tout premier passage, il reprend les anciennes données rangées dans data/.

  python3 robots/preparer.py                 # réunir les données
  python3 robots/preparer.py --nettoyer-main # en plus, retirer de data/ les anciennes données déjà migrées
"""
import argparse, os, shutil, subprocess, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.environ.get("DME_DONNEES") or os.path.join(RACINE, "donnees")
ANCIENNES = ("lieux", "meteo", "feries", "encyclo", "climat", "redaction", "change.json", "securite.json",
             "formalites.json", "cout.json", "journal.json")


def url_depot():
    jeton, depot = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if jeton and depot:
        return f"https://x-access-token:{jeton}@github.com/{depot}.git"
    r = subprocess.run(["git", "-C", RACINE, "remote", "get-url", "origin"], capture_output=True, text=True)
    return r.stdout.strip()


def branches(url):
    r = subprocess.run(["git", "ls-remote", "--heads", url, "donnees-*"], capture_output=True, text=True)
    return [l.split("refs/heads/")[1] for l in r.stdout.splitlines() if "refs/heads/" in l]


def fusionner(src, dst):
    for racine, dossiers, fichiers in os.walk(src):
        dossiers[:] = [d for d in dossiers if d != ".git"]
        cible = os.path.join(dst, os.path.relpath(racine, src))
        os.makedirs(cible, exist_ok=True)
        for f in fichiers:
            shutil.copy2(os.path.join(racine, f), os.path.join(cible, f))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--nettoyer-main", action="store_true")
    a = p.parse_args()
    os.makedirs(DEST, exist_ok=True)
    url = url_depot()
    liste = branches(url)
    tmp = os.path.join(RACINE, ".tmp-donnees")
    for b in liste:
        d = os.path.join(tmp, b)
        shutil.rmtree(d, ignore_errors=True)
        r = subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--single-branch", "--branch", b, url, d])
        if r.returncode == 0:
            fusionner(d, DEST)
            print(f"Données de « {b} » récupérées.")
    shutil.rmtree(tmp, ignore_errors=True)
    data = os.path.join(RACINE, "data")
    anciennes = [x for x in ANCIENNES if os.path.exists(os.path.join(data, x))]
    if not liste and anciennes:
        for x in anciennes:  # premier passage : reprise des données rangées dans data/
            s = os.path.join(data, x)
            if os.path.isdir(s):
                fusionner(s, os.path.join(DEST, x))
            else:
                shutil.copy2(s, os.path.join(DEST, x))
        print("Anciennes données de data/ reprises : " + ", ".join(anciennes))
    if a.nettoyer_main and liste and anciennes:
        subprocess.run(["git", "-C", RACINE, "rm", "-r", "--quiet", "--cached", *[os.path.join("data", x) for x in anciennes]])
        for x in anciennes:
            s = os.path.join(data, x)
            shutil.rmtree(s) if os.path.isdir(s) else os.remove(s)
        print("Anciennes données retirées du dépôt principal (elles sont dans les branches donnees-…).")
    print(f"Dossier des données prêt : {DEST}")


if __name__ == "__main__":
    sys.exit(main())
