#!/usr/bin/env python3
"""Enregistre dans le dépôt les données collectées par les robots (appelé plusieurs fois pendant un passage,
pour ne jamais perdre le travail déjà fait si le passage est interrompu)."""
import subprocess, sys
from datetime import datetime, timezone


def git(*args, ok=False):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if r.returncode and not ok:
        print(r.stdout, r.stderr, file=sys.stderr)
    return r.returncode


git("config", "user.name", "robot-dix-mille-escales")
git("config", "user.email", "robot-dix-mille-escales@users.noreply.github.com")
git("add", "data")
if git("diff", "--cached", "--quiet", ok=True) == 0:
    print("Aucune donnée nouvelle.")
    sys.exit(0)
git("commit", "-m", f"Données du {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
for essai in range(3):
    if git("pull", "--rebase", "-X", "theirs") == 0 and git("push") == 0:
        print("Données enregistrées.")
        sys.exit(0)
print("Enregistrement impossible pour l’instant.", file=sys.stderr)
sys.exit(1)
