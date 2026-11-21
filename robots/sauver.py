#!/usr/bin/env python3
"""
Enregistre les données d'un groupe de robots dans sa branche « donnees-<groupe> », sans historique :
la branche ne contient que la dernière version, le dépôt ne grossit donc pas au fil des nuits.

  python3 robots/sauver.py --branche donnees-base --chemins meteo climat change.json journal/meteo.json
  python3 robots/sauver.py --principal      # enregistre data/villes.json et data/pays.json dans le dépôt principal
"""
import argparse, os, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DONNEES = os.environ.get("DME_DONNEES") or os.path.join(RACINE, "donnees")
NOM, MAIL = "robot-dix-mille-escales", "robot-dix-mille-escales@users.noreply.github.com"


def git(*args, cwd=RACINE, ok=False):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode and not ok:
        print(r.stdout, r.stderr, file=sys.stderr)
    return r.returncode


def url_depot():
    jeton, depot = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if jeton and depot:
        return f"https://x-access-token:{jeton}@github.com/{depot}.git"
    return subprocess.run(["git", "-C", RACINE, "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()


def principal():
    git("config", "user.name", NOM); git("config", "user.email", MAIL)
    git("add", "-A", "data")
    if git("diff", "--cached", "--quiet", ok=True) == 0:
        print("Dépôt principal : rien de nouveau.")
        return 0
    git("commit", "-m", f"Liste des villes mise à jour le {datetime.now(timezone.utc):%Y-%m-%d}")
    for _ in range(3):
        if git("pull", "--rebase") == 0 and git("push") == 0:
            print("Dépôt principal enregistré.")
            return 0
    return 1


def branche(nom, chemins):
    with tempfile.TemporaryDirectory() as d:
        copies = 0
        for c in chemins:
            s = os.path.join(DONNEES, c)
            if os.path.isdir(s):
                shutil.copytree(s, os.path.join(d, c), dirs_exist_ok=True); copies += 1
            elif os.path.isfile(s):
                os.makedirs(os.path.dirname(os.path.join(d, c)), exist_ok=True)
                shutil.copy2(s, os.path.join(d, c)); copies += 1
        if not copies:
            print(f"{nom} : aucune donnée à enregistrer.")
            return 0
        git("init", "--quiet", cwd=d); git("checkout", "--quiet", "-b", nom, cwd=d)
        git("config", "user.name", NOM, cwd=d); git("config", "user.email", MAIL, cwd=d)
        git("add", "-A", cwd=d)
        git("commit", "--quiet", "-m", f"Données du {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", cwd=d)
        for _ in range(3):
            if git("push", "--quiet", "--force", url_depot(), f"{nom}:{nom}", cwd=d) == 0:
                print(f"{nom} : données enregistrées.")
                return 0
    print(f"{nom} : enregistrement impossible.", file=sys.stderr)
    return 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--branche")
    p.add_argument("--chemins", nargs="*", default=[])
    p.add_argument("--principal", action="store_true")
    a = p.parse_args()
    if a.principal:
        return principal()
    return branche(a.branche, a.chemins)


if __name__ == "__main__":
    sys.exit(main())
