"""Outils partagés par tous les robots de Dix Mille Escales."""
import json, os, sys, time, urllib.request
from datetime import datetime, timezone

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RACINE, "data")
USER_AGENT = "DixMilleEscales/1.0 (+https://github.com/ ; robots du guide)"


def maintenant():
    return datetime.now(timezone.utc)


def horodatage():
    return maintenant().strftime("%Y-%m-%dT%H:%M:%SZ")


def lire(chemin, defaut=None):
    chemin = os.path.join(DATA, chemin)
    if not os.path.exists(chemin):
        return defaut
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def ecrire(chemin, donnees, compact=False):
    chemin = os.path.join(DATA, chemin)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if compact:
            json.dump(donnees, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(donnees, f, ensure_ascii=False, indent=1)
    os.replace(tmp, chemin)  # jamais de fichier à moitié écrit


def villes():
    return lire("villes.json", [])


def http(url, donnees=None, essais=3, delai=30, timeout=120):
    """Télécharge une URL avec plusieurs essais. Renvoie les octets, ou None en cas d'échec."""
    for n in range(1, essais + 1):
        try:
            req = urllib.request.Request(url, data=donnees, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if r.status == 204:
                    return b""
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None  # inutile de réessayer
            print(f"    essai {n}/{essais} : erreur {e.code}", file=sys.stderr)
        except Exception as e:
            print(f"    essai {n}/{essais} : {e}", file=sys.stderr)
        time.sleep(delai * n)
    return None


def journal(robot, etat, **details):
    """Note le résultat du passage, affiché sur la page « État des robots » du site."""
    j = lire("journal.json", {})
    j[robot] = dict(details, etat=etat, dernier_passage=horodatage())
    ecrire("journal.json", j)
  
